import logging
from typing import List, Dict, Optional
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from config import BOT_TOKEN, BOT_USERNAME, COORDINATOR_IDS, VIEWER_IDS
from database import init_database, add_participant, get_all_participants, get_participant_by_id, find_participant_by_name, update_participant

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Функция проверки прав пользователя
def get_user_role(user_id):
    if user_id in COORDINATOR_IDS:
        return "coordinator"
    elif user_id in VIEWER_IDS:
        return "viewer"
    else:
        return "unauthorized"

# Функция умного парсинга данных участника
def parse_participant_data(text: str) -> Dict:
    """Пытается извлечь данные участника из любого текста"""
    
    # Очищаем текст
    text = text.strip()
    all_words = text.split()
    
    # Инициализируем данные
    data = {
        'FullNameRU': '',
        'Gender': 'F',
        'Size': '',
        'Church': '',
        'Role': 'CANDIDATE',
        'Department': '',
        'FullNameEN': '',
        'SubmittedBy': '',
        'ContactInformation': '',
        'CountryAndCity': ''
    }
    
    # Словари для распознавания
    gender_keywords = {
        'M': ['M', 'МУЖ', 'МУЖСКОЙ', 'MALE', 'М', 'МУЖЧИНА'],
        'F': ['F', 'ЖЕН', 'ЖЕНСКИЙ', 'FEMALE', 'Ж', 'ЖЕНЩИНА']
    }
    
    role_keywords = {
        'TEAM': ['TEAM', 'КОМАНДА', 'ТИМ', 'TIM', 'TEAM MEMBER', 'ЧЛЕН КОМАНДЫ', 'КОМАНДНЫЙ', 'СЛУЖИТЕЛЬ'],
        'CANDIDATE': ['CANDIDATE', 'КАНДИДАТ', 'УЧАСТНИК', 'КАНДИДАТКА']
    }
    
    department_keywords = {
        'ROE': ['ROE', 'РОЕ', 'ROE ROOM', 'РОЕ РУМ', 'РОЭ', 'РОИ'],
        'Chapel': ['CHAPEL', 'МОЛИТВЕННЫЙ', 'МОЛИТВА', 'PRAYER', 'ЧАСОВНЯ'],
        'Setup': ['SETUP', 'СЕТАП', 'НАСТРОЙКА', 'ПОДГОТОВКА', 'СЕТ АП'],
        'Palanka': ['PALANKA', 'ПАЛАНКА', 'ПОЛАНКА'],
        'Administration': ['ADMINISTRATION', 'АДМИНИСТРАЦИЯ', 'АДМИН', 'ADMIN', 'УПРАВЛЕНИЕ'],
        'Kitchen': ['KITCHEN', 'КУХНЯ', 'КИТЧЕН', 'КУЛИНАРИЯ', 'ПОВАРА'],
        'Decoration': ['DECORATION', 'ДЕКОРАЦИИ', 'ДЕКОР', 'DECO', 'DECOR', 'УКРАШЕНИЯ', 'ОФОРМЛЕНИЕ'],
        'Bell': ['BELL', 'ЗВОНАРЬ', 'БЕЛЛ', 'ЗВОН', 'КОЛОКОЛЬЧИК'],
        'Refreshment': ['REFRESHMENT', 'РЕФРЕШМЕНТ', 'УГОЩЕНИЯ', 'НАПИТКИ'],
        'Worship': ['WORSHIP', 'ПРОСЛАВЛЕНИЕ', 'ВОРШИП', 'МУЗЫКА', 'MUSIC'],
        'Media': ['MEDIA', 'МЕДИА', 'ВИДЕО', 'ФОТО', 'СЪЕМКА', 'КАМЕРА', 'ФОТОГРАФ'],
        'Духовенство': ['ДУХОВЕНСТВО', 'CLERGY', 'СВЯЩЕННИКИ'],
        'Ректорат': ['РЕКТОРАТ', 'RECTOR', 'РЕКТОРЫ']
    }
    
    church_keywords = ['ЦЕРКОВЬ', 'CHURCH', 'ХРАМ', 'ОБЩИНА']
    sizes = ['XS', 'S', 'M', 'L', 'XL', 'XXL', '2XL', '3XL']
    
    # Словарь городов Израиля
