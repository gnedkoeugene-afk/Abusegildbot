import asyncio
from datetime import datetime


def get_class_emoji(class_name: str) -> str:
    """Возвращает эмодзи для класса"""
    emojis = {
        "Воин": "⚔️", "Паладин": "✨", "Охотник": "🏹", "Разбойник": "🗡️",
        "Жрец": "🙏", "Друид": "🌳", "Шаман": "🌊", "Маг": "🔮",
        "Чернокнижник": "😈", "Рыцарь Смерти": "💀"
    }
    return emojis.get(class_name, "🎮")


async def delete_message_after_delay(message, delay: int):
    """Удаляет сообщение через заданную задержку"""
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except:
        pass


async def schedule_absence_removal(client, absence_id, end_datetime, message):
    """Планирует удаление сообщения об отсутствии и снятие роли AFK"""
    import utils
    
    now = datetime.now()
    
    if end_datetime <= now:
        await asyncio.sleep(5)
        try:
            await message.delete()
            db = client.db
            db.mark_absence_completed(absence_id)
            
            db.cursor.execute('SELECT user_id FROM absences WHERE id = ?', (absence_id,))
            row = db.cursor.fetchone()
            if row:
                user_id = row[0]
                guild = message.guild
                user = guild.get_member(user_id)
                if user:
                    await utils.remove_roles_from_setting(user, db, 'afk_role', "Окончание срока отсутствия")
        except Exception as e:
            print(f"⚠️ Ошибка: {e}")
    else:
        delay = (end_datetime - now).total_seconds()
        
        async def remove_task():
            await asyncio.sleep(delay)
            try:
                await message.delete()
                db = client.db
                db.mark_absence_completed(absence_id)
                
                db.cursor.execute('SELECT user_id FROM absences WHERE id = ?', (absence_id,))
                row = db.cursor.fetchone()
                if row:
                    user_id = row[0]
                    guild = message.guild
                    user = guild.get_member(user_id)
                    if user:
                        await utils.remove_roles_from_setting(user, db, 'afk_role', "Окончание срока отсутствия")
            except Exception as e:
                print(f"⚠️ Ошибка: {e}")
        
        asyncio.create_task(remove_task())