import logging
from logging.handlers import RotatingFileHandler
import re
from typing import List, Dict, Optional
from dataclasses import asdict
from telegram import Update
from functools import wraps
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from config import BOT_TOKEN, BOT_USERNAME, COORDINATOR_IDS, VIEWER_IDS
from utils.decorators import require_role
from utils.cache import load_reference_data
from database import init_database
from repositories.participant_repository import SqliteParticipantRepository
from services.participant_service import ParticipantService
from parsers.participant_parser import (
    parse_participant_data,
    is_template_format,
    parse_template_format,
    parse_unstructured_text,
    normalize_field_value,
)
from services.participant_service import (
    merge_participant_data,
    format_participant_block,
    detect_changes,
    get_edit_keyboard,
    FIELD_LABELS,
)
from utils.validators import validate_participant_data
from utils.exceptions import (
    BotException,
    ParticipantNotFoundError,
    ValidationError,
)
from messages import MESSAGES
from states import CONFIRMING_DATA, CONFIRMING_DUPLICATE, COLLECTING_DATA


def cleanup_on_error(func):
    """Декоратор для автоматической очистки состояния пользователя при ошибках."""

    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        try:
            return await func(update, context, *args, **kwargs)
        except Exception as e:
            user_id = update.effective_user.id if update.effective_user else "unknown"
            logger.error(
                f"Error in {func.__name__} for user {user_id}: {type(e).__name__}: {e}",
                exc_info=True,
            )

            cleanup_user_data_safe(context, update.effective_user.id)
            logger.info(f"Cleared user_data for user {user_id} due to error in {func.__name__}")

            try:
                if update.message:
                    await update.message.reply_text(
                        "❌ **Произошла ошибка при обработке данных.**\n\n"
                        "🔄 Попробуйте снова с команды /add\n"
                        "📞 Если проблема повторяется, обратитесь к администратору.",
                        parse_mode='Markdown',
                    )
                elif update.callback_query:
                    await update.callback_query.answer()
                    await update.callback_query.message.reply_text(
                        "❌ **Произошла ошибка при обработке данных.**\n\n"
                        "🔄 Попробуйте снова с команды /add",
                        parse_mode='Markdown',
                    )
            except Exception as send_error:
                logger.error(f"Failed to send error message to user {user_id}: {send_error}")

            return ConversationHandler.END

    return wrapper


def cleanup_user_data_safe(context: ContextTypes.DEFAULT_TYPE, user_id: int = None):
    """Безопасная очистка user_data с логированием."""

    if context.user_data:
        keys_to_clear = list(context.user_data.keys())
        context.user_data.clear()
        logger.info(
            f"Manually cleared user_data for user {user_id or 'unknown'}: removed keys {keys_to_clear}"
        )
    else:
        logger.debug(f"user_data already empty for user {user_id or 'unknown'}")

# Настройка логирования
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
handler = RotatingFileHandler('bot.log', maxBytes=10*1024*1024, backupCount=5)
handler.setFormatter(logging.Formatter(LOG_FORMAT))
logging.basicConfig(level=logging.INFO, handlers=[handler], format=LOG_FORMAT)
logger = logging.getLogger(__name__)

# Отдельный лог для SQL-запросов
sql_handler = RotatingFileHandler('sql.log', maxBytes=10*1024*1024, backupCount=5)
sql_handler.setFormatter(logging.Formatter(LOG_FORMAT))
sql_logger = logging.getLogger('sql')
sql_logger.setLevel(logging.INFO)
sql_logger.addHandler(sql_handler)

# Initialize repository and service instances
participant_repository = SqliteParticipantRepository()
participant_service = ParticipantService(repository=participant_repository)

# --- REQUIRED AND OPTIONAL FIELDS ---
REQUIRED_FIELDS = ['FullNameRU', 'Gender', 'Size', 'Church', 'Role']
OPTIONAL_FIELDS = ['FullNameEN', 'CountryAndCity', 'SubmittedBy', 'ContactInformation', 'Department']


# Функция проверки прав пользователя
def get_user_role(user_id):
    if user_id in COORDINATOR_IDS:
        return "coordinator"
    elif user_id in VIEWER_IDS:
        return "viewer"
    else:
        return "unauthorized"


