from typing import Dict, List, Optional, Union
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
    """Merge existing participant data with new values."""
    if isinstance(existing_data, Participant):
        merged = asdict(existing_data)
    else:
        merged = existing_data.copy()
    for key, value in updates.items():
        if value is not None and value != "":
            merged[key] = value
    return merged


def format_participant_block(data: Dict) -> str:
    text = (
        f"Имя (рус): {data.get('FullNameRU') or 'Не указано'}\n"
        f"Имя (англ): {data.get('FullNameEN') or 'Не указано'}\n"
        f"Пол: {data.get('Gender')}\n"
        f"Размер: {data.get('Size') or 'Не указано'}\n"
        f"Церковь: {data.get('Church') or 'Не указано'}\n"
        f"Роль: {data.get('Role')}"
    )
    if data.get("Role") == "TEAM":
        text += f"\nДепартамент: {data.get('Department') or 'Не указано'}"
    text += (
        f"\nГород: {data.get('CountryAndCity') or 'Не указано'}\n"
        f"Кто подал: {data.get('SubmittedBy') or 'Не указано'}\n"
        f"Контакты: {data.get('ContactInformation') or 'Не указано'}"
    )
    return text


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
        [
            InlineKeyboardButton("👥 Роль", callback_data="edit_Role"),
            InlineKeyboardButton("🏢 Департамент", callback_data="edit_Department"),
        ],
        [
            InlineKeyboardButton("👨‍💼 Кто подал", callback_data="edit_SubmittedBy"),
            InlineKeyboardButton(
                "📞 Контакты", callback_data="edit_ContactInformation"
            ),
        ],
    ]
    buttons.append([InlineKeyboardButton("❌ Отмена", callback_data="main_cancel")])
    return InlineKeyboardMarkup(buttons)


def detect_changes(old: Dict, new: Dict) -> List[str]:
    """Return human readable list of changes."""
    changes = []
    for field, new_value in new.items():
        old_value = old.get(field, "")
        if new_value != old_value:
            label = FIELD_LABELS.get(field, field)
            emoji = FIELD_EMOJIS.get(field, "")
            changes.append(f"{emoji} **{label}:** {old_value or '—'} → {new_value}")
    return changes


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

    def add_participant(self, data: Dict) -> int:
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
        return self.repository.add(new_participant)

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
