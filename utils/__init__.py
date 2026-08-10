# utils/__init__.py — ПОЛНЫЙ ФАЙЛ

import discord
from typing import Optional, Union


def safe_int(value: any, default: int = 0) -> int:
    """Безопасно преобразует значение в int"""
    try:
        if value is None:
            return default
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            cleaned = value.strip()
            if not cleaned:
                return default
            if cleaned.startswith('<@') and cleaned.endswith('>'):
                cleaned = cleaned.replace('<@', '').replace('>', '').replace('!', '')
            if cleaned.isdigit():
                return int(cleaned)
        return default
    except:
        return default


def get_role_ids_from_setting(db, setting_key: str) -> list:
    """Получить список ID ролей из настройки (через запятую)"""
    try:
        setting_value = db.get_setting(setting_key, '')
        if not setting_value:
            return []
        
        role_ids = []
        for part in setting_value.split(','):
            part = part.strip()
            if part.isdigit():
                role_ids.append(int(part))
        
        return role_ids
    except Exception as e:
        print(f"⚠️ Ошибка получения ролей из настройки {setting_key}: {e}")
        return []


def format_days(days_str: str) -> str:
    """Форматирует дни недели для отображения (переводит на русский)"""
    if not days_str:
        return "Не указаны"
    
    day_map = {
        "monday": "ПН",
        "tuesday": "ВТ",
        "wednesday": "СР",
        "thursday": "ЧТ",
        "friday": "ПТ",
        "saturday": "СБ",
        "sunday": "ВС",
        "mon": "ПН",
        "tue": "ВТ",
        "wed": "СР",
        "thu": "ЧТ",
        "fri": "ПТ",
        "sat": "СБ",
        "sun": "ВС",
        "пн": "ПН",
        "вт": "ВТ",
        "ср": "СР",
        "чт": "ЧТ",
        "пт": "ПТ",
        "сб": "СБ",
        "вс": "ВС",
        "понедельник": "ПН",
        "вторник": "ВТ",
        "среда": "СР",
        "четверг": "ЧТ",
        "пятница": "ПТ",
        "суббота": "СБ",
        "воскресенье": "ВС",
    }
    
    result = days_str.lower()
    for eng, rus in day_map.items():
        result = result.replace(eng.lower(), rus)
    
    result = result.replace(',', ' ').replace('.', ' ')
    
    day_order = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"]
    found_days = []
    for day in day_order:
        if day in result:
            found_days.append(day)
    
    if not found_days:
        return days_str
    
    return ', '.join(found_days)


def format_raid_roles(roles_str: str) -> str:
    """Форматирует строку ролей для отображения"""
    if not roles_str:
        return "Не указана"
    
    role_map = {
        'tank': '🛡️ Танк',
        'heal': '💚 Хил',
        'mdd': '⚔️ Ближний ДД',
        'rdd': '🏹 Дальний ДД'
    }
    
    roles = roles_str.split(',')
    formatted = []
    for role in roles:
        role = role.strip()
        formatted.append(role_map.get(role, role))
    
    return ', '.join(formatted)


async def remove_roles_from_setting(member: discord.Member, db, setting_key: str, reason: str = ""):
    """Снимает с участника роль, указанную в настройке"""
    try:
        role_id = safe_int(db.get_setting(setting_key, ''))
        if not role_id:
            return False
        
        role = member.guild.get_role(role_id)
        if not role:
            return False
        
        if role not in member.roles:
            return False
        
        await member.remove_roles(role, reason=reason or f"Снятие роли {role.name}")
        return True
    except discord.Forbidden:
        print(f"❌ Нет прав на снятие роли {setting_key} с {member.display_name}")
        return False
    except Exception as e:
        print(f"❌ Ошибка при снятии роли {setting_key}: {e}")
        return False


# ============================================
# ПРОВЕРКИ ПРАВ
# ============================================

def is_developer(user: discord.Member, db) -> bool:
    """Проверяет, является ли пользователь разработчиком"""
    try:
        dev_id = db.get_setting('developer_id', '')
        return dev_id and str(user.id) == dev_id
    except:
        return False


def is_guild_master(user: discord.Member, db) -> bool:
    """Проверяет, является ли пользователь главой гильдии"""
    if is_developer(user, db):
        return True
    try:
        role_id = safe_int(db.get_setting('guild_master', ''))
        if not role_id:
            return False
        role = user.guild.get_role(role_id)
        return role is not None and role in user.roles
    except:
        return False


def is_vice_master(user: discord.Member, db) -> bool:
    """Проверяет, является ли пользователь зам. главы"""
    if is_developer(user, db):
        return True
    try:
        role_id = safe_int(db.get_setting('vice_master', ''))
        if not role_id:
            return False
        role = user.guild.get_role(role_id)
        return role is not None and role in user.roles
    except:
        return False


def is_raid_leader(user: discord.Member, db) -> bool:
    """Проверяет, является ли пользователь рейд-лидером"""
    if is_developer(user, db):
        return True
    try:
        role_id = safe_int(db.get_setting('raid_leader', ''))
        if not role_id:
            return False
        role = user.guild.get_role(role_id)
        return role is not None and role in user.roles
    except:
        return False


def is_officer(user: discord.Member, db) -> bool:
    """Проверяет, является ли пользователь офицером"""
    if is_developer(user, db):
        return True
    try:
        role_id = safe_int(db.get_setting('officer', ''))
        if not role_id:
            return False
        role = user.guild.get_role(role_id)
        return role is not None and role in user.roles
    except:
        return False


