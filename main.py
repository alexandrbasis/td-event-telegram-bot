import logging
import re
from typing import List, Dict, Optional
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from config import BOT_TOKEN, BOT_USERNAME, COORDINATOR_IDS, VIEWER_IDS
from database import (
    init_database,
    add_participant,
    get_all_participants,
    get_participant_by_id,
    find_participant_by_name,
    update_participant,
    update_participant_field,
)
from parsers.participant_parser import parse_participant_data
from utils.validators import validate_participant_data

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Сопоставление полей для сообщений об изменениях
FIELD_LABELS = {
    'FullNameRU': 'Имя (рус)',
    'FullNameEN': 'Имя (англ)',
    'Gender': 'Пол',
    'Size': 'Размер',
    'Church': 'Церковь',
    'Role': 'Роль',
    'Department': 'Департамент',
    'CountryAndCity': 'Город',
    'SubmittedBy': 'Кто подал',
    'ContactInformation': 'Контакты',
}

FIELD_EMOJIS = {
    'FullNameRU': '👤',
    'FullNameEN': '🌍',
    'Gender': '⚥',
    'Size': '👕',
    'Church': '⛪',
    'Role': '👥',
    'Department': '🏢',
    'CountryAndCity': '🏙️',
    'SubmittedBy': '👨‍💼',
    'ContactInformation': '📞',
}


def merge_participant_data(existing_data: Dict, updates: Dict) -> Dict:
    """Объединяет существующие данные участника с обновлениями"""
    merged = existing_data.copy()
    for key, value in updates.items():
        if value:
            merged[key] = value
    return merged


def parse_confirmation_template(text: str) -> Dict:
    """Извлекает данные из скопированного блока подтверждения."""
    import re

    FIELD_MAPPING = {
        'Имя (рус)': 'FullNameRU',
        'Имя (англ)': 'FullNameEN',
        'Пол': 'Gender',
        'Размер': 'Size',
        'Церковь': 'Church',
        'Роль': 'Role',
        'Департамент': 'Department',
        'Город': 'CountryAndCity',
        'Кто подал': 'SubmittedBy',
        'Контакты': 'ContactInformation',
    }

    prefix_re = re.compile(r'^[🌍👤⚥👕⛪👥🏢🏙️👨‍💼📞\*\s]+(.+)$')
    kv_re = re.compile(r'^(?P<key>.+?):\s*(?P<value>.+)$')

    data: Dict = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        line = line.replace('**', '')

        m_pref = prefix_re.match(line)
        if m_pref:
            line = m_pref.group(1).strip()

        m_kv = kv_re.match(line)
        if not m_kv:
            continue

        key = m_kv.group('key').strip()
        value = m_kv.group('value').strip()

        if re.search(r'[❌➖]|Не указано', value):
            value = ''

        field = FIELD_MAPPING.get(key)
        if field:
            data[field] = value

    return data


def format_participant_block(data: Dict) -> str:
    text = (
        f"👤 **Имя (рус):** {data.get('FullNameRU') or '❌ Не указано'}\n"
        f"🌍 **Имя (англ):** {data.get('FullNameEN') or '➖ Не указано'}\n"
        f"⚥ **Пол:** {data.get('Gender')}\n"
        f"👕 **Размер:** {data.get('Size') or '❌ Не указано'}\n"
        f"⛪ **Церковь:** {data.get('Church') or '❌ Не указано'}\n"
        f"👥 **Роль:** {data.get('Role')}"
    )
    if data.get('Role') == 'TEAM':
        text += f"\n🏢 **Департамент:** {data.get('Department') or '❌ Не указано (обязательно для TEAM)'}"
    text += (
        f"\n🏙️ **Город:** {data.get('CountryAndCity') or '➖ Не указано'}\n"
        f"👨‍💼 **Кто подал:** {data.get('SubmittedBy') or '➖ Не указано'}\n"
        f"📞 **Контакты:** {data.get('ContactInformation') or '➖ Не указано'}"
    )
    return text