israel_cities = [
    'ХАЙФА', 'HAIFA', 'ТЕЛ-АВИВ', 'TEL AVIV', 'ТЕЛЬ-АВИВ', 'ИЕРУСАЛИМ', 'JERUSALEM', 
    'БЕЭР-ШЕВА', 'BEER SHEVA', 'НЕТАНИЯ', 'NETANYA', 'АШДОД', 'ASHDOD', 
    'РИШОН-ЛЕ-ЦИОН', 'RISHON LEZION', 'ПЕТАХ-ТИКВА', 'PETAH TIKVA', 'РЕХОВОТ', 'REHOVOT',
    'БАТ-ЯМ', 'BAT YAM', 'КАРМИЭЛЬ', 'CARMIEL', 'МОДИИН', 'MODIIN', 'НАЗАРЕТ', 'NAZARETH',
    'КИРЬЯТ-ГАТ', 'KIRYAT GAT', 'ЭЙЛАТ', 'EILAT', 'АККО', 'ACRE', 'РАМАТ-ГАН', 'RAMAT GAN',
    'БНЕЙ-БРАК', 'BNEI BRAK', 'ЦФАТ', 'SAFED', 'ТВЕРИЯ', 'TIBERIAS', 'ГЕРЦЛИЯ', 'HERZLIYA'
]

# Функция проверки иврита (вне основной функции)
def contains_hebrew(text):
    return any('\u0590' <= char <= '\u05FF' for char in text)

