"""Field normalization utilities for participant data."""

from typing import Optional, Set
from dataclasses import dataclass
from enum import Enum


class FieldType(Enum):
    GENDER = "gender"
    ROLE = "role"
    SIZE = "size"
    DEPARTMENT = "department"


@dataclass
class NormalizationResult:
    """Result of field normalization with confidence."""

    field_type: FieldType
    original_value: str
    normalized_value: str
    confidence: float

    @property
    def is_confident(self) -> bool:
        return self.confidence >= 0.8


class FieldNormalizer:
    """Unified normalizer for participant fields."""

    def __init__(self) -> None:
        self._init_mappings()

    def _init_mappings(self) -> None:
        """Initialize mapping dictionaries."""

        # === GENDER MAPPINGS ===
        self.GENDER_MAPPINGS = {
            "M": {"M", "МУЖ", "МУЖСКОЙ", "MALE", "М", "МУЖЧИНА", "МУЖЕ", "МУЖИК"},
            "F": {
                "F",
                "ЖЕН",
                "ЖЕНСКИЙ",
                "FEMALE",
                "Ж",
                "ЖЕНЩИНА",
                "ЖЕНА",
                "ДЕВОЧКА",
            },
        }

        # === ROLE MAPPINGS ===
        self.ROLE_MAPPINGS = {
            "TEAM": {
                "TEAM",
                "КОМАНДА",
                "ТИМ",
                "TIM",
                "TEAM MEMBER",
                "ЧЛЕН КОМАНДЫ",
                "КОМАНДНЫЙ",
                "СЛУЖИТЕЛЬ",
                "СЛУЖЕНИЕ",
                "STAFF",
            },
            "CANDIDATE": {
                "CANDIDATE",
                "КАНДИДАТ",
                "УЧАСТНИК",
                "КАНДИДАТКА",
                "CANDIDAT",
                "УЧАСТНИЦА",
                "ПАЛОМНИК",
                "ПАЛОМНИЦА",
            },
        }

        # === SIZE MAPPINGS ===
        self.SIZE_MAPPINGS = {
            "XS": {"XS", "EXTRA SMALL", "EXTRASMALL", "ХС"},
            "S": {"S", "SMALL", "СМОЛ", "С"},
            "M": {"M", "MEDIUM", "МЕДИУМ", "СРЕДНИЙ", "СРЕДНЯЯ"},
            "L": {"L", "LARGE", "ЛАРЖ"},
            "XL": {"XL", "EXTRA LARGE", "EXTRALARGE", "ХЛ"},
            "XXL": {"XXL", "2XL", "EXTRA EXTRA LARGE", "ХХЛ"},
            "3XL": {"3XL", "XXXL", "ХХХЛ"},
        }

        # === DEPARTMENT MAPPINGS ===
        self.DEPARTMENT_MAPPINGS = {
            "ROE": {"ROE", "РОЕ", "ROE ROOM", "РОЕ РУМ", "РОЭ", "РОИ"},
            "Chapel": {
                "CHAPEL",
                "МОЛИТВЕННЫЙ",
                "МОЛИТВА",
                "PRAYER",
                "ЧАСОВНЯ",
                "ЧАПЕЛ",
            },
            "Setup": {"SETUP", "СЕТАП", "НАСТРОЙКА", "ПОДГОТОВКА", "СЕТ АП", "СЕТАП"},
            "Palanka": {"PALANKA", "ПАЛАНКА", "ПОЛАНКА"},
            "Administration": {
                "ADMINISTRATION",
                "АДМИНИСТРАЦИЯ",
                "АДМИН",
                "ADMIN",
                "УПРАВЛЕНИЕ",
                "АДМИНИСТРАТИВНЫЙ",
                "ОФИС",
            },
            "Kitchen": {
                "KITCHEN",
                "КУХНЯ",
                "КИТЧЕН",
                "КУЛИНАРИЯ",
                "ПОВАРА",
                "ЕДА",
                "ПИТАНИЕ",
            },
            "Decoration": {
                "DECORATION",
                "ДЕКОРАЦИИ",
                "ДЕКОР",
                "DECO",
                "DECOR",
                "УКРАШЕНИЕ",
                "ОФОРМЛЕНИЕ",
                "ДЕКОРАТОР",
            },
            "Bell": {
                "BELL",
                "ЗВОНАРЬ",
                "БЕЛЛ",
                "ЗВОН",
                "КОЛОКОЛЬЧИК",
                "ЗВОНОК",
            },
            "Refreshment": {
                "REFRESHMENT",
                "РЕФРЕШМЕНТ",
                "УГОЩЕНИЯ",
                "НАПИТКИ",
                "ОСВЕЖЕНИЕ",
            },
            "Worship": {
                "WORSHIP",
                "ПРОСЛАВЛЕНИЕ",
                "ВОРШИП",
                "МУЗЫКА",
                "MUSIC",
                "ПЕСНИ",
                "ХВАЛА",
                "ПРОСЛАВИТЕЛЬ",
            },
            "Media": {
                "MEDIA",
                "МЕДИА",
                "ВИДЕО",
                "ФОТО",
                "СЪЕМКА",
                "КАМЕРА",
                "ФОТОГРАФ",
                "ВИДЕОГРАФ",
                "ТЕХНИКА",
            },
            "Духовенство": {
                "ДУХОВЕНСТВО",
                "CLERGY",
                "СВЯЩЕННИКИ",
                "СВЯЩЕННИК",
                "ПАСТОР",
            },
            "Ректорат": {"РЕКТОРАТ", "RECTOR", "РЕКТОРЫ", "РЕКТОР"},
        }

        self._create_reverse_indexes()

    def _create_reverse_indexes(self) -> None:
        """Create reverse indexes for fast lookup."""

        self._gender_index: dict[str, str] = {}
        self._role_index: dict[str, str] = {}
        self._size_index: dict[str, str] = {}
        self._department_index: dict[str, str] = {}

        for canonical, synonyms in self.GENDER_MAPPINGS.items():
            for synonym in synonyms:
                self._gender_index[synonym.upper()] = canonical

        for canonical, synonyms in self.ROLE_MAPPINGS.items():
            for synonym in synonyms:
                self._role_index[synonym.upper()] = canonical

        for canonical, synonyms in self.SIZE_MAPPINGS.items():
            for synonym in synonyms:
                self._size_index[synonym.upper()] = canonical

        for canonical, synonyms in self.DEPARTMENT_MAPPINGS.items():
            for synonym in synonyms:
                self._department_index[synonym.upper()] = canonical

    def normalize_gender(self, value: str) -> Optional[NormalizationResult]:
        """Normalize participant gender."""
        if not value or not value.strip():
            return None

        clean_value = value.strip().upper()
        canonical = self._gender_index.get(clean_value)

        if canonical:
            return NormalizationResult(
                field_type=FieldType.GENDER,
                original_value=value,
                normalized_value=canonical,
                confidence=1.0,
            )
        return None

    def normalize_role(self, value: str) -> Optional[NormalizationResult]:
        """Normalize participant role."""
        if not value or not value.strip():
            return None

        clean_value = value.strip().upper()
        canonical = self._role_index.get(clean_value)

        if canonical:
            return NormalizationResult(
                field_type=FieldType.ROLE,
                original_value=value,
                normalized_value=canonical,
                confidence=1.0,
            )
        return None

    def normalize_size(self, value: str) -> Optional[NormalizationResult]:
        """Normalize clothing size."""
        if not value or not value.strip():
            return None

        clean_value = value.strip().upper()
        canonical = self._size_index.get(clean_value)

        if canonical:
            return NormalizationResult(
                field_type=FieldType.SIZE,
                original_value=value,
                normalized_value=canonical,
                confidence=1.0,
            )
        return None

    def normalize_department(self, value: str) -> Optional[NormalizationResult]:
        """Normalize department name."""
        if not value or not value.strip():
            return None

        clean_value = value.strip().upper()
        canonical = self._department_index.get(clean_value)

        if canonical:
            return NormalizationResult(
                field_type=FieldType.DEPARTMENT,
                original_value=value,
                normalized_value=canonical,
                confidence=1.0,
            )
        return None

    def normalize_field(
        self, field_type: FieldType, value: str
    ) -> Optional[NormalizationResult]:
        """Generic normalization by field type."""
        if field_type == FieldType.GENDER:
            return self.normalize_gender(value)
        if field_type == FieldType.ROLE:
            return self.normalize_role(value)
        if field_type == FieldType.SIZE:
            return self.normalize_size(value)
        if field_type == FieldType.DEPARTMENT:
            return self.normalize_department(value)
        return None

    def get_gender_options(self) -> Set[str]:
        """Return all canonical gender values."""
        return set(self.GENDER_MAPPINGS.keys())

    def get_role_options(self) -> Set[str]:
        """Return all canonical role values."""
        return set(self.ROLE_MAPPINGS.keys())

    def get_size_options(self) -> Set[str]:
        """Return all canonical size values."""
        return set(self.SIZE_MAPPINGS.keys())

    def get_department_options(self) -> Set[str]:
        """Return all canonical departments."""
        return set(self.DEPARTMENT_MAPPINGS.keys())


field_normalizer = FieldNormalizer()


def normalize_gender(value: str) -> Optional[str]:
    """Convenience function for gender normalization."""
    result = field_normalizer.normalize_gender(value)
    return result.normalized_value if result else None


def normalize_role(value: str) -> Optional[str]:
    """Convenience function for role normalization."""
    result = field_normalizer.normalize_role(value)
    return result.normalized_value if result else None


def normalize_size(value: str) -> Optional[str]:
    """Convenience function for size normalization."""
    result = field_normalizer.normalize_size(value)
    return result.normalized_value if result else None


def normalize_department(value: str) -> Optional[str]:
    """Convenience function for department normalization."""
    result = field_normalizer.normalize_department(value)
    return result.normalized_value if result else None
