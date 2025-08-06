from telegram import InlineKeyboardButton, InlineKeyboardMarkup


class MainKeyboardFactory:
    @staticmethod
    def create() -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            [[InlineKeyboardButton("\u2795 Добавить", callback_data="main_add")]]
        )
