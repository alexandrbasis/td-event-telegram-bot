from typing import Optional
from utils.cache import cache
from utils.field_normalizer import (
    normalize_gender,
    normalize_role,
    normalize_size,
    normalize_department,
    normalize_payment_status,
)


def get_reference_data(key: str):
    return cache.get(key) or []


def recognize_role(token: str) -> Optional[str]:
    """Распознает роль из токена"""
    return normalize_role(token)


def recognize_gender(token: str) -> Optional[str]:
    """Распознает пол из токена"""
    return normalize_gender(token)


def recognize_size(token: str) -> Optional[str]:
    """Распознает размер из токена"""
    return normalize_size(token)


def recognize_department(token: str) -> Optional[str]:
    """Распознает департамент из токена с fuzzy matching."""
    # Сначала точное распознавание
    result = normalize_department(token)
    if result:
        return result

    # Если точное не сработало - fuzzy matching
    if len(token) < 3:  # Слишком короткие токены не ищем
        return None

    try:  # pragma: no cover - optional dependency
        from parsers.participant_parser import FuzzyMatcher

        matcher = FuzzyMatcher(similarity_threshold=0.8)  # Строгий порог для департаментов
        fuzzy_result = matcher.find_best_department_match(token)
        return fuzzy_result[0] if fuzzy_result else None
    except ImportError:
        return None


def recognize_payment_status(token: str) -> Optional[str]:
    """Распознает статус оплаты из токена."""
    return normalize_payment_status(token)


def recognize_church(token: str) -> Optional[str]:
    """Распознает церковь из токена с поддержкой fuzzy matching."""
    if len(token) < 3:
        return None

    churches = get_reference_data("churches")

    try:  # pragma: no cover - optional dependency
        from parsers.participant_parser import FuzzyMatcher

        matcher = FuzzyMatcher()
        fuzzy_result = matcher.find_best_church_match(token, churches)
        return fuzzy_result[0] if fuzzy_result else None
    except ImportError:
        for church_name in churches:
            if token.lower() in church_name.lower():
                return church_name
        return None


def recognize_city(token: str) -> Optional[str]:
    """Распознает город из токена"""
    if len(token) < 3:
        return None
    cities = get_reference_data("cities")
    token_upper = token.upper()
    for city_name in cities:
        if token_upper in city_name or city_name in token_upper:
            return city_name
    return None