# Функция умного парсинга данных участника
def parse_participant_data(text: str) -> Dict:
    """Пытается извлечь данные участника из любого текста"""
    
    # Очищаем текст
    text = text.strip()
    all_words = text.split()
    
    # Инициализируем данные
    data = {
        'FullNameRU': '',
        'Gender': 'F',
        'Size': '',
        'Church': '',
        'Role': 'CANDIDATE',
        'Department': '',
        'FullNameEN': '',
        'SubmittedBy': '',
        'ContactInformation': '',
        'CountryAndCity': ''
    }
    
    # Словари для распознавания
    gender_keywords = {
        'M': ['M', 'МУЖ', 'МУЖСКОЙ', 'MALE', 'М', 'МУЖЧИНА'],
        'F': ['F', 'ЖЕН', 'ЖЕНСКИЙ', 'FEMALE', 'Ж', 'ЖЕНЩИНА']
    }
    
    role_keywords = {
        'TEAM': ['TEAM', 'КОМАНДА', 'ТИМ', 'TIM', 'TEAM MEMBER', 'ЧЛЕН КОМАНДЫ', 'КОМАНДНЫЙ', 'СЛУЖИТЕЛЬ'],
        'CANDIDATE': ['CANDIDATE', 'КАНДИДАТ', 'УЧАСТНИК', 'КАНДИДАТКА']
    }
    
    department_keywords = {
        'ROE': ['ROE', 'РОЕ', 'ROE ROOM', 'РОЕ РУМ', 'РОЭ', 'РОИ'],
        'Chapel': ['CHAPEL', 'МОЛИТВЕННЫЙ', 'МОЛИТВА', 'PRAYER', 'ЧАСОВНЯ'],
        'Setup': ['SETUP', 'СЕТАП', 'НАСТРОЙКА', 'ПОДГОТОВКА', 'СЕТ АП'],
        'Palanka': ['PALANKA', 'ПАЛАНКА', 'ПОЛАНКА'],
        'Administration': ['ADMINISTRATION', 'АДМИНИСТРАЦИЯ', 'АДМИН', 'ADMIN', 'УПРАВЛЕНИЕ'],
        'Kitchen': ['KITCHEN', 'КУХНЯ', 'КИТЧЕН', 'КУЛИНАРИЯ', 'ПОВАРА'],
        'Decoration': ['DECORATION', 'ДЕКОРАЦИИ', 'ДЕКОР', 'DECO', 'DECOR', 'УКРАШЕНИЯ', 'ОФОРМЛЕНИЕ'],
        'Bell': ['BELL', 'ЗВОНАРЬ', 'БЕЛЛ', 'ЗВОН', 'КОЛОКОЛЬЧИК'],
        'Refreshment': ['REFRESHMENT', 'РЕФРЕШМЕНТ', 'УГОЩЕНИЯ', 'НАПИТКИ'],
        'Worship': ['WORSHIP', 'ПРОСЛАВЛЕНИЕ', 'ВОРШИП', 'МУЗЫКА', 'MUSIC'],
        'Media': ['MEDIA', 'МЕДИА', 'ВИДЕО', 'ФОТО', 'СЪЕМКА', 'КАМЕРА', 'ФОТОГРАФ'],
        'Духовенство': ['ДУХОВЕНСТВО', 'CLERGY', 'СВЯЩЕННИКИ'],
        'Ректорат': ['РЕКТОРАТ', 'RECTOR', 'РЕКТОРЫ']
    }
    
    church_keywords = ['ЦЕРКОВЬ', 'CHURCH', 'ХРАМ', 'ОБЩИНА']
    sizes = ['XS', 'S', 'M', 'L', 'XL', 'XXL', '2XL', '3XL']
    
    # Словарь городов Израиля
    israel_cities = [
        'ХАЙФА', 'HAIFA', 'ТЕЛ-АВИВ', 'TEL AVIV', 'ТЕЛЬ-АВИВ', 'ИЕРУСАЛИМ', 'JERUSALEM', 
        'БЕЭР-ШЕВА', 'BEER SHEVA', 'НЕТАНИЯ', 'NETANYA', 'АШДОД', 'ASHDOD', 
        'РИШОН-ЛЕ-ЦИОН', 'RISHON LEZION', 'ПЕТАХ-ТИКВА', 'PETAH TIKVA', 'РЕХОВОТ', 'REHOVOT',
        'БАТ-ЯМ', 'BAT YAM', 'КАРМИЭЛЬ', 'CARMIEL', 'МОДИИН', 'MODIIN', 'НАЗАРЕТ', 'NAZARETH',
        'КИРЬЯТ-ГАТ', 'KIRYAT GAT', 'ЭЙЛАТ', 'EILAT', 'АККО', 'ACRE', 'РАМАТ-ГАН', 'RAMAT GAN',
        'БНЕЙ-БРАК', 'BNEI BRAK', 'ЦФАТ', 'SAFED', 'ТВЕРИЯ', 'TIBERIAS', 'ГЕРЦЛИЯ', 'HERZLIYA'
    ]
    
    processed_words = set()
    
    # 1. ПЕРВЫЙ ПРОХОД: Ищем "от [имя]" для SubmittedBy
    import re
    match = re.search(r'от\s+([А-ЯЁA-Z][А-Яа-яёA-Za-z\s]+?)(?:\s*\+|\s*$)', text, re.IGNORECASE)
    if match:
        data['SubmittedBy'] = match.group(1).strip()
        # Отмечаем все слова фразы как обработанные
        from_phrase = match.group(0)
        for word in from_phrase.split():
            processed_words.add(word)
    
    # 2. ВТОРОЙ ПРОХОД: Ищем контакты
    for word in all_words:
        if word in processed_words:
            continue
        if ('@' in word or 
            (word.startswith(('+', '8', '7')) and len(word) > 5) or
            (word.replace('+', '').replace('-', '').replace('(', '').replace(')', '').replace(' ', '').isdigit() and len(word) > 7)):
            data['ContactInformation'] = word
            processed_words.add(word)
            break
    
    # 3. ТРЕТИЙ ПРОХОД: Ищем простые поля (пол, размер, роль, департамент, города)
    for word in all_words:
        if word in processed_words:
            continue
            
        word_upper = word.upper()
        
        # Проверяем пол
        for gender, keywords in gender_keywords.items():
            if word_upper in keywords:
                data['Gender'] = gender
                processed_words.add(word)
                break
        else:
            # Проверяем размер
            if word_upper in sizes:
                data['Size'] = word_upper
                processed_words.add(word)
            # Проверяем роль
            elif any(keyword == word_upper for keyword in role_keywords['TEAM']):
                data['Role'] = 'TEAM'
                processed_words.add(word)
            elif any(keyword == word_upper for keyword in role_keywords['CANDIDATE']):
                data['Role'] = 'CANDIDATE'
                processed_words.add(word)
            # Проверяем департамент
            elif not contains_hebrew(word):
                dept_found = False
                for dept, keywords in department_keywords.items():
                    if any(keyword == word_upper for keyword in keywords):
                        data['Department'] = dept
                        processed_words.add(word)
                        dept_found = True
                        break
                
                # Проверяем города Израиля (только если департамент не найден)
                if not dept_found and word_upper in israel_cities:
                    data['CountryAndCity'] = word
                    processed_words.add(word)
    
    # 4. ЧЕТВЕРТЫЙ ПРОХОД: Ищем церковь (только после обработки ролей)
    for i, word in enumerate(all_words):
        if word in processed_words:
            continue
            
        word_upper = word.upper()
        
        if any(keyword in word_upper for keyword in church_keywords):
            church_words = []
            
            # Добавляем слово перед "церковь" если оно не обработано И НЕ содержит иврит
            if (i > 0 and 
                all_words[i-1] not in processed_words and 
                not contains_hebrew(all_words[i-1])):
                church_words.append(all_words[i-1])
                processed_words.add(all_words[i-1])
            
            # Добавляем само слово "церковь"
            church_words.append(word)
            processed_words.add(word)
            
            # Добавляем следующее слово только если оно не обработано И НЕ содержит иврит
            if (i < len(all_words) - 1 and 
                all_words[i+1] not in processed_words and 
                not contains_hebrew(all_words[i+1])):
                church_words.append(all_words[i+1])
                processed_words.add(all_words[i+1])
            
            data['Church'] = ' '.join(church_words)
            break
    
    # 5. ПЯТЫЙ ПРОХОД: Собираем имена из оставшихся слов
    unprocessed_words = [word for word in all_words if word not in processed_words]
    
    russian_words = []
    english_words = []
    
    for word in unprocessed_words:
        # Если слово содержит только латинские буквы
        if word.isalpha() and all(ord(c) < 128 for c in word):
            english_words.append(word)
        else:
            russian_words.append(word)
    
    # Заполняем имена
    if russian_words:
        data['FullNameRU'] = ' '.join(russian_words[:2])
    
    if english_words:
        data['FullNameEN'] = ' '.join(english_words[:2])
    
    return data

