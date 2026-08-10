import discord
import hashlib

def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def has_role_by_setting(member: discord.Member, db, setting_key: str) -> bool:
    if db is None:
        return False
    role_ids_str = db.get_setting(setting_key, '')
    if not role_ids_str:
        return False
    role_ids = [rid.strip() for rid in role_ids_str.split(',') if rid.strip().isdigit()]
    for role in member.roles:
        if str(role.id) in role_ids:
            return True
    return False


def is_developer(member: discord.Member, db) -> bool:
    """Проверка: разработчик? Имеет ВСЕ права."""
    if db is None:
        return False
    developer_id = db.get_setting('developer_id', '')
    if not developer_id:
        return False
    return str(member.id) == developer_id


def has_permission(member: discord.Member, db, permission_key: str) -> bool:
    if db is None:
        return False
    
    # Разработчик имеет ВСЕ права
    if is_developer(member, db):
        return True
    
    # Обычная проверка по ролям
    role_checks = [
        ('guild_master', 'guild_master'),
        ('vice_master', 'vice_master'),
        ('raid_leader', 'raid_leader'),
        ('officer', 'officer'),
    ]
    
    for role_key, setting_key in role_checks:
        if has_role_by_setting(member, db, setting_key):
            perms = db.get_role_permissions_settings(role_key)
            if perms and perms.get(permission_key, False):
                return True
    
    return False


def get_role_ids_from_setting(db, setting_key: str) -> list:
    if db is None:
        return []
    value = db.get_setting(setting_key, '')
    if not value:
        return []
    return [int(rid.strip()) for rid in value.split(',') if rid.strip().isdigit()]


async def add_roles_from_setting(member: discord.Member, db, setting_key: str, reason: str = "") -> bool:
    """Безопасно выдаёт роли из настройки. Если основная не найдена — пробует альтернативные."""
    if db is None:
        print(f"❌ [{member.display_name}] БД не найдена")
        return False
    
    role_ids = get_role_ids_from_setting(db, setting_key)
    
    if not role_ids:
        print(f"⚠️ [{member.display_name}] Роль '{setting_key}' не настроена в БД!")
        
        # Пробуем альтернативные ключи для member_role
        if setting_key == 'member_role':
            alt_keys = ['member', 'main_role', 'participant_role']
            for alt_key in alt_keys:
                alt_ids = get_role_ids_from_setting(db, alt_key)
                if alt_ids:
                    print(f"   ℹ️ Найдена роль по альтернативному ключу '{alt_key}'")
                    role_ids = alt_ids
                    break
        
        # Если всё равно не нашли — пробуем выдать гостя
        if not role_ids and setting_key == 'member_role':
            print(f"   ⚠️ Пробуем выдать guest_role...")
            return await add_roles_from_setting(member, db, 'guest_role', f"{reason} (member_role не настроена)")
        
        if not role_ids:
            return False
    
    success = False
    for role_id in role_ids:
        role = member.guild.get_role(role_id)
        if role:
            try:
                if role not in member.roles:
                    await member.add_roles(role, reason=reason)
                    print(f"✅ [{member.display_name}] Выдана роль: {role.name} (ключ: {setting_key})")
                    success = True
                else:
                    print(f"ℹ️ [{member.display_name}] Роль {role.name} уже есть")
                    success = True
            except Exception as e:
                print(f"❌ [{member.display_name}] Ошибка выдачи роли {role.name}: {e}")
        else:
            print(f"❌ [{member.display_name}] Роль с ID {role_id} не найдена на сервере!")
    
    return success


async def remove_roles_from_setting(member: discord.Member, db, setting_key: str, reason: str = "") -> bool:
    if db is None:
        return False
    
    role_ids = get_role_ids_from_setting(db, setting_key)
    if not role_ids:
        return False
    
    success = False
    for role_id in role_ids:
        role = member.guild.get_role(role_id)
        if role and role in member.roles:
            try:
                await member.remove_roles(role, reason=reason)
                print(f"✅ [{member.display_name}] Снята роль: {role.name}")
                success = True
            except Exception as e:
                print(f"❌ [{member.display_name}] Ошибка снятия роли {role.name}: {e}")
    return success


