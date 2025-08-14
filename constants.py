from enum import Enum


class Gender(Enum):
    MALE = "M"
    FEMALE = "F"


class Role(Enum):
    CANDIDATE = "CANDIDATE"
    TEAM = "TEAM"


class PaymentStatus(Enum):
    UNPAID = "Unpaid"
    PAID = "Paid"
    PARTIAL = "Partial"
    REFUNDED = "Refunded"


# === DISPLAY_NAMES ===
# Отображаемые названия для пользователей
GENDER_DISPLAY = {"M": "Мужской", "F": "Женский"}
ROLE_DISPLAY = {"CANDIDATE": "Кандидат", "TEAM": "Команда"}
SIZE_DISPLAY = {
    "XS": "XS",
    "S": "S",
    "M": "M",
    "L": "L",
    "XL": "XL",
    "XXL": "XXL",
    "3XL": "3XL",
}

DEPARTMENT_DISPLAY = {
    "ROE": "РОЕ",
    "Chapel": "Молитвенная",
    "Setup": "Сетап",
    "Palanka": "Паланка",
    "Administration": "Администрация",
    "Kitchen": "Кухня",
    "Decoration": "Декорации",
    "Bell": "Звонарь",
    "Refreshment": "Рефрешмент",
    "Worship": "Прославление",
    "Media": "Медиа",
    "Clergy": "Духовенство",
    "Rectorate": "Ректорат",
}

PAYMENT_STATUS_DISPLAY = {
    "Unpaid": "❌ Не оплачено",
    "Paid": "✅ Оплачено",
    "Partial": "🔶 Частично оплачено",
    "Refunded": "🔄 Возвращено",
}

# Reverse lookups for parsing display names back to system keys
DISPLAY_TO_GENDER = {v.lower(): k for k, v in GENDER_DISPLAY.items()}
DISPLAY_TO_ROLE = {v.lower(): k for k, v in ROLE_DISPLAY.items()}
DISPLAY_TO_SIZE = {v.lower(): k for k, v in SIZE_DISPLAY.items()}
DISPLAY_TO_DEPARTMENT = {v.lower(): k for k, v in DEPARTMENT_DISPLAY.items()}
# Создаем обратный mapping для payment status
DISPLAY_TO_PAYMENT_STATUS = {}
for k, v in PAYMENT_STATUS_DISPLAY.items():
    # Убираем эмодзи и создаем mapping только по тексту
    clean_text = v.replace("❌ ", "").replace("✅ ", "").replace("🔶 ", "").replace("🔄 ", "")
    DISPLAY_TO_PAYMENT_STATUS[clean_text.lower()] = k


def gender_from_display(name: str) -> str:
    """Return internal gender key for a Russian display name."""
    return DISPLAY_TO_GENDER.get(name.strip().lower(), "")


def role_from_display(name: str) -> str:
    """Return internal role key for a Russian display name."""
    return DISPLAY_TO_ROLE.get(name.strip().lower(), "")


def size_from_display(name: str) -> str:
    """Return internal size key for a Russian display name."""
    return DISPLAY_TO_SIZE.get(name.strip().lower(), "")


def department_from_display(name: str) -> str:
    """Return internal department key for a Russian display name."""
    return DISPLAY_TO_DEPARTMENT.get(name.strip().lower(), "")


def payment_status_from_display(name: str) -> str:
    """Return internal payment status key for a Russian display name."""
    return DISPLAY_TO_PAYMENT_STATUS.get(name.strip().lower(), "Unpaid")


ISRAEL_CITIES = [
    "ХАЙФА",
    "HAIFA",
    "ТЕЛ-АВИВ",
    "TEL AVIV",
    "ТЕЛЬ-АВИВ",
    "ИЕРУСАЛИМ",
    "JERUSALEM",
    "БЕЭР-ШЕВА",
    "BEER SHEVA",
    "НЕТАНИЯ",
    "NETANYA",
    "АШДОД",
    "ASHDOD",
    "РИШОН-ЛЕ-ЦИОН",
    "РИШОН ЛЕ ЦИОН",
    "РИШОН-ЛЕ ЦИОН",
    "РИШОН ЛЕЦИОН",
    "RISHON LEZION",
    "RISHON-LEZION",
    "RISHON LE ZION",
    "RISHON-LE ZION",
    "ПЕТАХ-ТИКВА",
    "PETAH TIKVA",
    "РЕХОВОТ",
    "REHOVOT",
    "БАТ-ЯМ",
    "BAT YAM",
    "КАРМИЭЛЬ",
    "CARMIEL",
    "МОДИИН",
    "MODIIN",
    "НАЗАРЕТ",
    "NAZARETH",
    "КИРЬЯТ-ГАТ",
    "KIRYAT GAT",
    "ЭЙЛАТ",
    "EILAT",
    "АККО",
    "ACRE",
    "РАМАТ-ГАН",
    "RAMAT GAN",
    "БНЕЙ-БРАК",
    "BNEI BRAK",
    "ЦФАТ",
    "SAFED",
    "ТВЕРИЯ",
    "TIBERIAS",
    "ГЕРЦЛИЯ",
    "HERZLIYA",
    "АФУЛА",
    "AFULA",
]
