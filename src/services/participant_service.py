import json
import logging
import logging
import time
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional, Tuple, Union

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from src.presentation.ui.legacy_keyboards import (
    get_department_selection_keyboard,
    get_department_selection_keyboard_required,
    get_edit_keyboard,
    get_gender_selection_keyboard,
    get_gender_selection_keyboard_required,
    get_gender_selection_keyboard_simple,
    get_role_selection_keyboard,
    get_role_selection_keyboard_required,
    get_size_selection_keyboard,
    get_size_selection_keyboard_required,
)
from src.presentation.ui.formatters import MessageFormatter
from src.repositories.participant_repository import AbstractParticipantRepository
from src.models.participant import Participant
from src.database import find_participant_by_name
from src.utils.validators import validate_participant_data
from src.shared.exceptions import (
    DuplicateParticipantError,
    ParticipantNotFoundError,
    ValidationError,
)
from src.parsers.participant_parser import normalize_field_value
from src.constants import (
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


@dataclass
class SearchResult:
    participant: Participant
    confidence: float
    match_field: str  # "name_ru", "name_en", "id"
    match_type: str  # "exact", "fuzzy", "partial"


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
    """Proxy to new message formatter for backward compatibility."""
    return MessageFormatter.format_participant_info(data)


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
        self.logger = logging.getLogger("participant_changes")
        self.performance_logger = logging.getLogger("performance")
        self._participants_cache = None
        self._cache_timestamp = 0
        self._cache_ttl = 300  # 5 минут

    def _get_cached_participants(self):
        now = time.time()
        if (
            self._participants_cache is None
            or now - self._cache_timestamp > self._cache_ttl
        ):
            logger.debug("Refreshing participants cache")
            self._participants_cache = self.get_all_participants()
            self._cache_timestamp = now
        else:
            logger.debug("Using cached participants")
        return self._participants_cache

    def _log_participant_change(
        self,
        user_id: Optional[int],
        operation: str,
        data: Dict,
        participant_id: Optional[int] = None,
        old_data: Optional[Dict] = None,
    ) -> None:
        entry = {
            "user_id": user_id,
            "operation": operation,
            "data": data,
        }
        if participant_id is not None:
            entry["participant_id"] = participant_id
        if old_data is not None:
            entry["old_data"] = old_data
        self.logger.info(json.dumps(entry, ensure_ascii=False))

    def check_duplicate(
        self, full_name_ru: str, user_id: Optional[int] = None
    ) -> Optional[Participant]:
        """Return participant if exists, otherwise None."""
        start = time.time()
        participant = self.repository.get_by_name(full_name_ru)
        duration = time.time() - start
        self.performance_logger.info(
            json.dumps(
                {
                    "operation": "check_duplicate",
                    "duration": duration,
                    "user_id": user_id,
                    "name": full_name_ru,
                    "duplicate": bool(participant),
                },
                ensure_ascii=False,
            )
        )
        return participant

    def add_participant(self, data: Dict, user_id: Optional[int] = None) -> Participant:
        """
        ✅ ОБНОВЛЕНО: создает объект Participant и передает в repository.

        Validate data, check for duplicates and save participant.
        """
        valid, error = validate_participant_data(data)
        if not valid:
            raise ValidationError(error)

        existing = self.check_duplicate(data.get("FullNameRU", ""), user_id)
        if existing:
            raise DuplicateParticipantError(
                f"Participant '{data.get('FullNameRU')}' already exists"
            )

        # ✅ ИСПРАВЛЕНИЕ: создаем объект Participant и передаем в repository
        start = time.time()
        new_participant = Participant(**data)
        new_id = self.repository.add(new_participant)
        duration = time.time() - start
        new_participant.id = new_id
        self._log_participant_change(user_id, "add", data, participant_id=new_id)
        self.performance_logger.info(
            json.dumps(
                {
                    "operation": "add_participant",
                    "duration": duration,
                    "user_id": user_id,
                    "participant_id": new_id,
                },
                ensure_ascii=False,
            )
        )
        return new_participant

    def update_participant(
        self, participant_id: Union[int, str], data: Dict, user_id: Optional[int] = None
    ) -> bool:
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

        start = time.time()
        updated_participant = Participant(**updated_data)
        result = self.repository.update(updated_participant)
        duration = time.time() - start
        self._log_participant_change(
            user_id,
            "update",
            data,
            participant_id=participant_id,
            old_data=asdict(existing),
        )
        self.performance_logger.info(
            json.dumps(
                {
                    "operation": "update_participant",
                    "duration": duration,
                    "user_id": user_id,
                    "participant_id": participant_id,
                },
                ensure_ascii=False,
            )
        )
        return result

    def update_participant_fields(
        self, participant_id: Union[int, str], user_id: Optional[int] = None, **fields
    ) -> bool:
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

        start = time.time()
        result = self.repository.update_fields(participant_id, **fields)
        duration = time.time() - start
        self._log_participant_change(
            user_id, "update_fields", fields, participant_id=participant_id
        )
        self.performance_logger.info(
            json.dumps(
                {
                    "operation": "update_fields",
                    "duration": duration,
                    "user_id": user_id,
                    "participant_id": participant_id,
                },
                ensure_ascii=False,
            )
        )
        return result

    def get_participant(self, participant_id: Union[int, str]) -> Optional[Participant]:
        """
        ✅ НОВЫЙ МЕТОД: получение участника по ID.
        """

        return self.repository.get_by_id(participant_id)

    def get_all_participants(self) -> List[Participant]:
        """
        ✅ НОВЫЙ МЕТОД: получение всех участников.
        """

        return self.repository.get_all()

    def delete_participant(
        self,
        participant_id: Union[int, str],
        user_id: Optional[int] = None,
        reason: str = "",
    ) -> bool:
        """Delete participant and log reason."""
        start = time.time()
        result = self.repository.delete(participant_id)
        duration = time.time() - start
        self._log_participant_change(
            user_id,
            "delete",
            {"reason": reason},
            participant_id=participant_id,
        )
        self.performance_logger.info(
            json.dumps(
                {
                    "operation": "delete_participant",
                    "duration": duration,
                    "user_id": user_id,
                    "participant_id": participant_id,
                },
                ensure_ascii=False,
            )
        )
        return result

    def participant_exists(self, participant_id: Union[int, str]) -> bool:
        """
        ✅ НОВЫЙ МЕТОД: проверка существования участника.
        """

        return self.repository.exists(participant_id)

    # --- Поисковые методы ---

    def search_participants(
        self,
        query: str,
        max_results: int = 5,
        min_confidence: float = 0.6,
    ) -> List[SearchResult]:
        """Умный поиск участников по различным критериям."""

        results: List[SearchResult] = []
        query_cleaned = query.strip()

        # 1. Поиск по ID
        if query_cleaned.isdigit():
            participant_id = int(query_cleaned)
            participant = self.get_participant(participant_id)
            if participant:
                results.append(
                    SearchResult(
                        participant=participant,
                        confidence=1.0,
                        match_field="id",
                        match_type="exact",
                    )
                )
                return results

        all_participants = self._get_cached_participants()

        # 2. Точные совпадения по именам
        for p in all_participants:
            if p.FullNameRU and p.FullNameRU.lower() == query_cleaned.lower():
                results.append(
                    SearchResult(
                        participant=p,
                        confidence=1.0,
                        match_field="name_ru",
                        match_type="exact",
                    )
                )
                continue
            if p.FullNameEN and p.FullNameEN.lower() == query_cleaned.lower():
                results.append(
                    SearchResult(
                        participant=p,
                        confidence=1.0,
                        match_field="name_en",
                        match_type="exact",
                    )
                )
                continue

        if results:
            return results

        # 3. Fuzzy поиск
        results.extend(
            self._fuzzy_search(query_cleaned, all_participants, min_confidence)
        )

        results.sort(key=lambda x: x.confidence, reverse=True)
        return results[:max_results]

    def _fuzzy_search(
        self,
        query: str,
        participants: List[Participant],
        min_confidence: float,
    ) -> List[SearchResult]:
        """Нечеткий поиск с использованием Levenshtein distance."""

        results: List[SearchResult] = []
        try:
            import Levenshtein  # type: ignore

            fuzzy_available = True
        except ImportError:  # pragma: no cover - fallback when library missing
            fuzzy_available = False

        for p in participants:
            ru_conf = self._calculate_similarity(
                query, p.FullNameRU or "", fuzzy_available
            )
            if ru_conf >= min_confidence:
                results.append(
                    SearchResult(
                        participant=p,
                        confidence=ru_conf,
                        match_field="name_ru",
                        match_type="fuzzy" if fuzzy_available else "partial",
                    )
                )
                continue

            if p.FullNameEN:
                en_conf = self._calculate_similarity(
                    query, p.FullNameEN, fuzzy_available
                )
                if en_conf >= min_confidence:
                    results.append(
                        SearchResult(
                            participant=p,
                            confidence=en_conf,
                            match_field="name_en",
                            match_type="fuzzy" if fuzzy_available else "partial",
                        )
                    )

        return results

    def _calculate_similarity(
        self, query: str, target: str, fuzzy_available: bool
    ) -> float:
        """Вычисляет похожесть строк."""

        if not target:
            return 0.0

        query_lower = query.lower()
        target_lower = target.lower()

        if query_lower == target_lower:
            return 1.0

        if query_lower in target_lower or target_lower in query_lower:
            return 0.8

        if fuzzy_available:
            import Levenshtein  # type: ignore

            distance = Levenshtein.distance(query_lower, target_lower)
            max_len = max(len(query_lower), len(target_lower))
            if max_len == 0:
                return 1.0
            return max(0.0, 1.0 - (distance / max_len))

        return 0.0

    def format_search_result(self, result: SearchResult) -> str:
        """Форматирует результат поиска для отображения."""

        p = result.participant
        confidence_emoji = "🎯" if result.confidence == 1.0 else "🔍"
        role_emoji = "👤" if p.Role == "CANDIDATE" else "👨‍💼"

        text = f"{confidence_emoji} {role_emoji} **{p.FullNameRU}** (ID: {p.id})\n"
        text += f"   • Церковь: {p.Church}\n"
        text += f"   • Роль: {p.Role}"
        if p.Role == "TEAM" and p.Department:
            text += f" ({p.Department})"

        if result.match_field == "name_en" and p.FullNameEN:
            text += f"\n   • English: {p.FullNameEN}"

        if result.confidence < 1.0:
            text += f"\n   • Совпадение: {int(result.confidence * 100)}%"

        return text