async def show_confirmation(update: Update, participant_data: Dict) -> None:
    """Отправляет сообщение с данными участника и клавиатурой для редактирования."""
    confirmation_text = "🔍 Вот что удалось распознать. Всё правильно?\n\n"
    confirmation_text += format_participant_block(participant_data)
    confirmation_text += "\n\n✅ Отправьте **ДА** для сохранения или **НЕТ** для отмены."
    confirmation_text += "\n\n✏️ **Чтобы исправить поле, нажмите на кнопку ниже.**"

    keyboard = get_edit_keyboard(participant_data)

    await update.message.reply_text(
        confirmation_text,
        parse_mode='Markdown',
        reply_markup=keyboard,
    )

# --- HELPER FUNCTIONS (NEW) ---

def get_missing_fields(participant_data: Dict) -> List[str]:
    """Checks for missing required fields."""
    missing = []
    for field in REQUIRED_FIELDS:
        if not participant_data.get(field):
            missing.append(FIELD_LABELS.get(field, field))

    if participant_data.get('Role') == 'TEAM' and not participant_data.get('Department'):
        missing.append(FIELD_LABELS.get('Department', 'Department'))
    return missing


def format_status_message(participant_data: Dict) -> str:
    """Creates a status message with filled data and missing fields."""
    message = "📝 **Процесс добавления:**\n\n"
    message += format_participant_block(participant_data)
    message += "\n\n"

    missing = get_missing_fields(participant_data)
    if missing:
        message += "🔴 **Осталось заполнить:**\n- " + "\n- ".join(missing)
        message += "\n\nОтправьте данные для одного из этих полей или отправьте /cancel для отмены."
    else:
        message += "✅ **Все обязательные поля заполнены!**\n\n"
        message += "Отправьте **ДА** для подтверждения или **НЕТ** для отмены."

    return message

# Команда /start
@require_role("viewer")
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    role = get_user_role(user_id)
    logger.info("User %s started /start", user_id)
    
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
@require_role("viewer")
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    role = get_user_role(user_id)
    logger.info("User %s requested help", user_id)
    
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
@require_role("coordinator")
@cleanup_on_error
async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the /add flow and initializes the session."""
    user_id = update.effective_user.id
    logger.info("User %s started add participant", user_id)

    context.user_data['add_flow_data'] = {
        'FullNameRU': None,
        'Gender': None,
        'Size': None,
        'Church': None,
        'Role': None,
        'Department': None,
        'FullNameEN': None,
        'CountryAndCity': None,
        'SubmittedBy': None,
        'ContactInformation': None,
    }

    await update.message.reply_text(
        "🚀 **Начинаем добавлять нового участника.**\n\n"
        "Отправьте данные любым удобным способом:\n"
        "1️⃣ **Вставьте заполненный шаблон** (пришлю его следующим сообщением).\n"
        "2️⃣ **Отправьте несколько полей**, разделяя их запятой (`,`) или каждое с новой строки.\n"
        "3️⃣ **Отправляйте по одному полю** в сообщении (например, `Церковь Грейс`).\n\n"
        "*Для самой точной обработки используйте запятые или ввод с новой строки.*\n"
        "Для отмены введите /cancel.",
        parse_mode='Markdown'
    )
    await update.message.reply_text(MESSAGES['ADD_TEMPLATE'])
    return COLLECTING_DATA


@require_role("coordinator")
@cleanup_on_error
async def handle_partial_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Collects and processes partial data, supporting multiple formats."""
    text = update.message.text.strip()
    participant_data = context.user_data.get('add_flow_data', {})

    # 1. Check if user pasted a full template (highest priority)
    if is_template_format(text):
        parsed_update = parse_template_format(text)
        for key, value in parsed_update.items():
            if value:
                participant_data[key] = value
    else:
        # 2. Try splitting by newline or comma to detect multiple fields
        chunks = []
        if "\n" in text:
            chunks = [c.strip() for c in text.split("\n") if c.strip()]
        elif "," in text:
            chunks = [c.strip() for c in text.split(",") if c.strip()]
        else:
            chunks = [text]

        # Parse each chunk separately
        for chunk in chunks:
            if not chunk:
                continue

            if ':' in chunk:
                parsed_chunk = parse_participant_data(chunk, is_update=True)
            else:
                parsed_chunk = parse_unstructured_text(chunk)

            for key, value in parsed_chunk.items():
                if value:
                    participant_data[key] = value

    # --- NAME DUPLICATE CHECK BLOCK ---
    newly_identified_name = participant_data.get('FullNameRU')
    if newly_identified_name and not context.user_data.get('participant_id'):
        existing_participant = participant_service.check_duplicate(newly_identified_name)
        if existing_participant:
            context.user_data['participant_id'] = existing_participant.id
            existing_dict = asdict(existing_participant)
            context.user_data['add_flow_data'] = existing_dict
            context.user_data['parsed_participant'] = existing_dict
            await update.message.reply_text(
                f"ℹ️ Участник с именем '{newly_identified_name}' уже существует. Переключаюсь в режим редактирования."
            )
            await show_confirmation(update, existing_dict)
            return CONFIRMING_DATA

    context.user_data['add_flow_data'] = participant_data

    missing_fields = get_missing_fields(participant_data)

    if not missing_fields:
        context.user_data['parsed_participant'] = participant_data
        await show_confirmation(update, participant_data)
        return CONFIRMING_DATA
    else:
        status_message = format_status_message(participant_data)
        await update.message.reply_text(status_message, parse_mode='Markdown')
        return COLLECTING_DATA
