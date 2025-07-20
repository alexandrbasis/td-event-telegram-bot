import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Токен бота (получите у @BotFather)
BOT_TOKEN = os.getenv('BOT_TOKEN', '7655205858:AAGftiITVgSM2dlGcMFZo5VJaYJ0kYNi14g')

# Настройки бота
BOT_USERNAME = 'tresdias_israelbot'

# Роли пользователей (пока заглушки)
COORDINATOR_IDS = [311380449, 5212991086, 649919193]  # ID пользователей-координаторов
VIEWER_IDS = []       # ID пользователей-наблюдателей

# Проверка конфигурации
if BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
    print("⚠️  ВНИМАНИЕ: Установите BOT_TOKEN в файле .env")