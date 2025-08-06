from typing import Dict

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from src.constants import DEPARTMENT_DISPLAY


def get_gender_selection_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора пола."""
    buttons = [
        [InlineKeyboardButton("\U0001f468 Мужской", callback_data="gender_M")],
        [InlineKeyboardButton("\U0001f469 Женский", callback_data="gender_F")],
        [InlineKeyboardButton("↩️ Назад", callback_data="field_edit_cancel")],
    ]
    return InlineKeyboardMarkup(buttons)


def get_role_selection_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора роли."""
    buttons = [
        [InlineKeyboardButton("\U0001f464 Кандидат", callback_data="role_CANDIDATE")],
        [InlineKeyboardButton("\U0001f465 Команда", callback_data="role_TEAM")],
        [InlineKeyboardButton("↩️ Назад", callback_data="field_edit_cancel")],
    ]
    return InlineKeyboardMarkup(buttons)


def get_gender_selection_keyboard_required() -> InlineKeyboardMarkup:
    """Keyboard for gender selection without manual input."""
    buttons = [
        [InlineKeyboardButton("\U0001f468 Мужской", callback_data="gender_M")],
        [InlineKeyboardButton("\U0001f469 Женский", callback_data="gender_F")],
        [InlineKeyboardButton("↩️ Назад", callback_data="field_edit_cancel")],
    ]
    return InlineKeyboardMarkup(buttons)


def get_role_selection_keyboard_required() -> InlineKeyboardMarkup:
    """Keyboard for role selection without manual input."""
    buttons = [
        [InlineKeyboardButton("\U0001f464 Кандидат", callback_data="role_CANDIDATE")],
        [InlineKeyboardButton("\U0001f465 Команда", callback_data="role_TEAM")],
        [InlineKeyboardButton("↩️ Назад", callback_data="field_edit_cancel")],
    ]
    return InlineKeyboardMarkup(buttons)


def get_size_selection_keyboard_required() -> InlineKeyboardMarkup:
    """Keyboard for size selection without manual input."""
    buttons = [
        [
            InlineKeyboardButton("XS", callback_data="size_XS"),
            InlineKeyboardButton("S", callback_data="size_S"),
            InlineKeyboardButton("M", callback_data="size_M"),
        ],
        [
            InlineKeyboardButton("L", callback_data="size_L"),
            InlineKeyboardButton("XL", callback_data="size_XL"),
            InlineKeyboardButton("XXL", callback_data="size_XXL"),
        ],
        [InlineKeyboardButton("3XL", callback_data="size_3XL")],
        [InlineKeyboardButton("↩️ Назад", callback_data="field_edit_cancel")],
    ]
    return InlineKeyboardMarkup(buttons)


def get_department_selection_keyboard_required() -> InlineKeyboardMarkup:
    """Keyboard for department selection without manual input."""
    buttons = []
    dept_items = list(DEPARTMENT_DISPLAY.items())
    for i in range(0, len(dept_items), 2):
        row = []
        for j in range(i, min(i + 2, len(dept_items))):
            key, display_name = dept_items[j]
            row.append(InlineKeyboardButton(display_name, callback_data=f"dept_{key}"))
        buttons.append(row)

    buttons.append([InlineKeyboardButton("↩️ Назад", callback_data="field_edit_cancel")])
    return InlineKeyboardMarkup(buttons)