# Команда /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    role = get_user_role(user_id)
    
    if role == "unauthorized":
        await update.message.reply_text(
            "❌ У вас нет доступа к этому боту.\n"
            "Обратитесь к координатору для получения прав."
        )
        return
    
    welcome_text = f"""
🏕️ **Добро пожаловать в бот Tres Dias Israel!**

👤 Ваша роль: **{role.title()}**

📋 **Доступные команды:**
/add - Добавить участника
/edit - Редактировать участника  
/delete - Удалить участника
/list - Список участников
/export - Экспорт данных
/help - Справка по командам

🚀 Выберите команду для начала работы.
    """
    
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

# Команда /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    role = get_user_role(user_id)
    
    if role == "unauthorized":
        await update.message.reply_text("❌ У вас нет доступа к этому боту.")
        return
    
    help_text = """
📖 **Справка по командам:**

👥 **Управление участниками:**
/add - Добавить нового участника
/edit - Редактировать данные участника
/delete - Удалить участника

📊 **Просмотр данных:**
/list - Показать список участников
/export - Экспорт данных в CSV

❓ **Помощь:**
/help - Показать эту справку
/start - Главное меню
/cancel - Отменить текущую операцию

🔍 **Примеры запросов (скоро):**
"Сколько team-member в worship?"
"Кто живет в комнате 203A?"
    """
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

