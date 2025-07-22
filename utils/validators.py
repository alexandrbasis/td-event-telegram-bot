from typing import Dict, Tuple, Optional, Set, Union
from messages import MESSAGES

# ✅ ИСПРАВЛЕНО: добавлен правильный импорт типов

VALID_SIZES = [
    "XS",
    "EXTRA SMALL",
    "EXTRASMALL",
    "S",
    "SMALL",
    "M",
    "MEDIUM",
    "L",
    "LARGE",
    "XL",
    "EXTRA LARGE",
    "EXTRALARGE",
    "XXL",
    "2XL",
    "EXTRA EXTRA LARGE",
    "3XL",
    "XXXL",
]

# ✅ НОВОЕ: набор валидных размеров для быстрой проверки
VALID_SIZES_SET: Set[str] = {size.upper() for size in VALID_SIZES}

# ✅ НОВОЕ: валидные значения для других полей
VALID_GENDERS: Set[str] = {"M", "F"}
VALID_ROLES: Set[str] = {"CANDIDATE", "TEAM"}

# ✅ НОВОЕ: обязательные поля
REQUIRED_FIELDS: Set[str] = {"FullNameRU", "Gender", "Church", "Role"}

# ✅ НОВОЕ: поля, которые требуются для роли TEAM
TEAM_REQUIRED_FIELDS: Set[str] = {"Department"}


def validate_size(size: str) -> bool:
    """
    ✅ УЛУЧШЕНО: валидация размера одежды.

    Args:
        size: Размер для проверки

    Returns:
        bool: True если размер валидный
    """
    if not size or not isinstance(size, str):
        return False
    return size.upper() in VALID_SIZES_SET


def validate_gender(gender: str) -> bool:
    """
    ✅ НОВАЯ ФУНКЦИЯ: валидация пола.

    Args:
        gender: Пол для проверки ('M' или 'F')

    Returns:
        bool: True если пол валидный
    """
    if not gender or not isinstance(gender, str):
        return False
    return gender.upper() in VALID_GENDERS


def validate_role(role: str) -> bool:
    """
    ✅ НОВАЯ ФУНКЦИЯ: валидация роли.

    Args:
        role: Роль для проверки ('CANDIDATE' или 'TEAM')

    Returns:
        bool: True если роль валидная
    """
    if not role or not isinstance(role, str):
        return False
    return role.upper() in VALID_ROLES


def validate_required_fields(
    data: Dict, required_fields: Set[str]
) -> Tuple[bool, Optional[str]]:
    """
    ✅ НОВАЯ ФУНКЦИЯ: проверка обязательных полей.

    Args:
        data: Данные для проверки
        required_fields: Набор обязательных полей

    Returns:
        Tuple[bool, Optional[str]]: (успех, сообщение об ошибке)
    """
    for field in required_fields:
        if not data.get(field):
            field_name = MESSAGES["VALIDATION_ERRORS"].get(field, field)
            return False, field_name
    return True, None


def validate_participant_data(data: Dict) -> Tuple[bool, str]:
    """
    ✅ ИСПРАВЛЕНО: правильный синтаксис типов Tuple[bool, str] вместо (bool, str).

    Валидирует данные участника на корректность.

    Args:
        data: Словарь с данными участника

    Returns:
        Tuple[bool, str]: (валидность, сообщение об ошибке)
            - (True, '') если данные валидные
            - (False, 'сообщение об ошибке') если есть проблемы

    Example:
        >>> data = {'FullNameRU': 'Иван Петров', 'Gender': 'M', ...}
        >>> valid, error = validate_participant_data(data)
        >>> if not valid:
        ...     print(f"Ошибка: {error}")
    """
    # ✅ УЛУЧШЕНО: проверяем тип входных данных
    if not isinstance(data, dict):
        return False, "Данные должны быть словарем"

    # ✅ УЛУЧШЕНО: проверяем обязательные поля
    valid, error = validate_required_fields(data, REQUIRED_FIELDS)
    if not valid:
        return False, error

    # ✅ УЛУЧШЕНО: валидация пола
    gender = data.get("Gender")
    if gender and not validate_gender(gender):
        return False, MESSAGES["VALIDATION_ERRORS"]["Gender"]

    # ✅ УЛУЧШЕНО: валидация роли
    role = data.get("Role")
    if role and not validate_role(role):
        return False, MESSAGES["VALIDATION_ERRORS"]["Role"]

    # ✅ УЛУЧШЕНО: проверка департамента для роли TEAM
    if data.get("Role") == "TEAM":
        valid, error = validate_required_fields(data, TEAM_REQUIRED_FIELDS)
        if not valid:
            return False, MESSAGES["VALIDATION_ERRORS"]["Department"]

    # ✅ УЛУЧШЕНО: валидация размера (если указан)
    size = data.get("Size")
    if size and not validate_size(size):
        return False, MESSAGES["VALIDATION_ERRORS"]["Size"]

    # ✅ УЛУЧШЕНО: валидация имени (не должно быть пустым)
    full_name = data.get("FullNameRU", "").strip()
    if not full_name:
        return False, MESSAGES["VALIDATION_ERRORS"]["FullNameRU"]

    # ✅ НОВОЕ: проверка длины имени
    if len(full_name) > 100:
        return False, "Имя слишком длинное (максимум 100 символов)"

    # ✅ НОВОЕ: проверка длины других полей
    text_fields = {
        "Church": 100,
        "ContactInformation": 200,
        "SubmittedBy": 100,
        "CountryAndCity": 100,
        "FullNameEN": 100,
        "Department": 50,
    }

    for field, max_length in text_fields.items():
        value = data.get(field, "")
        if value and len(str(value)) > max_length:
            return (
                False,
                f"Поле '{field}' слишком длинное (максимум {max_length} символов)",
            )

    return True, ""


