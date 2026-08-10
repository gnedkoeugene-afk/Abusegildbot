import discord

# ========== РОЛИ ДЛЯ РЕЙДА ==========

RAID_ROLE_NAMES = {
    "mdd": "🗡️ МДД",
    "rdd": "🏹 РДД",
    "tank": "🛡️ Танк",
    "heal": "💚 Хилл"
}

RAID_ROLE_EMOJIS = {
    "mdd": "🗡️",
    "rdd": "🏹",
    "tank": "🛡️",
    "heal": "💚"
}

def format_raid_roles(roles_str: str) -> str:
    """Форматирует строку ролей (mdd,rdd) в читаемый вид (🗡️ МДД, 🏹 РДД)"""
    if not roles_str:
        return "Не указана"
    roles = roles_str.split(',')
    names = [RAID_ROLE_NAMES.get(r.strip(), r.strip()) for r in roles]
    return ', '.join(names)

# ========== КЛАССЫ И СПЕЦИАЛИЗАЦИИ ==========

CLASS_SPECS = {
    "Воин": ["Защита", "Оружие", "Неистовство"],
    "Паладин": ["Свет", "Защита", "Возмездие"],
    "Охотник": ["Выживание", "Повелитель зверей", "Стрельба"],
    "Разбойник": ["Ликвидация", "Головорез", "Бойня"],
    "Жрец": ["Свет", "Тьма", "Послушание"],
    "Друид": ["Баланс", "Страж", "Сила зверя", "Исцеление"],
    "Шаман": ["Стихии", "Совершенствование", "Исцеление"],
    "Маг": ["Лед", "Огонь", "Тайная магия"],
    "Чернокнижник": ["Колдовство", "Демонология", "Разрушение"],
    "Рыцарь Смерти": ["Кровь", "Лёд", "Нечестивость"],
}

CLASS_OPTIONS = [
    discord.SelectOption(label="Воин", value="Воин", emoji="⚔️"),
    discord.SelectOption(label="Паладин", value="Паладин", emoji="✨"),
    discord.SelectOption(label="Охотник", value="Охотник", emoji="🏹"),
    discord.SelectOption(label="Разбойник", value="Разбойник", emoji="🗡️"),
    discord.SelectOption(label="Жрец", value="Жрец", emoji="🙏"),
    discord.SelectOption(label="Друид", value="Друид", emoji="🌳"),
    discord.SelectOption(label="Шаман", value="Шаман", emoji="🌊"),
    discord.SelectOption(label="Маг", value="Маг", emoji="🔮"),
    discord.SelectOption(label="Чернокнижник", value="Чернокнижник", emoji="😈"),
    discord.SelectOption(label="Рыцарь Смерти", value="Рыцарь Смерти", emoji="💀"),
]

DAY_OPTIONS = [
    discord.SelectOption(label="Понедельник", value="mon", emoji="📅"),
    discord.SelectOption(label="Вторник", value="tue", emoji="📅"),
    discord.SelectOption(label="Среда", value="wed", emoji="📅"),
    discord.SelectOption(label="Четверг", value="thu", emoji="📅"),
    discord.SelectOption(label="Пятница", value="fri", emoji="📅"),
    discord.SelectOption(label="Суббота", value="sat", emoji="🎉"),
    discord.SelectOption(label="Воскресенье", value="sun", emoji="🎉"),
]