# Команда /add
# Команда /add
async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    role = get_user_role(user_id)
    
    if role != "coordinator":
        await update.message.reply_text("❌ Только координаторы могут добавлять участников.")
        return
    
    context.user_data['waiting_for_participant'] = True
    
    template_text = """
➕ **Добавление участника**

🔴 **ОБЯЗАТЕЛЬНЫЕ ПОЛЯ:**
- Полное имя на русском
- Пол (M/F, муж/жен)
- Размер одежды (XS, S, M, L, XL, XXL)
- Церковь
- Роль (CANDIDATE/кандидат или TEAM/команда)
- Департамент (только для TEAM): Worship, Media, Kitchen, Setup, ROE, Chapel, Palanka, Administration, Decoration, Bell, Refreshment, Духовенство, Ректорат

🟡 **ОПЦИОНАЛЬНЫЕ:**
- Полное имя на английском
- Город и страна
- Кто подал заявку
- Контактная информация (телефон, email)

🤖 **Можете писать в любом формате** - бот попытается понять и покажет результат для подтверждения.

❌ /cancel для отмены
    """
    
    await update.message.reply_text(template_text, parse_mode='Markdown')
# Команда /edit
async def edit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    role = get_user_role(user_id)
    
    if role != "coordinator":
        await update.message.reply_text("❌ Только координаторы могут редактировать участников.")
        return
    
    await update.message.reply_text(
        "✏️ **Редактирование участника** (заглушка)\n\n"
        "🔧 Функция в разработке.\n"
        "Пример: /edit 123 - редактировать участника с ID 123",
        parse_mode='Markdown'
    )

# Команда /delete
async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    role = get_user_role(user_id)
    
    if role != "coordinator":
        await update.message.reply_text("❌ Только координаторы могут удалять участников.")
        return
    
    await update.message.reply_text(
        "🗑️ **Удаление участника** (заглушка)\n\n"
        "🔧 Функция в разработке.\n"
        "Пример: /delete 123 - удалить участника с ID 123",
        parse_mode='Markdown'
    )

# Команда /list
async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    role = get_user_role(user_id)
    
    if role == "unauthorized":
        await update.message.reply_text("❌ У вас нет доступа к этому боту.")
        return
    
    # Получаем участников из базы данных
    participants = get_all_participants()
    
    if not participants:
        await update.message.reply_text("📋 **Список участников пуст**\n\nИспользуйте /add для добавления участников.", parse_mode='Markdown')
        return
    
    # Формируем список участников
    message = f"📋 **Список участников ({len(participants)} чел.):**\n\n"
    
    for p in participants:
        role_emoji = "👤" if p['Role'] == 'CANDIDATE' else "👨‍💼"
        department = f" ({p['Department']})" if p['Department'] else ""
        
        message += f"{role_emoji} **{p['FullNameRU']}**\n"
        message += f"   • Роль: {p['Role']}{department}\n"
        message += f"   • ID: {p['id']}\n\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

# Команда /export
async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    role = get_user_role(user_id)
    
    if role == "unauthorized":
        await update.message.reply_text("❌ У вас нет доступа к этому боту.")
        return
    
    await update.message.reply_text(
        "📤 **Экспорт данных** (заглушка)\n\n"
        "🔧 Функция в разработке.\n"
        "Пример: /export worship team - экспорт участников worship команды",
        parse_mode='Markdown'
    )

# Команда /cancel
async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Все операции отменены.\n\nИспользуйте /help для справки.")
    
