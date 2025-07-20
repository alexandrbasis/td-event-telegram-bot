import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Токен бота (получите у @BotFather)
BOT_TOKEN = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')

# Настройки бота
BOT_USERNAME = 'tresdias_israelbot'

# Роли пользователей
COORDINATOR_IDS = [311380449, 5212991086, 649919193, 8086614107]  # ID пользователей-координаторов
VIEWER_IDS = []       # ID пользователей-наблюдателей

# Проверка конфигурации
if BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
    print("⚠️  ВНИМАНИЕ: Установите BOT_TOKEN в файле .env")