from telegram import InlineKeyboardButton, InlineKeyboardMarkup


class ConfirmationKeyboardFactory:
    @staticmethod
    def create_confirm_cancel() -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("✅ Подтвердить", callback_data="confirm")],
                [InlineKeyboardButton("❌ Отмена", callback_data="cancel")],
            ]
        )