def validate_partial_update(
    data: Dict, allowed_fields: Optional[Set[str]] = None
) -> Tuple[bool, str]:
    """
    ✅ НОВАЯ ФУНКЦИЯ: валидация частичного обновления данных.

    Args:
        data: Данные для частичного обновления
        allowed_fields: Разрешенные поля (None = все поля разрешены)

    Returns:
        Tuple[bool, str]: (валидность, сообщение об ошибке)
    """
    if not isinstance(data, dict):
        return False, "Данные должны быть словарем"

    if not data:
        return False, "Нет данных для обновления"

    # Проверяем разрешенные поля
    if allowed_fields is not None:
        invalid_fields = set(data.keys()) - allowed_fields
        if invalid_fields:
            return False, f"Недопустимые поля: {', '.join(invalid_fields)}"

    # Валидируем конкретные поля
    for field, value in data.items():
        if field == "Gender" and value and not validate_gender(value):
            return False, MESSAGES["VALIDATION_ERRORS"]["Gender"]
        elif field == "Role" and value and not validate_role(value):
            return False, MESSAGES["VALIDATION_ERRORS"]["Role"]
        elif field == "Size" and value and not validate_size(value):
            return False, MESSAGES["VALIDATION_ERRORS"]["Size"]
        elif field == "FullNameRU" and not value:
            return False, MESSAGES["VALIDATION_ERRORS"]["FullNameRU"]

    # Специальная проверка: если роль меняется на TEAM, нужен департамент
    if data.get("Role") == "TEAM" and "Department" not in data:
        return False, "При смене роли на TEAM необходимо указать департамент"

    return True, ""


def get_validation_errors_summary(data: Dict) -> Dict[str, str]:
    """
    ✅ НОВАЯ ФУНКЦИЯ: получить подробный отчет об ошибках валидации.

    Args:
        data: Данные для проверки

    Returns:
        Dict[str, str]: Словарь {поле: сообщение_об_ошибке}
    """
    errors = {}

    # Проверяем каждое поле отдельно
    if not data.get("FullNameRU", "").strip():
        errors["FullNameRU"] = MESSAGES["VALIDATION_ERRORS"]["FullNameRU"]

    gender = data.get("Gender")
    if gender and not validate_gender(gender):
        errors["Gender"] = MESSAGES["VALIDATION_ERRORS"]["Gender"]

    role = data.get("Role")
    if role and not validate_role(role):
        errors["Role"] = MESSAGES["VALIDATION_ERRORS"]["Role"]

    if data.get("Role") == "TEAM" and not data.get("Department"):
        errors["Department"] = MESSAGES["VALIDATION_ERRORS"]["Department"]

    size = data.get("Size")
    if size and not validate_size(size):
        errors["Size"] = MESSAGES["VALIDATION_ERRORS"]["Size"]

    if not data.get("Church", "").strip():
        errors["Church"] = MESSAGES["VALIDATION_ERRORS"]["Church"]

    return errors


# ✅ НОВОЕ: вспомогательные функции для использования в других модулях


def is_valid_participant_field(field_name: str, value: Union[str, None]) -> bool:
    """
    Проверяет валидность одного поля участника.

    Args:
        field_name: Название поля
        value: Значение поля

    Returns:
        bool: True если поле валидное
    """
    if value is None:
        return field_name not in REQUIRED_FIELDS

    if field_name == "Gender":
        return validate_gender(value)
    elif field_name == "Role":
        return validate_role(value)
    elif field_name == "Size":
        return validate_size(value) if value else True
    elif field_name in REQUIRED_FIELDS:
        return bool(str(value).strip())

    return True


def get_field_constraints() -> Dict[str, Dict]:
    """
    ✅ НОВАЯ ФУНКЦИЯ: возвращает ограничения для полей.

    Полезно для фронтенда или автодокументации.

    Returns:
        Dict с ограничениями для каждого поля
    """
    return {
        "FullNameRU": {
            "type": "string",
            "required": True,
            "max_length": 100,
            "min_length": 1,
        },
        "Gender": {"type": "choice", "required": True, "choices": list(VALID_GENDERS)},
        "Role": {"type": "choice", "required": True, "choices": list(VALID_ROLES)},
        "Size": {"type": "choice", "required": False, "choices": VALID_SIZES},
        "Church": {"type": "string", "required": True, "max_length": 100},
        "Department": {
            "type": "string",
            "required": False,  # Обязательно только для TEAM
            "max_length": 50,
        },
    }
