import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Токен бота (получите у @BotFather)
BOT_TOKEN = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')

# Настройки бота
BOT_USERNAME = 'tresdias_israelbot'

# Роли пользователей
COORDINATOR_IDS = [311380449, 5212991086, 649919193, 8086614107, 476732940]  # ID пользователей-координаторов
VIEWER_IDS = []       # ID пользователей-наблюдателей

# ✅ ИСПРАВЛЕНО: Настройки базы данных с умной логикой
DATABASE_TYPE = os.getenv('DATABASE_TYPE', 'local')  # 'airtable' или 'local'

# ✅ ИСПРАВЛЕНО: Настройки Airtable с проверками
AIRTABLE_TOKEN = os.getenv('AIRTABLE_TOKEN', '').strip()
AIRTABLE_BASE_ID = os.getenv('AIRTABLE_BASE_ID', '').strip()
AIRTABLE_TABLE_NAME = os.getenv('AIRTABLE_TABLE_NAME', 'Events')

# ✅ ДОБАВЛЕНО: Автоматическое переключение на local если Airtable не настроен
if DATABASE_TYPE == 'airtable':
    if not AIRTABLE_TOKEN or not AIRTABLE_BASE_ID:
        print("⚠️  Airtable не настроен полностью. Переключаемся на локальную базу данных.")
        print(f"   AIRTABLE_TOKEN: {'✅ есть' if AIRTABLE_TOKEN else '❌ пустой'}")
        print(f"   AIRTABLE_BASE_ID: {'✅ есть' if AIRTABLE_BASE_ID else '❌ пустой'}")
        DATABASE_TYPE = 'local'
    else:
        print("✅ Используем Airtable базу данных")
else:
    print("✅ Используем локальную базу данных")

# ✅ ДОБАВЛЕНО: Дополнительные настройки
DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Проверка конфигурации
if BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE' or len(BOT_TOKEN) < 40:
    print("⚠️  ВНИМАНИЕ: Установите корректный BOT_TOKEN в файле .env")
    print("   Получите токен у @BotFather в Telegram")

print(f"🤖 Бот: {BOT_USERNAME}")
print(f"🗃️  База данных: {DATABASE_TYPE}")
print(f"👥 Координаторов: {len(COORDINATOR_IDS)}")