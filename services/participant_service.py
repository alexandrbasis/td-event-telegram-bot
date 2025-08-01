from typing import Dict, List, Optional, Tuple, Union
from dataclasses import asdict
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from repositories.participant_repository import AbstractParticipantRepository
from models.participant import Participant
from database import find_participant_by_name
from utils.validators import validate_participant_data
from utils.exceptions import (
    DuplicateParticipantError,
    ParticipantNotFoundError,
    ValidationError,
)
from parsers.participant_parser import normalize_field_value
from constants import (
    GENDER_DISPLAY,
    ROLE_DISPLAY,
    SIZE_DISPLAY,
    DEPARTMENT_DISPLAY,
)

logger = logging.getLogger(__name__)

FIELD_LABELS = {
    "FullNameRU": "Имя (рус)",
    "FullNameEN": "Имя (англ)",
    "Gender": "Пол",
    "Size": "Размер",
    "Church": "Церковь",
    "Role": "Роль",
    "Department": "Департамент",
    "CountryAndCity": "Город",
    "SubmittedBy": "Кто подал",
    "ContactInformation": "Контакты",
}

FIELD_EMOJIS = {
    "FullNameRU": "👤",
    "FullNameEN": "🌍",
    "Gender": "⚥",
    "Size": "👕",
    "Church": "⛪",
    "Role": "👥",
    "Department": "🏢",
    "CountryAndCity": "🏙️",
    "SubmittedBy": "👨‍💼",
    "ContactInformation": "📞",
}


def merge_participant_data(
    existing_data: Union[Participant, Dict], updates: Dict
) -> Dict:
    """Merge existing participant data with new values.

    Business rules:
    - Explicit values from ``updates`` override existing ones.
    - If the role changes from ``TEAM`` to ``CANDIDATE`` the ``Department``
      field must be cleared automatically.
    """

    if isinstance(existing_data, Participant):
        merged = asdict(existing_data)
    else:
        merged = existing_data.copy()

    old_role = merged.get("Role")

    for key, value in updates.items():
        if value is not None and value != "":
            merged[key] = value

    # Auto clear department if role switched from TEAM to CANDIDATE
    if old_role == "TEAM" and merged.get("Role") == "CANDIDATE":
        merged["Department"] = ""

    # Also clear department when switching to TEAM without specifying department
    if (
        old_role != "TEAM"
        and merged.get("Role") == "TEAM"
        and "Department" not in updates
    ):
        merged["Department"] = ""

    return merged


def format_participant_block(data: Dict) -> str:
    gender_key = data.get("Gender") or ""
    size_key = data.get("Size") or ""
    role_key = data.get("Role") or ""
    dept_key = data.get("Department") or ""

    gender = GENDER_DISPLAY.get(gender_key, "Не указано")
    size = SIZE_DISPLAY.get(size_key, "Не указано")
    role = ROLE_DISPLAY.get(role_key, role_key)
    department = DEPARTMENT_DISPLAY.get(dept_key, dept_key or "Не указано")

    text = (
        f"Имя (рус): {data.get('FullNameRU') or 'Не указано'}\n"
        f"Имя (англ): {data.get('FullNameEN') or 'Не указано'}\n"
        f"Пол: {gender}\n"
        f"Размер: {size}\n"
        f"Церковь: {data.get('Church') or 'Не указано'}\n"
        f"Роль: {role}"
    )

    if role_key == "TEAM":
        text += f"\nДепартамент: {department}"

    text += (
        f"\nГород: {data.get('CountryAndCity') or 'Не указано'}\n"
        f"Кто подал: {data.get('SubmittedBy') or 'Не указано'}\n"
        f"Контакты: {data.get('ContactInformation') or 'Не указано'}"
    )
    return text


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


def detect_changes(old: Dict, new: Dict) -> List[str]:
    """Return human readable list of changes.

    Additionally handles the business rule that switching a participant's role
    from ``TEAM`` to ``CANDIDATE`` should clear the ``Department`` field and be
    reflected as a change.
    """

    changes = []

    role_changed_to_candidate = (
        old.get("Role") == "TEAM" and new.get("Role") == "CANDIDATE"
    )

    for field, new_value in new.items():
        old_value = old.get(field, "")

        # When role changes to CANDIDATE the Department is implicitly cleared
        if field == "Department" and role_changed_to_candidate:
            new_value = ""

        if new_value != old_value:
            label = FIELD_LABELS.get(field, field)
            emoji = FIELD_EMOJIS.get(field, "")
            changes.append(
                f"{emoji} **{label}:** {old_value or '—'} → {new_value or '—'}"
            )

    # If the role changed to CANDIDATE and no Department was supplied in ``new``
    # we still need to show that the Department was cleared
    if role_changed_to_candidate and "Department" not in new:
        old_value = old.get("Department", "")
        if old_value:
            label = FIELD_LABELS.get("Department", "Department")
            emoji = FIELD_EMOJIS.get("Department", "")
            changes.append(f"{emoji} **{label}:** {old_value or '—'} → —")

    return changes