# Команда /edit
@require_role("coordinator")
async def edit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    role = get_user_role(user_id)
    logger.info("User %s started edit participant", user_id)
    
    await update.message.reply_text(
        "✏️ **Редактирование участника** (заглушка)\n\n"
        "🔧 Функция в разработке.\n"
        "Пример: /edit 123 - редактировать участника с ID 123",
        parse_mode='Markdown'
    )

# Команда /delete
@require_role("coordinator")
async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    role = get_user_role(user_id)
    logger.info("User %s started delete participant", user_id)
    
    await update.message.reply_text(
        "🗑️ **Удаление участника** (заглушка)\n\n"
        "🔧 Функция в разработке.\n"
        "Пример: /delete 123 - удалить участника с ID 123",
        parse_mode='Markdown'
    )

@require_role("coordinator")
async def edit_field_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    ✅ НОВАЯ КОМАНДА: Демонстрация частичного обновления полей.

    Использование: /edit_field 123 FullNameRU "Новое имя"
    """
    try:
        parts = update.message.text.split(' ', 3)
        if len(parts) < 4:
            await update.message.reply_text(
                "❌ **Использование:** /edit_field ID поле значение\n\n"
                "**Пример:** /edit_field 123 FullNameRU \"Новое имя\"",
                parse_mode='Markdown'
            )
            return

        _, participant_id, field_name, new_value = parts
        participant_id = int(participant_id)

        if not participant_service.participant_exists(participant_id):
            await update.message.reply_text(f"❌ Участник с ID {participant_id} не найден")
            return

        kwargs = {field_name: new_value}
        success = participant_service.update_participant_fields(participant_id, **kwargs)

        if success:
            await update.message.reply_text(
                f"✅ **Поле обновлено!**\n\n"
                f"🆔 ID: {participant_id}\n"
                f"📝 Поле: {field_name}\n"
                f"🔄 Новое значение: {new_value}",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ Ошибка при обновлении поля")

    except ValueError as e:
        await update.message.reply_text(f"❌ Ошибка валидации: {e}")
    except ParticipantNotFoundError as e:
        await update.message.reply_text(f"❌ {e}")
    except Exception as e:
        logger.error("Error in edit_field_command: %s", e)
        await update.message.reply_text("❌ Произошла ошибка при обновлении поля")

# Команда /list
@require_role("viewer")
async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    role = get_user_role(user_id)
    logger.info("User %s requested participants list", user_id)
    
    # ✅ ИСПРАВЛЕНИЕ: используем новый service для получения списка
    participants = participant_service.get_all_participants()
    
    if not participants:
        await update.message.reply_text("📋 **Список участников пуст**\n\nИспользуйте /add для добавления участников.", parse_mode='Markdown')
        return
    
    # Формируем список участников
    message = f"📋 **Список участников ({len(participants)} чел.):**\n\n"
    
    for p in participants:
        role_emoji = "👤" if p.Role == 'CANDIDATE' else "👨‍💼"
        department = f" ({p.Department})" if p.Role == 'TEAM' and p.Department else ""

        message += f"{role_emoji} **{p.FullNameRU}**\n"
        message += f"   • Роль: {p.Role}{department}\n"
        message += f"   • ID: {p.id}\n\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

# Команда /export
@require_role("viewer")
async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    role = get_user_role(user_id)
    logger.info("User %s requested export", user_id)
    
    await update.message.reply_text(
        "📤 **Экспорт данных** (заглушка)\n\n"
        "🔧 Функция в разработке.\n"
        "Пример: /export worship team - экспорт участников worship команды",
        parse_mode='Markdown'
    )

# Команда /cancel
@require_role("viewer")
async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if 'add_flow_data' in context.user_data:
        context.user_data.clear()
        logger.info("User %s cancelled the add flow.", update.effective_user.id)
        await update.message.reply_text("❌ Добавление отменено.")
    else:
        logger.info("User %s cancelled a non-existent operation.", update.effective_user.id)
        await update.message.reply_text("❌ Нет активной операции для отмены.")

    return ConversationHandler.END
    
# Обработка и подтверждение данных участника
async def process_participant_confirmation(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    is_update: bool = False,
) -> int:
    """Обрабатывает ввод пользователя на этапе подтверждения."""

    # Копия текста подтверждения или его части может приходить обратно от пользователя
    is_block = ('Имя (рус):' in text and 'Пол:' in text)
    if text.startswith('🔍') or 'Вот что я понял' in text or is_block:
        parsed = parse_template_format(text)
    else:
        parsed = parse_participant_data(text, is_update=is_update)

    # Определяем, является ли это точечным исправлением или массовым обновлением
    existing = context.user_data.get('parsed_participant', {}) if is_update else {}

    if is_update:
        participant_data = merge_participant_data(existing, parsed)
    else:
        participant_data = parsed
    
    valid, error = validate_participant_data(participant_data)
    if not valid:
        logger.error("Parsing error: %s | Text: %s", error, text)
        await update.message.reply_text(f"❌ {error}")
        return COLLECTING_DATA

    existing_participant = None
    if not is_update:
        existing_participant = participant_service.check_duplicate(
            participant_data['FullNameRU']
        )
    
    if existing_participant:
        # Найден дубль - объединяем старые и новые данные
        merged_data = merge_participant_data(existing_participant, participant_data)
        context.user_data['parsed_participant'] = merged_data
        context.user_data['duplicate'] = True
        
        duplicate_warning = f"""
