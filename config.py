import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')

# Основной сервер
MAIN_GUILD_ID = int(os.getenv('MAIN_GUILD_ID'))
MAIN_DB_PATH = os.getenv('MAIN_DB_PATH', 'data/main_guild_bot.db')

# Тестовый сервер
TEST_GUILD_ID = int(os.getenv('TEST_GUILD_ID'))
TEST_DB_PATH = os.getenv('TEST_DB_PATH', 'data/test_guild_bot.db')

# Разработчик
DEVELOPER_ID = int(os.getenv('DEVELOPER_ID')) if os.getenv('DEVELOPER_ID') else None
BOT_OWNER_ID = int(os.getenv('BOT_OWNER_ID')) if os.getenv('BOT_OWNER_ID') else None