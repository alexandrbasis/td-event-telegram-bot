from typing import List

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


class UIFactory:
    """Factory to create common UI elements."""

    def create_add_participant_form(self) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "📝 Заполнить шаблон", callback_data="template"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "✍️ Ввести вручную", callback_data="manual"
                    )
                ],
                [InlineKeyboardButton("❌ Отмена", callback_data="cancel")],
            ]
        )

    def create_success_keyboard(self) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🏠 Главное меню", callback_data="main_menu"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "➕ Добавить ещё", callback_data="add_more"
                    )
                ],
            ]
        )

    def create_search_results_keyboard(self, results: List) -> InlineKeyboardMarkup:
        buttons: List[List[InlineKeyboardButton]] = []
        for participant in results[:5]:
            buttons.append(
                [
                    InlineKeyboardButton(
                        f"{participant.FullNameRU}",
                        callback_data=f"select_{participant.id}",
                    )
                ]
            )
        if len(results) > 5:
            buttons.append(
                [
                    InlineKeyboardButton(
                        "➡️ Ещё результаты", callback_data="more_results"
                    )
                ]
            )
        return InlineKeyboardMarkup(buttons)
