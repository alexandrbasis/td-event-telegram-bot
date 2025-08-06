from telegram import InlineKeyboardMarkup

from .keyboards import ParticipantKeyboardFactory


class UIFactory:
    """Simple factory to create UI elements."""

    def create_add_participant_form(self) -> InlineKeyboardMarkup:
        return ParticipantKeyboardFactory.create_main_menu("coordinator")

    def create_success_keyboard(self) -> InlineKeyboardMarkup:
        return ParticipantKeyboardFactory.create_main_menu("coordinator")
