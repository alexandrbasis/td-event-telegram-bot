from typing import Optional
from utils.cache import cache
from utils.field_normalizer import (
    normalize_gender,
    normalize_role,
    normalize_size,
    normalize_department,
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
    """Распознает департамент из токена"""
    return normalize_department(token)


def recognize_church(token: str) -> Optional[str]:
    """Распознает церковь из токена"""
    if len(token) < 3:
        return None
    churches = get_reference_data("churches")
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
