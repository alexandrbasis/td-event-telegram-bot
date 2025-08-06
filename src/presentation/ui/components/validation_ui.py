from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update


async def show_validation_errors(update: Update, errors: dict) -> None:
    lines = ["❌ **Ошибки валидации:**\n"]
    for field, field_errors in errors.items():
        lines.append(f"• **{field}**: {', '.join(field_errors)}")

    message = '\n'.join(lines)
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔄 Попробовать снова", callback_data="retry")],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel")],
        ]
    )

    await update.message.reply_text(
        message, parse_mode="Markdown", reply_markup=keyboard
    )


async def show_duplicate_warning(update: Update, existing_participant: dict) -> None:
    message = f"""⚠️ **Участник уже существует!**
    
**Найденный участник:**
- Имя: {existing_participant.get('FullNameRU')}
- ID: {existing_participant.get('id')}
- Роль: {existing_participant.get('Role')}

Что делать?"""

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✏️ Изменить данные", callback_data="modify_data")],
            [
                InlineKeyboardButton(
                    "👁️ Просмотреть",
                    callback_data=f"view_{existing_participant['id']}",
                )
            ],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel")],
        ]
    )

    await update.message.reply_text(
        message, parse_mode="Markdown", reply_markup=keyboard
    )