# Обработка и подтверждение данных участника
async def process_participant_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    # Парсим данные
    participant_data = parse_participant_data(text)
    
    # Проверяем на дублирование
    existing_participant = find_participant_by_name(participant_data['FullNameRU'])
    
    if existing_participant:
        # Найден дубль
        context.user_data['parsed_participant'] = participant_data
        context.user_data['waiting_for_participant'] = False
        context.user_data['confirming_duplicate'] = True
        
        duplicate_warning = f"""
⚠️ **ВНИМАНИЕ: Участник уже существует!**

🆔 **Существующий участник (ID: {existing_participant['id']}):**
👤 Имя: {existing_participant['FullNameRU']}
⚥ Пол: {existing_participant['Gender']}
👥 Роль: {existing_participant['Role']}
⛪ Церковь: {existing_participant['Church']}

🔄 **Новые данные:**
👤 Имя: {participant_data['FullNameRU']}
⚥ Пол: {participant_data['Gender']}
👥 Роль: {participant_data['Role']}
⛪ Церковь: {participant_data['Church']}

❓ **Что делать?**
- **ДА** - добавить как нового участника (возможен дубль)
- **НЕТ** - отменить добавление
- **ЗАМЕНИТЬ** - заменить существующего участника новыми данными

❌ /cancel для полной отмены
        """
        
        await update.message.reply_text(duplicate_warning, parse_mode='Markdown')
        return
    
    # Дублей нет - показываем обычное подтверждение
    context.user_data['parsed_participant'] = participant_data
    context.user_data['waiting_for_participant'] = False
    context.user_data['confirming_participant'] = True
    
    # Формируем сообщение подтверждения
    confirmation_text = f"""
🔍 **Вот что я понял из ваших данных:**

👤 **Имя (рус):** {participant_data['FullNameRU'] or '❌ Не указано'}
🌍 **Имя (англ):** {participant_data['FullNameEN'] or '➖ Не указано'}
⚥ **Пол:** {participant_data['Gender']}
👕 **Размер:** {participant_data['Size'] or '❌ Не указано'}
⛪ **Церковь:** {participant_data['Church'] or '❌ Не указано'}
👥 **Роль:** {participant_data['Role']}"""

    # Показываем департамент только для TEAM
    if participant_data['Role'] == 'TEAM':
        confirmation_text += f"\n🏢 **Департамент:** {participant_data['Department'] or '❌ Не указано (обязательно для TEAM)'}"
    
    confirmation_text += f"""
🏙️ **Город:** {participant_data['CountryAndCity'] or '➖ Не указано'}
👨‍💼 **Кто подал:** {participant_data['SubmittedBy'] or '➖ Не указано'}
📞 **Контакты:** {participant_data['ContactInformation'] or '➖ Не указано'}

✅ **Всё правильно?**
- Отправьте **ДА** для сохранения
- Отправьте **НЕТ** для отмены
- Или пришлите исправленные данные по темплейту

❌ /cancel для полной отмены
    """
    
    await update.message.reply_text(confirmation_text, parse_mode='Markdown')

# Обработка неизвестных команд и текстовых сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    role = get_user_role(user_id)
    
    if role == "unauthorized":
        await update.message.reply_text("❌ У вас нет доступа к этому боту.")
        return
    
    message_text = update.message.text.strip()
    
    # Проверяем режим ожидания данных участника
    if context.user_data.get('waiting_for_participant'):
        await process_participant_confirmation(update, context, message_text)
        return
    
    # Проверяем режим подтверждения
    if context.user_data.get('confirming_participant'):
        await handle_participant_confirmation(update, context, message_text)
        return
    
    # Проверяем режим подтверждения дублей
    if context.user_data.get('confirming_duplicate'):
        await handle_participant_confirmation(update, context, message_text)
        return
    
    # В будущем здесь будет NLP обработка
    await update.message.reply_text(
        f"🤖 Получено сообщение: \"{message_text}\"\n\n"
        "🔧 NLP обработка в разработке.\n"
        "Пока используйте команды: /help для справки.",
        parse_mode='Markdown'
    )
    