def update_single_field(
    participant_data: Dict, field_name: str, new_value: str
) -> Tuple[Dict, List[str]]:
    """Safely update a single field in participant data.

    Normalizes ``new_value`` according to ``field_name`` and applies the change
    only to that field. Raises :class:`ValidationError` if normalization fails.

    Returns a tuple of the updated data and a list with human readable changes.
    """

    original = participant_data.copy()
    normalized = normalize_field_value(field_name, new_value) if new_value else ""

    if new_value and not normalized:
        raise ValidationError(f"Invalid value for field {field_name}")

    updated = participant_data.copy()
    updated[field_name] = normalized

    if field_name == "Role" and normalized != original.get("Role"):
        updated["Department"] = ""

    changes = detect_changes(original, updated)
    return updated, changes


def check_duplicate(full_name_ru: str) -> Optional[Dict]:
    """Проверяет наличие дубликата по имени. Возвращает dict или None."""
    try:
        return find_participant_by_name(full_name_ru)
    except ParticipantNotFoundError:
        # На случай, если поиск по имени сгенерирует исключение
        return None


class ParticipantService:
    """
    ✅ ОБНОВЛЕННЫЙ Service layer для работы с улучшенным Repository pattern.

    Принципы:
    1. Service работает с доменными объектами Participant
    2. Бизнес-логика (валидация, проверка дублей) остается в Service
    3. Repository используется только для персистентности
    4. Поддержка как полного, так и частичного обновления
    """

    def __init__(self, repository: AbstractParticipantRepository):
        self.repository = repository

    def check_duplicate(self, full_name_ru: str) -> Optional[Participant]:
        """Return participant if exists, otherwise None."""
        return self.repository.get_by_name(full_name_ru)

    def add_participant(self, data: Dict) -> Participant:
        """
        ✅ ОБНОВЛЕНО: создает объект Participant и передает в repository.

        Validate data, check for duplicates and save participant.
        """
        valid, error = validate_participant_data(data)
        if not valid:
            raise ValidationError(error)

        existing = self.check_duplicate(data.get("FullNameRU", ""))
        if existing:
            raise DuplicateParticipantError(
                f"Participant '{data.get('FullNameRU')}' already exists"
            )

        # ✅ ИСПРАВЛЕНИЕ: создаем объект Participant и передаем в repository
        new_participant = Participant(**data)
        new_id = self.repository.add(new_participant)
        new_participant.id = new_id
        return new_participant

    def update_participant(self, participant_id: int, data: Dict) -> bool:
        """
        ✅ ОБНОВЛЕНО: полное обновление через объект Participant.

        Validate and update participant completely.
        """
        valid, error = validate_participant_data(data)
        if not valid:
            raise ValidationError(error)

        # Получаем существующего участника
        existing = self.repository.get_by_id(participant_id)
        if existing is None:
            raise ParticipantNotFoundError(
                f"Participant with id {participant_id} not found"
            )

        # ✅ ИСПРАВЛЕНИЕ: создаем новый объект с обновленными данными
        updated_data = data.copy()
        updated_data["id"] = participant_id

        updated_participant = Participant(**updated_data)
        return self.repository.update(updated_participant)

    def update_participant_fields(self, participant_id: int, **fields) -> bool:
        """
        ✅ НОВЫЙ МЕТОД: частичное обновление конкретных полей.

        Args:
            participant_id: ID участника
            **fields: Поля для обновления

        Example:
            service.update_participant_fields(123, FullNameRU="Новое имя", Gender="M")
        """

        if fields:
            temp_data = {
                "FullNameRU": "temp",
                "Gender": "F",
                "Church": "temp",
                "Role": "CANDIDATE",
                **fields,
            }

            valid, error = validate_participant_data(temp_data)
            if not valid:
                field_names = set(fields.keys())
                critical_fields = {"FullNameRU", "Gender", "Church", "Role"}
                if field_names & critical_fields:
                    raise ValidationError(error)

        return self.repository.update_fields(participant_id, **fields)

    def get_participant(self, participant_id: int) -> Optional[Participant]:
        """
        ✅ НОВЫЙ МЕТОД: получение участника по ID.
        """

        return self.repository.get_by_id(participant_id)

    def get_all_participants(self) -> List[Participant]:
        """
        ✅ НОВЫЙ МЕТОД: получение всех участников.
        """

        return self.repository.get_all()

    def delete_participant(self, participant_id: int) -> bool:
        """
        ✅ НОВЫЙ МЕТОД: удаление участника.
        """

        return self.repository.delete(participant_id)

    def participant_exists(self, participant_id: int) -> bool:
        """
        ✅ НОВЫЙ МЕТОД: проверка существования участника.
        """

        return self.repository.exists(participant_id)
