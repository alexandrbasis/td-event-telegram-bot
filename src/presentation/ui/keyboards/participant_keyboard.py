from telegram import InlineKeyboardButton, InlineKeyboardMarkup


class ParticipantKeyboardFactory:
    """Factory for participant related keyboards."""

    @staticmethod
    def create_main_menu(user_role: str) -> InlineKeyboardMarkup:
        buttons = [
            [InlineKeyboardButton("\u2795 Добавить", callback_data="main_add")],
            [InlineKeyboardButton("\U0001F50D Поиск", callback_data="main_search")],
            [InlineKeyboardButton("\U0001F4CB Список", callback_data="main_list")],
        ]
        if user_role == "admin":
            buttons.append([InlineKeyboardButton("\u2699\ufe0f Админ", callback_data="admin")])
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def create_edit_menu(participant_id: int) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("\u270F\ufe0f Редактировать", callback_data=f"edit_{participant_id}")],
                [InlineKeyboardButton("\U0001F5D1\ufe0f Удалить", callback_data=f"delete_{participant_id}")],
                [InlineKeyboardButton("\u25C0\ufe0f Назад", callback_data="back_to_list")],
            ]
        )