def get_size_selection_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора размера без ручного ввода."""
    buttons = [
        [
            InlineKeyboardButton("XS", callback_data="size_XS"),
            InlineKeyboardButton("S", callback_data="size_S"),
            InlineKeyboardButton("M", callback_data="size_M"),
        ],
        [
            InlineKeyboardButton("L", callback_data="size_L"),
            InlineKeyboardButton("XL", callback_data="size_XL"),
            InlineKeyboardButton("XXL", callback_data="size_XXL"),
        ],
        [InlineKeyboardButton("3XL", callback_data="size_3XL")],
        [InlineKeyboardButton("↩️ Назад", callback_data="field_edit_cancel")],
    ]
    return InlineKeyboardMarkup(buttons)


def get_gender_selection_keyboard_simple() -> InlineKeyboardMarkup:
    """Keyboard for gender selection without manual input."""
    buttons = [
        [InlineKeyboardButton("\U0001f468 Мужской", callback_data="gender_M")],
        [InlineKeyboardButton("\U0001f469 Женский", callback_data="gender_F")],
        [InlineKeyboardButton("↩️ Назад", callback_data="field_edit_cancel")],
    ]
    return InlineKeyboardMarkup(buttons)


def get_department_selection_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора департамента."""
    buttons = []
    dept_items = list(DEPARTMENT_DISPLAY.items())
    for i in range(0, len(dept_items), 2):
        row = []
        for j in range(i, min(i + 2, len(dept_items))):
            key, display_name = dept_items[j]
            row.append(InlineKeyboardButton(display_name, callback_data=f"dept_{key}"))
        buttons.append(row)

    # Кнопка ручного ввода удалена
    buttons.append([InlineKeyboardButton("↩️ Назад", callback_data="field_edit_cancel")])
    return InlineKeyboardMarkup(buttons)


def get_edit_keyboard(participant_data: Dict) -> InlineKeyboardMarkup:
    """Создает клавиатуру с кнопками для редактирования полей."""
    buttons = [
        [InlineKeyboardButton("✅ Сохранить", callback_data="confirm_save")],
        [
            InlineKeyboardButton("👤 Имя (рус)", callback_data="edit_FullNameRU"),
            InlineKeyboardButton("🌍 Имя (англ)", callback_data="edit_FullNameEN"),
        ],
        [
            InlineKeyboardButton("⚥ Пол", callback_data="edit_Gender"),
            InlineKeyboardButton("👕 Размер", callback_data="edit_Size"),
        ],
        [
            InlineKeyboardButton("⛪ Церковь", callback_data="edit_Church"),
            InlineKeyboardButton("🏙️ Город", callback_data="edit_CountryAndCity"),
        ],
    ]

    role = participant_data.get("Role")
    if role == "CANDIDATE":
        buttons.append([InlineKeyboardButton("👥 Роль", callback_data="edit_Role")])
    else:
        buttons.append(
            [
                InlineKeyboardButton("👥 Роль", callback_data="edit_Role"),
                InlineKeyboardButton("🏢 Департамент", callback_data="edit_Department"),
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton("👨‍💼 Кто подал", callback_data="edit_SubmittedBy"),
            InlineKeyboardButton(
                "📞 Контакты", callback_data="edit_ContactInformation"
            ),
        ]
    )

    buttons.append([InlineKeyboardButton("❌ Отмена", callback_data="main_cancel")])
    return InlineKeyboardMarkup(buttons)


class KeyboardFactory:
    @staticmethod
    def create_main_menu(user_role: str) -> InlineKeyboardMarkup:
        """Создает клавиатуру главного меню в зависимости от роли."""
        if user_role == "coordinator":
            keyboard = [
                [
                    InlineKeyboardButton("➕ Добавить", callback_data="main_add"),
                    InlineKeyboardButton("🔍 Поиск", callback_data="main_search"),
                ],
                [
                    InlineKeyboardButton("📋 Список", callback_data="main_list"),
                    InlineKeyboardButton("📤 Экспорт", callback_data="main_export"),
                ],
                [InlineKeyboardButton("ℹ️ Помощь", callback_data="main_help")],
            ]
        else:
            keyboard = [
                [
                    InlineKeyboardButton("🔍 Поиск", callback_data="main_search"),
                    InlineKeyboardButton("📋 Список", callback_data="main_list"),
                ],
                [
                    InlineKeyboardButton("📤 Экспорт", callback_data="main_export"),
                    InlineKeyboardButton("ℹ️ Помощь", callback_data="main_help"),
                ],
            ]

        return InlineKeyboardMarkup(keyboard)