# Функция проверки прав пользователя
def get_user_role(user_id):
    if user_id in COORDINATOR_IDS:
        return "coordinator"
    elif user_id in VIEWER_IDS:
        return "viewer"
    else:
        return "unauthorized"

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
async def process_participant_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, is_update: bool = False):
    """Обрабатывает ввод пользователя на этапе подтверждения."""

    # Копия текста подтверждения может приходить обратно от пользователя
    if text.startswith('🔍') or 'Вот что я понял' in text:
        parsed = parse_confirmation_template(text)
        is_update = False
    else:
        parsed = parse_participant_data(text, is_update=is_update)

    # Определяем, является ли это точечным исправлением
    partial_update = is_update and 0 < len(parsed) <= 2

    if partial_update:
        if not parsed:
            await update.message.reply_text(
                "Не понял что изменить. Попробуйте: 'Пол женский' или 'Размер M'"
            )
            return
        existing = context.user_data.get('parsed_participant', {})
        participant_data = merge_participant_data(existing, parsed)
    else:
        participant_data = parsed
    
    valid, error = validate_participant_data(participant_data)
    if not valid:
        await update.message.reply_text(f"❌ {error}")
        return

    existing_participant = None
    if not is_update:
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

    if partial_update:
        changes = []
        for field, new_value in parsed.items():
            old_value = existing.get(field, '')
            if old_value != new_value:
                label = FIELD_LABELS.get(field, field)
                emoji = FIELD_EMOJIS.get(field, '')
                changes.append(f"{emoji} **{label}:** {old_value or '—'} → {new_value}")

        context.user_data['parsed_participant'] = participant_data
        context.user_data['waiting_for_participant'] = False
        context.user_data['confirming_participant'] = True

        confirmation_text = (
            "🔄 **Исправление данных:**\n\n"
            "✏️ **Изменено:**\n" + "\n".join(changes) +
            "\n\n👤 **Итоговые данные:**\n" +
            format_participant_block(participant_data) +
            "\n\n✅ **Что делать дальше?**\n"
            "- Напишите **ДА** или **НЕТ**\n"
            "- Или пришлите новые исправления"
        )

        await update.message.reply_text(confirmation_text, parse_mode='Markdown')
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

    # Отладка состояния пользователя
    logger.info(f"User {user_id} state: {context.user_data}")
    
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
    # Нормализуем текст ответа
    normalized = re.sub(r'[\s\.,!]', '', text.upper())

    if not normalized:
        await update.message.reply_text(
            "❓ Ответ не распознан. Напишите ДА или НЕТ или пришлите новые данные."
        )
        return

    positive = ['ДА', 'YES', 'Y', 'ОК', 'OK', '+']
    negative = ['НЕТ', 'NO', 'N', '-', 'НИСТ', 'НИТ']
    
    def is_positive(txt: str) -> bool:
        return txt in positive or any(txt.startswith(p) for p in positive)

    def is_negative(txt: str) -> bool:
        return txt in negative or any(txt.startswith(n) for n in negative)

    # Обработка дублей
    if context.user_data.get('confirming_duplicate'):
        participant_data = context.user_data['parsed_participant']

        if is_positive(normalized):
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
            
        elif normalized in ['ЗАМЕНИТЬ', 'REPLACE', 'ОБНОВИТЬ', 'UPDATE']:
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
            
        elif is_negative(normalized):
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
    if is_positive(normalized):
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
        
    elif is_negative(normalized):
        # Отменяем добавление
        context.user_data.clear()
        await update.message.reply_text(
            "❌ Добавление участника отменено.\n\n"
            "Используйте /add для повторной попытки."
        )
        
    else:
        # Пользователь прислал новые данные для исправления
        await process_participant_confirmation(update, context, text, is_update=True)

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