⚠️ **ВНИМАНИЕ: Участник уже существует!**

🆔 **Существующий участник (ID: {existing_participant.id}):**
👤 Имя: {existing_participant.FullNameRU}
⚥ Пол: {existing_participant.Gender}
👥 Роль: {existing_participant.Role}
⛪ Церковь: {existing_participant.Church}

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
        return CONFIRMING_DUPLICATE

    if is_update:
        changes = detect_changes(existing, participant_data)
        if not changes:
            await update.message.reply_text(
                "Изменений не обнаружено. Напишите ДА или НЕТ."
            )
            return CONFIRMING_DATA

        context.user_data['parsed_participant'] = participant_data
        context.user_data['duplicate'] = False
        confirmation_text = (
            "🔄 **Исправление данных:**\n\n"
            "✏️ **Изменено:**\n" + "\n".join(changes) +
            "\n\n👤 **Итоговые данные:**\n" +
            format_participant_block(participant_data) +
            "\n\n✅ **Что делать дальше?**\n"
            "- Напишите **ДА** или **НЕТ**\n"
            "- Или пришлите новые исправления" +
            "\n\n✏️ **Чтобы исправить поле, нажмите на кнопку ниже.**"
        )

        keyboard = get_edit_keyboard(participant_data)

        await update.message.reply_text(
            confirmation_text,
            parse_mode='Markdown',
            reply_markup=keyboard,
        )
        return CONFIRMING_DATA
    
    # Дублей нет - показываем обычное подтверждение
    context.user_data['parsed_participant'] = participant_data
    context.user_data['duplicate'] = False
    
    await show_confirmation(update, participant_data)
    return CONFIRMING_DATA