# ========== ПРОВЕРКИ РОЛЕЙ ==========

def is_guild_master(member: discord.Member, db) -> bool:
    if is_developer(member, db):
        return True
    return has_role_by_setting(member, db, 'guild_master')


def is_vice_master(member: discord.Member, db) -> bool:
    if is_developer(member, db):
        return True
    return has_role_by_setting(member, db, 'vice_master')


def is_raid_leader(member: discord.Member, db) -> bool:
    if is_developer(member, db):
        return True
    return has_role_by_setting(member, db, 'raid_leader')


def is_officer(member: discord.Member, db) -> bool:
    if is_developer(member, db):
        return True
    return has_role_by_setting(member, db, 'officer')


# ========== ПРОВЕРКИ ПРАВ ==========

def can_manage_settings(member: discord.Member, db) -> bool:
    if is_developer(member, db):
        return True
    return has_permission(member, db, 'settings')


def can_manage_applications(member: discord.Member, db) -> bool:
    if is_developer(member, db):
        return True
    return has_permission(member, db, 'applications')


def can_manage_appeals(member: discord.Member, db) -> bool:
    if is_developer(member, db):
        return True
    return has_permission(member, db, 'appeals')


def can_manage_absences(member: discord.Member, db) -> bool:
    if is_developer(member, db):
        return True
    return has_permission(member, db, 'absences')


def can_manage_characters(member: discord.Member, db) -> bool:
    if is_developer(member, db):
        return True
    return has_permission(member, db, 'characters')


def can_manage_raids(member: discord.Member, db) -> bool:
    if is_developer(member, db):
        return True
    return has_permission(member, db, 'raids')


def can_manage_compositions(member: discord.Member, db) -> bool:
    if is_developer(member, db):
        return True
    return has_permission(member, db, 'manage_raids')


def can_issue_punishments(member: discord.Member, db) -> bool:
    if is_developer(member, db):
        return True
    return has_permission(member, db, 'punishments')


def can_remove_punishments(member: discord.Member, db) -> bool:
    if is_developer(member, db):
        return True
    return has_permission(member, db, 'remove_punishments')


def can_approve_main_change(member: discord.Member, db) -> bool:
    if is_developer(member, db):
        return True
    return has_permission(member, db, 'main_change')


def can_accept_static(member: discord.Member, db) -> bool:
    if is_developer(member, db):
        return True
    return has_permission(member, db, 'static')


def can_use_admin_center(member: discord.Member, db) -> bool:
    if is_developer(member, db):
        return True
    return has_permission(member, db, 'admin_center')


# ========== ФОРМАТИРОВАНИЕ ==========

def format_days(days_str: str) -> str:
    if not days_str:
        return "Не указано"
    days_map = {"mon": "Пн", "tue": "Вт", "wed": "Ср", "thu": "Чт", "fri": "Пт", "sat": "Сб", "sun": "Вс"}
    days_list = days_str.split(',')
    formatted = [days_map[d] for d in days_list if d in days_map]
    return " ".join(formatted)


RAID_ROLE_NAMES = {
    "mdd": "🗡️ МДД",
    "rdd": "🏹 РДД",
    "tank": "🛡️ Танк",
    "heal": "💚 Хилл"
}


def format_raid_roles(roles_str: str) -> str:
    if not roles_str:
        return "Не указана"
    roles = roles_str.split(',')
    names = [RAID_ROLE_NAMES.get(r.strip(), r.strip()) for r in roles]
    return ', '.join(names)

def can_manage_reports(member: discord.Member, db) -> bool:
    """Проверка права управления жалобами"""
    if is_developer(member, db):
        return True
    return has_permission(member, db, 'reports')



def generate_user_hash(user_id: int, guild_id: int) -> str:
    """Генерирует уникальный 6-значный хеш для идентификации автора"""
    salt = "AbuseGuildBot2024"
    raw = f"{user_id}_{guild_id}_{salt}"
    hash_obj = hashlib.md5(raw.encode())
    return hash_obj.hexdigest()[:6].upper()