# Обработка подтверждения пользователя
async def handle_participant_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    text_upper = text.upper()
    
    # Обработка дублей
    if context.user_data.get('confirming_duplicate'):
        participant_data = context.user_data['parsed_participant']
        
        if text_upper in ['ДА', 'YES', 'Y', 'ОК', 'OK', '+']:
            # Добавляем как нового участника несмотря на дубль
            participant_id = add_participant(participant_data)
            context.user_data.clear()
            
            await update.message.reply_text(
                f"✅ **Участник добавлен как новый (возможен дубль)**\n\n"
                f"🆔 ID: {participant_id}\n"
                f"👤 Имя: {participant_data['FullNameRU']}\n\n"
                f"⚠️ Обратите внимание на возможное дублирование!",
                parse_mode='Markdown'
            )
            
        elif text_upper in ['ЗАМЕНИТЬ', 'REPLACE', 'ОБНОВИТЬ', 'UPDATE']:
            # Находим существующего участника и обновляем
            existing = find_participant_by_name(participant_data['FullNameRU'])
            if existing:
                updated = update_participant(existing['id'], participant_data)
                context.user_data.clear()
                
                if updated:
                    await update.message.reply_text(
                        f"🔄 **Участник обновлен!**\n\n"
                        f"🆔 ID: {existing['id']}\n"
                        f"👤 Имя: {participant_data['FullNameRU']}\n"
                        f"👥 Роль: {participant_data['Role']}\n\n"
                        f"📋 Данные заменены новыми значениями",
                        parse_mode='Markdown'
                    )
                else:
                    await update.message.reply_text("❌ Ошибка обновления участника.")
            
        elif text_upper in ['НЕТ', 'NO', 'N', '-']:
            # Отменяем добавление
            context.user_data.clear()
            await update.message.reply_text(
                "❌ Добавление участника отменено из-за дублирования.\n\n"
                "Используйте /add для повторной попытки."
            )
        else:
            await update.message.reply_text(
                "❓ Не понял ответ. Отправьте:\n"
                "• **ДА** - добавить дубль\n"
                "• **НЕТ** - отменить\n"
                "• **ЗАМЕНИТЬ** - обновить существующего"
            )
        return
    
    # Обычное подтверждение (без дублей)
    if text_upper in ['ДА', 'YES', 'Y', 'ОК', 'OK', '+']:
        # Сохраняем участника
        participant_data = context.user_data['parsed_participant']
        
        participant_id = add_participant(participant_data)
        
        # Очищаем состояние
        context.user_data.clear()
        
        # Формируем полный ответ о добавленном участнике
        success_text = f"✅ **Участник успешно добавлен!**\n\n🆔 **ID:** {participant_id}\n"
        success_text += f"👤 **Имя:** {participant_data['FullNameRU']}\n"
        success_text += f"⚥ **Пол:** {participant_data['Gender']}\n"
        success_text += f"👕 **Размер:** {participant_data['Size']}\n"
        success_text += f"⛪ **Церковь:** {participant_data['Church']}\n"
        success_text += f"👥 **Роль:** {participant_data['Role']}\n"

        if participant_data['Role'] == 'TEAM':
            success_text += f"🏢 **Департамент:** {participant_data['Department']}\n"

        if participant_data['SubmittedBy']:
            success_text += f"👨‍💼 **Кто подал:** {participant_data['SubmittedBy']}\n"

        if participant_data['ContactInformation']:
            success_text += f"📞 **Контакты:** {participant_data['ContactInformation']}\n"

        success_text += f"\n📋 Используйте /list для просмотра всех участников"

        await update.message.reply_text(success_text, parse_mode='Markdown')
        
    elif text_upper in ['НЕТ', 'NO', 'N', '-']:
        # Отменяем добавление
        context.user_data.clear()
        await update.message.reply_text(
            "❌ Добавление участника отменено.\n\n"
            "Используйте /add для повторной попытки."
        )
        
    else:
        # Пользователь прислал новые данные для исправления
        await process_participant_confirmation(update, context, text)

# Обработка ошибок
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

# Основная функция
def main():
    # Инициализируем базу данных
    init_database()
    
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("add", add_command))
    application.add_handler(CommandHandler("edit", edit_command))
    application.add_handler(CommandHandler("delete", delete_command))
    application.add_handler(CommandHandler("list", list_command))
    application.add_handler(CommandHandler("export", export_command))
    application.add_handler(CommandHandler("cancel", cancel_command))
    
    # Обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)
    
    print(f"🤖 Бот @{BOT_USERNAME} запущен!")
    print("🔄 Polling started...")
    
    # Запускаем бота
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()