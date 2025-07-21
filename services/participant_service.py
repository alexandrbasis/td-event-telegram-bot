from typing import Dict, List, Optional
import logging

from database import find_participant_by_name

logger = logging.getLogger(__name__)

FIELD_LABELS = {
    'FullNameRU': 'Имя (рус)',
    'FullNameEN': 'Имя (англ)',
    'Gender': 'Пол',
    'Size': 'Размер',
    'Church': 'Церковь',
    'Role': 'Роль',
    'Department': 'Департамент',
    'CountryAndCity': 'Город',
    'SubmittedBy': 'Кто подал',
    'ContactInformation': 'Контакты',
}

FIELD_EMOJIS = {
    'FullNameRU': '👤',
    'FullNameEN': '🌍',
    'Gender': '⚥',
    'Size': '👕',
    'Church': '⛪',
    'Role': '👥',
    'Department': '🏢',
    'CountryAndCity': '🏙️',
    'SubmittedBy': '👨‍💼',
    'ContactInformation': '📞',
}


def merge_participant_data(existing_data: Dict, updates: Dict) -> Dict:
    """Merge existing participant data with new values."""
    merged = existing_data.copy()
    for key, value in updates.items():
        if value is not None and value != '':
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
    if data.get('Role') == 'TEAM':
        text += f"\nДепартамент: {data.get('Department') or 'Не указано'}"
    text += (
        f"\nГород: {data.get('CountryAndCity') or 'Не указано'}\n"
        f"Кто подал: {data.get('SubmittedBy') or 'Не указано'}\n"
        f"Контакты: {data.get('ContactInformation') or 'Не указано'}"
    )
    return text


def detect_changes(old: Dict, new: Dict) -> List[str]:
    """Return human readable list of changes."""
    changes = []
    for field, new_value in new.items():
        old_value = old.get(field, '')
        if new_value != old_value:
            label = FIELD_LABELS.get(field, field)
            emoji = FIELD_EMOJIS.get(field, '')
            changes.append(f"{emoji} **{label}:** {old_value or '—'} → {new_value}")
    return changes


def check_duplicate(full_name_ru: str) -> Optional[Dict]:
    return find_participant_by_name(full_name_ru)
