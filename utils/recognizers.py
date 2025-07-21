from typing import Optional
from utils.cache import cache

ROLE_MAP = {
    'тим': 'TEAM', 'команда': 'TEAM', 'team': 'TEAM',
    'участник': 'Participant', 'кандидат': 'Participant', 'participant': 'Participant'
}

GENDER_MAP = {
    'м': 'M', 'm': 'M', 'муж': 'M', 'мужской': 'M',
    'ж': 'F', 'f': 'F', 'жен': 'F', 'женский': 'F'
}

SIZE_MAP = {
    'xs': 'XS', 's': 'S', 'm': 'M', 'l': 'L', 'xl': 'XL', 'xxl': 'XXL',
    'хс': 'XS', 'с': 'S', 'м': 'M', 'л': 'L', 'хл': 'XL', 'ххл': 'XXL'
}

DEPARTMENT_MAP = {
    'админ': 'Administration', 'администрация': 'Administration',
    'кухня': 'Kitchen',
    'прославление': 'Worship', 'воршип': 'Worship',
}


def get_reference_data(key: str):
    return cache.get(key) or []


def recognize_role(token: str) -> Optional[str]:
    return ROLE_MAP.get(token.lower())


def recognize_gender(token: str) -> Optional[str]:
    return GENDER_MAP.get(token.lower())


def recognize_size(token: str) -> Optional[str]:
    return SIZE_MAP.get(token.lower())


def recognize_department(token: str) -> Optional[str]:
    for alias, standard in DEPARTMENT_MAP.items():
        if alias in token.lower():
            return standard
    return None


def recognize_church(token: str) -> Optional[str]:
    if len(token) < 3:
        return None
    churches = get_reference_data('churches')
    for church_name in churches:
        if token.lower() in church_name.lower():
            return church_name
    return None


def recognize_city(token: str) -> Optional[str]:
    if len(token) < 3:
        return None
    cities = get_reference_data('cities')
    for city_name in cities:
        if token.lower() in city_name.lower():
            return city_name
    return None
