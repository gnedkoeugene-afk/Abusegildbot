# utils/trainee_utils.py — ПОЛНЫЙ ФАЙЛ

import discord
import utils


async def assign_trainee_role(member: discord.Member, db) -> bool:
    """Выдать роль курсанта"""
    try:
        role_id = utils.safe_int(db.get_setting('trainee_role', ''))
        if not role_id:
            print(f"⚠️ Роль курсанта не настроена в /settings")
            return False
        
        role = member.guild.get_role(role_id)
        if not role:
            print(f"❌ Роль курсанта (ID: {role_id}) не найдена на сервере")
            return False
        
        if role in member.roles:
            print(f"ℹ️ У {member.display_name} уже есть роль курсанта")
            return False
        
        await member.add_roles(role, reason="Назначение роли курсанта (обучение РЛ)")
        print(f"✅ Роль курсанта выдана {member.display_name}")
        return True
        
    except discord.Forbidden:
        print(f"❌ Нет прав на выдачу роли курсанта {member.display_name}")
        return False
    except discord.HTTPException as e:
        print(f"❌ Ошибка HTTP при выдаче роли: {e}")
        return False
    except Exception as e:
        print(f"❌ Ошибка при выдаче роли курсанта: {e}")
        return False


async def remove_trainee_role(member: discord.Member, db) -> bool:
    """Снять роль курсанта"""
    try:
        role_id = utils.safe_int(db.get_setting('trainee_role', ''))
        if not role_id:
            print(f"⚠️ Роль курсанта не настроена в /settings")
            return False
        
        role = member.guild.get_role(role_id)
        if not role:
            print(f"❌ Роль курсанта (ID: {role_id}) не найдена на сервере")
            return False
        
        if role not in member.roles:
            print(f"ℹ️ У {member.display_name} нет роли курсанта")
            return False
        
        await member.remove_roles(role, reason="Снятие роли курсанта")
        print(f"✅ Роль курсанта снята с {member.display_name}")
        return True
        
    except discord.Forbidden:
        print(f"❌ Нет прав на снятие роли курсанта с {member.display_name}")
        return False
    except discord.HTTPException as e:
        print(f"❌ Ошибка HTTP при снятии роли: {e}")
        return False
    except Exception as e:
        print(f"❌ Ошибка при снятии роли курсанта: {e}")
        return False


async def assign_curator_role(member: discord.Member, db) -> bool:
    """Выдать роль куратора"""
    try:
        role_id = utils.safe_int(db.get_setting('curator_role', ''))
        if not role_id:
            print(f"⚠️ Роль куратора не настроена в /settings")
            return False
        
        role = member.guild.get_role(role_id)
        if not role:
            print(f"❌ Роль куратора (ID: {role_id}) не найдена на сервере")
            return False
        
        if role in member.roles:
            print(f"ℹ️ У {member.display_name} уже есть роль куратора")
            return False
        
        await member.add_roles(role, reason="Назначение роли куратора")
        print(f"✅ Роль куратора выдана {member.display_name}")
        return True
        
    except discord.Forbidden:
        print(f"❌ Нет прав на выдачу роли куратора {member.display_name}")
        return False
    except discord.HTTPException as e:
        print(f"❌ Ошибка HTTP при выдаче роли: {e}")
        return False
    except Exception as e:
        print(f"❌ Ошибка при выдаче роли куратора: {e}")
        return False


async def remove_curator_role(member: discord.Member, db) -> bool:
    """Снять роль куратора"""
    try:
        role_id = utils.safe_int(db.get_setting('curator_role', ''))
        if not role_id:
            print(f"⚠️ Роль куратора не настроена в /settings")
            return False
        
        role = member.guild.get_role(role_id)
        if not role:
            print(f"❌ Роль куратора (ID: {role_id}) не найдена на сервере")
            return False
        
        if role not in member.roles:
            print(f"ℹ️ У {member.display_name} нет роли куратора")
            return False
        
        await member.remove_roles(role, reason="Снятие роли куратора")
        print(f"✅ Роль куратора снята с {member.display_name}")
        return True
        
    except discord.Forbidden:
        print(f"❌ Нет прав на снятие роли куратора с {member.display_name}")
        return False
    except discord.HTTPException as e:
        print(f"❌ Ошибка HTTP при снятии роли: {e}")
        return False
    except Exception as e:
        print(f"❌ Ошибка при снятии роли куратора: {e}")
        return False

async def remove_trainee_completely(member: discord.Member, db) -> bool:
    """
    Полностью удалить пользователя из системы обучения:
    - Снять роль курсанта
    - Снять роль куратора (если есть)
    - Удалить запись из БД
    - Записать лог
    """
    if not member or not db:
        return False

    # Снимаем роль курсанта
    await remove_trainee_role(member, db)
    # Снимаем роль куратора (на всякий случай)
    await remove_curator_role(member, db)
    # Удаляем из БД
    success = db.remove_trainee(member.id)
    if success:
        db.add_trainee_log(
            0,  # trainee_id = 0, так как удаляем
            f"🗑️ Удалён из системы обучения: {member.display_name} (ID: {member.id})",
            performed_by=member.id
        )
        return True
    return False