def can_manage_settings(user: discord.Member, db) -> bool:
    """Может ли пользователь управлять настройками"""
    if is_developer(user, db):
        return True
    return is_guild_master(user, db) or is_vice_master(user, db)


def can_manage_applications(user: discord.Member, db) -> bool:
    """Может ли пользователь управлять заявками"""
    if is_developer(user, db):
        return True
    return is_officer(user, db) or is_raid_leader(user, db) or is_vice_master(user, db) or is_guild_master(user, db)


def can_manage_appeals(user: discord.Member, db) -> bool:
    """Может ли пользователь управлять апелляциями"""
    if is_developer(user, db):
        return True
    return is_officer(user, db) or is_raid_leader(user, db) or is_vice_master(user, db) or is_guild_master(user, db)


def can_manage_characters(user: discord.Member, db) -> bool:
    """Может ли пользователь управлять персонажами"""
    if is_developer(user, db):
        return True
    return is_officer(user, db) or is_raid_leader(user, db) or is_vice_master(user, db) or is_guild_master(user, db)


def can_issue_punishments(user: discord.Member, db) -> bool:
    """Может ли пользователь выдавать наказания"""
    if is_developer(user, db):
        return True
    return is_officer(user, db) or is_raid_leader(user, db) or is_vice_master(user, db) or is_guild_master(user, db)


def can_remove_punishments(user: discord.Member, db) -> bool:
    """Может ли пользователь снимать наказания"""
    if is_developer(user, db):
        return True
    return is_raid_leader(user, db) or is_vice_master(user, db) or is_guild_master(user, db)


def can_manage_absences(user: discord.Member, db) -> bool:
    """Может ли пользователь управлять отсутствиями"""
    if is_developer(user, db):
        return True
    return is_officer(user, db) or is_raid_leader(user, db) or is_vice_master(user, db) or is_guild_master(user, db)


def can_manage_raids(user: discord.Member, db) -> bool:
    """Может ли пользователь управлять рейдами"""
    if is_developer(user, db):
        return True
    return is_raid_leader(user, db) or is_vice_master(user, db) or is_guild_master(user, db)


def can_manage_compositions(user: discord.Member, db) -> bool:
    """Может ли пользователь управлять составами"""
    if is_developer(user, db):
        return True
    return is_raid_leader(user, db) or is_vice_master(user, db) or is_guild_master(user, db)


def can_accept_static(user: discord.Member, db) -> bool:
    """Может ли пользователь принимать в статик"""
    if is_developer(user, db):
        return True
    return is_raid_leader(user, db) or is_vice_master(user, db) or is_guild_master(user, db)


def can_approve_main_change(user: discord.Member, db) -> bool:
    """Может ли пользователь одобрять смену основного"""
    if is_developer(user, db):
        return True
    return is_raid_leader(user, db) or is_vice_master(user, db) or is_guild_master(user, db)


def can_use_admin_center(user: discord.Member, db) -> bool:
    """Может ли пользователь использовать админ-центр"""
    if is_developer(user, db):
        return True
    return is_guild_master(user, db) or is_vice_master(user, db)


def can_manage_reports(user: discord.Member, db) -> bool:
    """Может ли пользователь управлять жалобами"""
    if is_developer(user, db):
        return True
    return is_officer(user, db) or is_raid_leader(user, db) or is_vice_master(user, db) or is_guild_master(user, db)
async def add_roles_from_setting(member: discord.Member, db, setting_key: str, reason: str = "") -> bool:
    """
    Выдаёт роли пользователю из настройки (список ID через запятую)
    Возвращает True если хотя бы одна роль была выдана
    """
    if not member or not db:
        return False
    
    role_ids = get_role_ids_from_setting(db, setting_key)
    if not role_ids:
        return False
    
    success = False
    for role_id in role_ids:
        role = member.guild.get_role(role_id)
        if role and role not in member.roles:
            try:
                await member.add_roles(role, reason=reason or f"Выдача роли {role.name}")
                success = True
                print(f"   ✅ Выдана роль: {role.name}")
            except Exception as e:
                print(f"   ❌ Ошибка выдачи роли {role.name}: {e}")
    
    return success


async def remove_roles_from_setting(member: discord.Member, db, setting_key: str, reason: str = "") -> bool:
    """
    Снимает роли с пользователя из настройки (список ID через запятую)
    Возвращает True если хотя бы одна роль была снята
    """
    if not member or not db:
        return False
    
    role_ids = get_role_ids_from_setting(db, setting_key)
    if not role_ids:
        return False
    
    success = False
    for role_id in role_ids:
        role = member.guild.get_role(role_id)
        if role and role in member.roles:
            try:
                await member.remove_roles(role, reason=reason or f"Снятие роли {role.name}")
                success = True
                print(f"   ✅ Снята роль: {role.name}")
            except Exception as e:
                print(f"   ❌ Ошибка снятия роли {role.name}: {e}")
    
    return success


def get_role_ids_from_setting(db, setting_key: str) -> list:
    """
    Получает список ID ролей из настройки (разделённых запятой)
    """
    if not db:
        return []
    
    setting_value = db.get_setting(setting_key, '')
    if not setting_value:
        return []
    
    role_ids = []
    for part in setting_value.split(','):
        part = part.strip()
        if part.isdigit():
            role_ids.append(int(part))
    
    return role_ids


def safe_int(value, default=0):
    """
    Безопасное преобразование в int
    """
    if value is None:
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except (ValueError, TypeError):
            return default
    return default