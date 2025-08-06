from telegram import Update


async def show_validation_errors(update: Update, errors: dict) -> None:
    lines = [f"- {field}: {', '.join(errs)}" for field, errs in errors.items()]
    await update.message.reply_text("\n".join(lines))
