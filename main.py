import logging
import re
from typing import List, Dict, Optional
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from config import BOT_TOKEN, BOT_USERNAME, COORDINATOR_IDS, VIEWER_IDS
from utils.decorators import require_role
from utils.cache import load_reference_data
from database import (
    init_database,
    add_participant,
    get_all_participants,
    get_participant_by_id,
    update_participant,
    update_participant_field,
)
from parsers.participant_parser import (
    parse_participant_data,
    is_template_format,
    parse_template_format,
)
from services.participant_service import (
    merge_participant_data,
    format_participant_block,
    detect_changes,
    check_duplicate,
)
from utils.validators import validate_participant_data
from utils.exceptions import (
    BotException,
    ParticipantNotFoundError,
    ValidationError,
)
from messages import MESSAGES

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

# Команда /start
@require_role("viewer")
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    role = get_user_role(user_id)
    
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
@require_role("coordinator")
async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    role = get_user_role(user_id)
    
    context.user_data['waiting_for_participant'] = True

    description_text = MESSAGES['ADD_DESCRIPTION']
    template_block = MESSAGES['ADD_TEMPLATE']

    await update.message.reply_text(description_text, parse_mode='Markdown')
    await update.message.reply_text(template_block)
# Команда /edit
@require_role("coordinator")
async def edit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    role = get_user_role(user_id)
    
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
    
    await update.message.reply_text(
        "🗑️ **Удаление участника** (заглушка)\n\n"
        "🔧 Функция в разработке.\n"
        "Пример: /delete 123 - удалить участника с ID 123",
        parse_mode='Markdown'
    )

# Команда /list
@require_role("viewer")
async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    role = get_user_role(user_id)
    
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
@require_role("viewer")
async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    role = get_user_role(user_id)
    
    await update.message.reply_text(
        "📤 **Экспорт данных** (заглушка)\n\n"
        "🔧 Функция в разработке.\n"
        "Пример: /export worship team - экспорт участников worship команды",
        parse_mode='Markdown'
    )

# Команда /cancel
@require_role("viewer")
async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "❌ Все операции отменены.\n\nИспользуйте /help для справки."
    )
    
# Обработка и подтверждение данных участника
async def process_participant_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, is_update: bool = False):
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
        await update.message.reply_text(f"❌ {error}")
        return

    existing_participant = None
    if not is_update:
        existing_participant = check_duplicate(participant_data['FullNameRU'])
    
    if existing_participant:
        # Найден дубль - объединяем старые и новые данные
        merged_data = merge_participant_data(existing_participant, participant_data)
        context.user_data['parsed_participant'] = merged_data
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

    if is_update:
        changes = detect_changes(existing, participant_data)
        if not changes:
            await update.message.reply_text(
                "Изменений не обнаружено. Напишите ДА или НЕТ."
            )
            return

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
    
    # Готовим два сообщения с распознанными данными
    intro_text = MESSAGES['CONFIRMATION_INTRO']

    template_text = format_participant_block(participant_data)

    await update.message.reply_text(intro_text, parse_mode='Markdown')
    await update.message.reply_text(template_text)

# Обработка неизвестных команд и текстовых сообщений
@require_role("viewer")
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    role = get_user_role(user_id)

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
            return
        context.user_data['parsed_participant'] = participant_data
        intro_text = MESSAGES['CONFIRMATION_INTRO']
        template_text = format_participant_block(participant_data)
        await update.message.reply_text(intro_text, parse_mode='Markdown')
        await update.message.reply_text(template_text)
        return

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
            try:
                participant_id = add_participant(participant_data)
            except ValidationError as e:
                await update.message.reply_text(f"❌ Ошибка валидации: {e}")
                return
            except ParticipantNotFoundError as e:  # unlikely here
                await update.message.reply_text(str(e))
                return
            except BotException as e:
                logger.error("Error adding participant: %s", e)
                await update.message.reply_text(
                    "❌ Ошибка базы данных при добавлении участника."
                )
                return
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
            existing = check_duplicate(participant_data['FullNameRU'])
            if existing:
                try:
                    updated = update_participant(existing['id'], participant_data)
                except ValidationError as e:
                    await update.message.reply_text(f"❌ Ошибка валидации: {e}")
                    return
                except ParticipantNotFoundError as e:
                    await update.message.reply_text(str(e))
                    return
                except BotException as e:
                    logger.error("Error updating participant: %s", e)
                    await update.message.reply_text(
                        "❌ Ошибка базы данных при обновлении участника."
                    )
                    return
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
        
        try:
            participant_id = add_participant(participant_data)
        except ValidationError as e:
            await update.message.reply_text(f"❌ Ошибка валидации: {e}")
            return
        except ParticipantNotFoundError as e:
            await update.message.reply_text(str(e))
            return
        except BotException as e:
            logger.error("Error adding participant: %s", e)
            await update.message.reply_text(
                "❌ Ошибка базы данных при добавлении участника."
            )
            return
        
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

    # Загружаем справочники в кэш
    load_reference_data()
    
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