# Обработка неизвестных команд и текстовых сообщений
@require_role("viewer")
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message_text = update.message.text.strip()
    logger.info("User %s sent message: %s", user_id, message_text)

    # Отладка состояния пользователя
    logger.info(f"User {user_id} state: {context.user_data}")
    
    # В будущем здесь будет NLP обработка
    await update.message.reply_text(
        f"🤖 Получено сообщение: \"{message_text}\"\n\n"
        "🔧 NLP обработка в разработке.\n"
        "Пока используйте команды: /help для справки.",
        parse_mode='Markdown'
    )
    
# Обработка подтверждения пользователя
@cleanup_on_error
async def handle_participant_confirmation(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    text = update.message.text.strip()
    logger.info("User %s confirmation message: %s", update.effective_user.id, text)

    field_to_edit = context.user_data.get('field_to_edit')
    if field_to_edit:
        new_value = text.strip()
        participant_data = context.user_data.get('parsed_participant', {})

        normalized_value = normalize_field_value(field_to_edit, new_value)

        participant_data[field_to_edit] = normalized_value

        context.user_data['parsed_participant'] = participant_data
        context.user_data.pop('field_to_edit')

        await show_confirmation(update, participant_data)
        return CONFIRMING_DATA
    # Если пользователь прислал блок подтверждения целиком
    if is_template_format(text):
        parsed = parse_template_format(text)
        existing = context.user_data.get('parsed_participant', {})
        participant_data = merge_participant_data(existing, parsed)
        changes = detect_changes(existing, participant_data)
        if not changes:
            await update.message.reply_text(
                "Изменений не обнаружено. Напишите ДА или НЕТ."
            )
            return CONFIRMING_DATA
        context.user_data['parsed_participant'] = participant_data
        await show_confirmation(update, participant_data)
        return CONFIRMING_DATA

    # Нормализуем текст ответа
    normalized = re.sub(r'[\s\.,!]', '', text.upper())

    if not normalized:
        await update.message.reply_text(
            "❓ Ответ не распознан. Напишите ДА или НЕТ или пришлите новые данные."
        )
        return CONFIRMING_DATA

    positive = ['ДА', 'YES', 'Y', 'ОК', 'OK', '+']
    negative = ['НЕТ', 'NO', 'N', '-', 'НИСТ', 'НИТ']
    
    def is_positive(txt: str) -> bool:
        return txt in positive or any(txt.startswith(p) for p in positive)

    def is_negative(txt: str) -> bool:
        return txt in negative or any(txt.startswith(n) for n in negative)

    # Обработка дублей
    if context.user_data.get('duplicate'):
        participant_data = context.user_data['parsed_participant']

        if is_positive(normalized):
            # Добавляем как нового участника несмотря на дубль
            try:
                participant_id = participant_service.add_participant(participant_data)
            except ValidationError as e:
                await update.message.reply_text(f"❌ Ошибка валидации: {e}")
                return ConversationHandler.END
            except ParticipantNotFoundError as e:  # unlikely here
                await update.message.reply_text(str(e))
                return ConversationHandler.END
            except BotException as e:
                logger.error("Error adding participant: %s", e)
                await update.message.reply_text(
                    "❌ Ошибка базы данных при добавлении участника."
                )
                return ConversationHandler.END
            cleanup_user_data_safe(context, update.effective_user.id)
            
            await update.message.reply_text(
                f"✅ **Участник добавлен как новый (возможен дубль)**\n\n"
                f"🆔 ID: {participant_id}\n"
                f"👤 Имя: {participant_data['FullNameRU']}\n\n"
                f"⚠️ Обратите внимание на возможное дублирование!",
                parse_mode='Markdown'
            )
            
        elif normalized in ['ЗАМЕНИТЬ', 'REPLACE', 'ОБНОВИТЬ', 'UPDATE']:
            # Находим существующего участника и обновляем
            existing = participant_service.check_duplicate(participant_data['FullNameRU'])
            if existing:
                try:
                    updated = participant_service.update_participant(existing.id, participant_data)
                except ValidationError as e:
                    await update.message.reply_text(f"❌ Ошибка валидации: {e}")
                    return ConversationHandler.END
                except ParticipantNotFoundError as e:
                    await update.message.reply_text(str(e))
                    return ConversationHandler.END
                except BotException as e:
                    logger.error("Error updating participant: %s", e)
                    await update.message.reply_text(
                        "❌ Ошибка базы данных при обновлении участника."
                    )
                    return ConversationHandler.END
                cleanup_user_data_safe(context, update.effective_user.id)
                
                if updated:
                    await update.message.reply_text(
                        f"🔄 **Участник обновлен!**\n\n"
                        f"🆔 ID: {existing.id}\n"
                        f"👤 Имя: {participant_data['FullNameRU']}\n"
                        f"👥 Роль: {participant_data['Role']}\n\n"
                        f"📋 Данные заменены новыми значениями",
                        parse_mode='Markdown'
                    )
                else:
                    await update.message.reply_text("❌ Ошибка обновления участника.")
            
        elif is_negative(normalized):
            # Отменяем добавление
            cleanup_user_data_safe(context, update.effective_user.id)
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
        return CONFIRMING_DUPLICATE
    
    # Обычное подтверждение (без дублей)
    if is_positive(normalized):
        participant_data = context.user_data.get('parsed_participant', {})
        participant_id = context.user_data.get('participant_id')

        try:
            if participant_id:
                participant_service.update_participant(participant_id, participant_data)
            else:
                participant_id = participant_service.add_participant(participant_data)
        except ValidationError as e:
            await update.message.reply_text(f"❌ Ошибка валидации: {e}")
            return ConversationHandler.END
        except ParticipantNotFoundError as e:
            await update.message.reply_text(str(e))
            return ConversationHandler.END
        except BotException as e:
            logger.error("Error saving participant: %s", e)
            await update.message.reply_text(
                "❌ Ошибка базы данных при сохранении участника."
            )
            return ConversationHandler.END

        was_update = bool(context.user_data.get('participant_id'))
        cleanup_user_data_safe(context, update.effective_user.id)

        success_text = (
            "✅ **Данные участника успешно обновлены!**"
            if was_update
            else "✅ **Участник успешно добавлен!**"
        )
        success_text += f"\n\n🆔 **ID:** {participant_id}\n"
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
        return ConversationHandler.END

    elif is_negative(normalized):
        # Отменяем добавление
        cleanup_user_data_safe(context, update.effective_user.id)
        await update.message.reply_text(
            "❌ Добавление участника отменено.\n\n"
            "Используйте /add для повторной попытки."
        )
        return ConversationHandler.END

    else:
        # Пользователь прислал новые данные для исправления
        return await process_participant_confirmation(update, context, text, is_update=True)


@cleanup_on_error
async def edit_field_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает нажатие на кнопку редактирования поля."""
    query = update.callback_query
    await query.answer()

    field_to_edit = query.data.split('_')[1]
    context.user_data['field_to_edit'] = field_to_edit

    await query.edit_message_text(
        text=f"Пришлите новое значение для поля **{field_to_edit}**",
        parse_mode='Markdown'
    )

    return CONFIRMING_DATA

# Обработка ошибок
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

# Основная функция
def main():
    # Инициализируем базу данных
    init_database()

    # Загружаем справочники в кэш
    load_reference_data()
    
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))

    add_conv = ConversationHandler(
        entry_points=[CommandHandler("add", add_command)],
        states={
            COLLECTING_DATA: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_partial_data)],
            CONFIRMING_DATA: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_participant_confirmation),
                CallbackQueryHandler(edit_field_callback, pattern="^edit_")
            ],
            CONFIRMING_DUPLICATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_participant_confirmation)],
        },
        fallbacks=[CommandHandler("cancel", cancel_command)],
    )

    application.add_handler(add_conv)
    application.add_handler(CommandHandler("edit", edit_command))
    application.add_handler(CommandHandler("edit_field", edit_field_command))
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
