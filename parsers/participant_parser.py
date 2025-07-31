from typing import Dict, Optional, List
from dataclasses import dataclass
import re
import logging

from utils.field_normalizer import (
    field_normalizer,
    normalize_gender,
    normalize_role,
    normalize_size,
    normalize_department,
)
from utils.cache import cache
from utils.recognizers import (
    recognize_role,
    recognize_gender,
    recognize_size,
    recognize_department,
    recognize_church,
    recognize_city,
)


@dataclass
class ConflictContext:
    """Контекст для разрешения конфликтов токенов."""

    token: str
    token_index: int
    surrounding_tokens: List[str]
    already_found_gender: bool
    already_found_size: bool


class TokenConflictResolver:
    """Разрешает конфликты при парсинге токенов (например, M как пол vs размер)."""

    def __init__(self, field_normalizer):
        self.field_normalizer = field_normalizer

        # Индикаторы контекста для полей
        self.gender_context_words = {
            "ПОЛ",
            "GENDER",
            "МУЖСКОЙ",
            "ЖЕНСКИЙ",
            "МУЖЧИНА",
            "ЖЕНЩИНА",
        }

        self.size_context_words = {
            "РАЗМЕР",
            "SIZE",
            "ОДЕЖДА",
            "ФУТБОЛКА",
            "РУБАШКА",
            "CLOTHING",
        }

    def resolve_m_conflict(
        self, context: ConflictContext
    ) -> tuple[Optional[str], Optional[str]]:
        """Разрешает конфликт токена 'M' между полом и размером."""

        token_upper = context.token.upper()

        if token_upper != "M":
            return None, None

        surrounding_upper = [t.upper() for t in context.surrounding_tokens]

        strong_size_indicators = any(
            word in surrounding_upper for word in self.size_context_words
        )

        strong_gender_indicators = any(
            word in surrounding_upper for word in self.gender_context_words
        )

        other_sizes_nearby = False
        for token in context.surrounding_tokens:
            if normalize_size(token) and normalize_size(token) != "M":
                other_sizes_nearby = True
                break

        if strong_size_indicators:
            return None, "M"

        if strong_gender_indicators:
            return "M", None

        if context.already_found_gender and not context.already_found_size:
            return None, "M"

        if context.already_found_size and not context.already_found_gender:
            return "M", None

        if other_sizes_nearby:
            if context.already_found_size or strong_size_indicators:
                return None, "M"
            return "M", None

        return "M", None

    def get_surrounding_context(
        self, all_words: List[str], target_index: int, window: int = 2
    ) -> List[str]:
        """Получает окружающие токены в заданном окне."""

        start = max(0, target_index - window)
        end = min(len(all_words), target_index + window + 1)

        context = []
        for i in range(start, end):
            if i != target_index:
                context.append(all_words[i])

        return context


logger = logging.getLogger(__name__)


def is_valid_email(email: str) -> bool:
    """Проверяет корректность email адреса."""
    if "@" not in email:
        return False

    try:
        local, domain = email.rsplit("@", 1)
    except ValueError:
        return False

    if not local:
        return False

    if not domain or "." not in domain:
        return False

    domain_parts = domain.split(".")
    if len(domain_parts[-1]) < 2:
        return False

    if len(email) < 5 or len(email) > 254:
        return False

    invalid_chars = {" ", "\t", "\n", "\r"}
    if any(char in email for char in invalid_chars):
        return False

    return True


def is_valid_phone(phone: str) -> bool:
    """Проверяет корректность израильского номера телефона."""
    if not phone:
        return False

    # Оставляем только цифры и плюс
    cleaned = "".join(c for c in phone if c.isdigit() or c == "+")
    digits = "".join(c for c in cleaned if c.isdigit())

    if len(digits) < 7:
        return False

    if len(digits) > 15:
        return False

    if len(set(digits)) == 1:
        return False

    # 1. Международный формат +972
    if phone.startswith("+972"):
        if len(digits) in (11, 12):
            israeli_part = digits[3:]

            mobile_prefixes = ["50", "52", "53", "54", "55", "58"]
            if israeli_part[:2] in mobile_prefixes and len(israeli_part) == 9:
                return True

            landline_prefixes = ["2", "3", "4", "8", "9"]
            if israeli_part[0] in landline_prefixes and len(israeli_part) == 8:
                return True

        return False

    # 2. Местный израильский формат (без +972)
    if digits.startswith("05"):
        if len(digits) in [9, 10]:
            mobile_codes = ["050", "052", "053", "054", "055", "058"]
            if digits[:3] in mobile_codes:
                return True
        return False

    if digits.startswith("0") and len(digits) == 9:
        landline_prefixes = ["02", "03", "04", "08", "09"]
        if digits[:2] in landline_prefixes:
            return True
        return False

    # 3. Другие международные номера
    if phone.startswith("+"):
        if 7 <= len(digits) <= 15:
            return True

    # 4. Российские номера
    if phone.startswith(("8", "7")) and len(digits) >= 10:
        return True

    # 5. Номера с форматированием
    if len(digits) >= 7 and any(char in phone for char in ["-", "(", ")", " ", "."]):
        formatting_chars = sum(1 for c in phone if c in "-()., ")
        if formatting_chars <= len(digits):
            return True

    return False


def extract_contact_info(word: str) -> Optional[str]:
    """Извлекает и валидирует контактную информацию из токена."""
    word = word.strip()

    if not word:
        return None

    if "@" in word:
        return word if is_valid_email(word) else None

    if any(c.isdigit() for c in word):
        return word if is_valid_phone(word) else None

    return None


CHURCH_KEYWORDS = ["ЦЕРКОВЬ", "CHURCH", "ХРАМ", "ОБЩИНА"]

# Punctuation characters to strip when normalizing tokens
PUNCTUATION_CHARS = ".,!?:;"

# Pre-computed synonym sets for performance
GENDER_SYNONYMS = {
    syn.upper()
    for synonyms in field_normalizer.GENDER_MAPPINGS.values()
    for syn in synonyms
}
SIZE_SYNONYMS = {
    syn.upper()
    for synonyms in field_normalizer.SIZE_MAPPINGS.values()
    for syn in synonyms
}
ROLE_SYNONYMS = {
    syn.upper()
    for synonyms in field_normalizer.ROLE_MAPPINGS.values()
    for syn in synonyms
}


# Служебные слова, которые встречаются в блоке подтверждения
CONFIRMATION_NOISE_WORDS = {
    "ВОТ",
    "ЧТО",
    "Я",
    "ПОНЯЛ",
    "ИЗ",
    "ВАШИХ",
    "ДАННЫХ",
    "ИМЯ",
    "РУС",
    "АНГЛ",
    "ПОЛ",
    "РАЗМЕР",
    "ГОРОД",
    "КТО",
    "ПОДАЛ",
    "КОНТАКТЫ",
    "НЕ",
    "УКАЗАНО",
    "РОЛЬ",
    "ДЕПАРТАМЕНТ",
    "ВСЕГО",
    "ПРАВИЛЬНО",
    "ОТПРАВЬТЕ",
    "ДА",
    "ДЛЯ",
    "СОХРАНЕНИЯ",
    "НЕТ",
    "ОТМЕНЫ",
    "ИЛИ",
    "ПРИШЛИТЕ",
    "ИСПРАВЛЕННЫЕ",
    "ПО",
    "ТЕМПЛЕЙТУ",
    "ПОЛНОЙ",
    "CANCEL",
}

# Подсказки для определения поля при исправлении
FIELD_INDICATORS = {
    "Gender": ["ПОЛ", "GENDER"],
    "Size": ["РАЗМЕР", "SIZE"],
    "Role": ["РОЛЬ", "ROLE"],
    "Department": ["ДЕПАРТАМЕНТ", "DEPARTMENT"],
    "Church": ["ЦЕРКОВЬ", "CHURCH"],
    "FullNameRU": ["ИМЯ", "РУССКИЙ", "NAME"],
    "FullNameEN": ["АНГЛИЙСКИЙ", "ENGLISH", "АНГЛ"],
    "CountryAndCity": ["ГОРОД", "CITY", "СТРАНА"],
    "SubmittedBy": ["ПОДАЛ", "SUBMITTED"],
    "ContactInformation": ["КОНТАКТ", "ТЕЛЕФОН", "EMAIL", "PHONE"],
}

# Поля шаблона и их соответствие ключам базы данных
TEMPLATE_FIELD_MAP = {
    "Имя (рус)": "FullNameRU",
    "Имя (англ)": "FullNameEN",
    "Пол": "Gender",
    "Размер": "Size",
    "Церковь": "Church",
    "Роль": "Role",
    "Департамент": "Department",
    "Город": "CountryAndCity",
    "Кто подал": "SubmittedBy",
    "Контакты": "ContactInformation",
}


def is_template_format(text: str) -> bool:
    """Определяет, похоже ли сообщение на заполненный шаблон."""
    count = 0
    for field in TEMPLATE_FIELD_MAP.keys():
        if re.search(rf"{re.escape(field)}\s*:", text, re.IGNORECASE):
            count += 1
    result = count >= 3
    logger.debug("is_template_format=%s for text: %s", result, text)
    return result


def parse_template_format(text: str) -> Dict:
    """Парсит текст, оформленный по шаблону Ключ: Значение."""
    data: Dict = {}
    # Разделяем по переносу строк и возможным разделителям
    parts = re.split(r"[\n;]+", text)
    items = []
    for part in parts:
        items.extend(part.split(","))

    for item in items:
        if ":" not in item:
            continue
        key, value = item.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value in ["➖ Не указано", "❌ Не указано"]:
            value = ""
        for ru, eng in TEMPLATE_FIELD_MAP.items():
            if key.lower() == ru.lower():
                norm = value or ""
                if eng == "Gender":
                    norm = normalize_gender(value) or ""
                elif eng == "Role":
                    norm = normalize_role(value) or ""
                elif eng == "Department":
                    norm = normalize_department(value) or ""
                elif eng == "Size":
                    norm = normalize_size(value) or ""
                data[eng] = norm
                break
    logger.debug("parse_template_format parsed fields: %s", list(data.keys()))
    return data


def parse_unstructured_text(text: str) -> Dict[str, str]:
    """Parses unstructured text using a non-destructive, prioritized, multi-pass strategy."""
    participant_data: Dict[str, str] = {}
    tokens = text.split()
    # A list to mark which tokens have been successfully parsed and "consumed"
    consumed = [False] * len(tokens)

    # --- Pass 1: Match multi-word known church names (highest priority) ---
    known_churches = cache.get("churches") or []
    # Sort by number of words in name, descending, to match "Слово Жизни" before "Слово"
    sorted_church_names = sorted(
        known_churches, key=lambda x: len(x.split()), reverse=True
    )
    for church_name_str in sorted_church_names:
        name_tokens = church_name_str.split()
        for i in range(len(tokens) - len(name_tokens) + 1):
            # Slice of tokens from the input to check for a match
            chunk = tokens[i : i + len(name_tokens)]
            # Check if this chunk has already been consumed
            if any(consumed[i : i + len(name_tokens)]):
                continue
            # Compare lowercased tokens
            if [t.lower() for t in chunk] == [nt.lower() for nt in name_tokens]:
                participant_data["Church"] = church_name_str.capitalize()
                for j in range(i, i + len(name_tokens)):
                    consumed[j] = True
                # Consume a nearby church identifier if present to avoid it ending up in the name
                church_identifiers = {kw.lower() for kw in CHURCH_KEYWORDS}
                if i > 0 and tokens[i - 1].lower() in church_identifiers:
                    consumed[i - 1] = True
                elif (
                    i + len(name_tokens) < len(tokens)
                    and tokens[i + len(name_tokens)].lower() in church_identifiers
                ):
                    consumed[i + len(name_tokens)] = True
                break
        if "Church" in participant_data:
            break

    # --- Pass 2: Match "keyword + value" pattern for churches (e.g., "церковь Грейс") ---
    # This runs only if we haven't already found a church
    church_identifiers = {kw.lower() for kw in CHURCH_KEYWORDS}
    if "Church" not in participant_data:
        for i in range(len(tokens) - 1):
            if (
                not consumed[i]
                and not consumed[i + 1]
                and tokens[i].lower() in church_identifiers
            ):
                participant_data["Church"] = tokens[i + 1].capitalize()
                consumed[i] = True  # Consume the identifier (e.g., "церковь")
                consumed[i + 1] = True  # Consume the name
                break

    # --- Pass 2.5: Match "keyword + value" for cities (e.g., "город Хайфа") ---
    city_identifiers = {"город", "из", "city", "from"}
    if "CountryAndCity" not in participant_data:
        for i in range(len(tokens) - 1):
            if (
                not consumed[i]
                and not consumed[i + 1]
                and tokens[i].lower() in city_identifiers
            ):
                participant_data["CountryAndCity"] = tokens[i + 1].capitalize()
                consumed[i] = True
                consumed[i + 1] = True
                break

    # --- Pass 3: Match all other single-token fields ---
    recognizers = {
        "Role": recognize_role,
        "Gender": recognize_gender,
        "Size": recognize_size,
        "Department": recognize_department,
        "CountryAndCity": recognize_city,
        "Church": recognize_church,  # Fallback for single-word church names without identifier
    }
    for i, token in enumerate(tokens):
        if consumed[i]:
            continue
        for field, func in recognizers.items():
            # Do not overwrite already found data
            if field in participant_data:
                continue
            result = func(token)
            if result:
                participant_data[field] = result
                consumed[i] = True
                break

    # --- Pass 4: Everything that is left is the name ---
    name_parts = [tokens[i] for i in range(len(tokens)) if not consumed[i]]
    if name_parts:
        participant_data["FullNameRU"] = " ".join(name_parts)

    return participant_data


def contains_hebrew(text: str) -> bool:
    return any("\u0590" <= char <= "\u05ff" for char in text)


def contains_emoji(text: str) -> bool:
    """Проверяет наличие эмодзи"""
    return any(
        "\U0001f600" <= char <= "\U0001f64f"  # Emoticons
        or "\U0001f300" <= char <= "\U0001f5ff"  # Misc Symbols
        or "\U0001f680" <= char <= "\U0001f6ff"  # Transport & Map
        or "\U0001f1e0" <= char <= "\U0001f1ff"  # Regional
        or "\U00002600" <= char <= "\U000027bf"  # Misc
        or "\U0001f900" <= char <= "\U0001f9ff"
        for char in text
    )


def clean_text_from_confirmation_block(text: str) -> str:
    """Удаляет эмодзи и служебные слова из текста подтверждения"""
    cleaned = "".join(ch for ch in text if not contains_emoji(ch))
    cleaned = cleaned.replace("**", "").replace("*", "")
    cleaned = cleaned.replace("🔍", "").replace("•", "")

    field_labels = [
        "Имя (рус)",
        "Имя (англ)",
        "Пол",
        "Размер",
        "Церковь",
        "Роль",
        "Департамент",
        "Город",
        "Кто подал",
        "Контакты",
    ]

    for label in field_labels:
        cleaned = re.sub(rf"{label}\s*:", "", cleaned, flags=re.IGNORECASE)

    cleaned = cleaned.replace(":", "")

    words = cleaned.split()
    filtered = []
    for word in words:
        w = word.strip(".,!?:;").upper()
        if (
            w not in CONFIRMATION_NOISE_WORDS
            and not w.startswith("➖")
            and not w.startswith("❌")
            and len(w) > 0
        ):
            filtered.append(word)

    return " ".join(filtered)


def detect_field_update_intent(text: str) -> Optional[str]:
    """Определяет, какое поле хочет обновить пользователь"""
    text_upper = text.upper()
    words = re.split(r"\s+", text_upper)

    for field, indicators in FIELD_INDICATORS.items():
        for ind in indicators:
            if ind in words:
                return field

    if any(word in GENDER_SYNONYMS for word in words):
        return "Gender"

    if any(word in SIZE_SYNONYMS for word in words):
        return "Size"

    return None


def parse_field_update(text: str, field_hint: str) -> Dict:
    """Парсит исправление конкретного поля"""
    text_clean = clean_text_from_confirmation_block(text)
    words = text_clean.split()
    update: Dict = {}

    if field_hint == "Gender":
        for word in words:
            gender_val = normalize_gender(word)
            if gender_val:
                update["Gender"] = gender_val
                break

    elif field_hint == "Size":
        for word in words:
            size_val = normalize_size(word)
            if size_val:
                update["Size"] = size_val
                break

    elif field_hint == "Role":
        for word in words:
            role_val = normalize_role(word)
            if role_val:
                update["Role"] = role_val
                break

    elif field_hint == "Department":
        for word in words:
            dept_val = normalize_department(word)
            if dept_val:
                update["Department"] = dept_val
                break

    elif field_hint == "Church":
        church_words = []
        for word in words:
            if not any(
                kw in word.upper() for kw in CHURCH_KEYWORDS
            ) and not contains_hebrew(word):
                church_words.append(word)
        if church_words:
            update["Church"] = " ".join(church_words)

    elif field_hint == "CountryAndCity":
        cities = cache.get("cities") or []
        for word in words:
            if word.upper() in cities:
                update["CountryAndCity"] = word
                break

    return update


class ParticipantParser:
    def __init__(self):
        self.data: Dict = {}
        self.processed_words: set[str] = set()
        self.department_keywords = cache.get("departments") or {}
        self.israel_cities = cache.get("cities") or []
        # Cache synonym sets for performance
        self._size_synonyms = SIZE_SYNONYMS
        self._role_synonyms = ROLE_SYNONYMS
        self._dept_synonyms = {
            syn.upper()
            for synonyms in self.department_keywords.values()
            for syn in synonyms
        }

    def parse(self, text: str, is_update: bool = False) -> Dict:
        """Основной метод парсинга."""
        text, early = self._preprocess_text(text, is_update)
        if early is not None:
            return early

        all_words = text.split()
        self.data = {
            "FullNameRU": "",
            "Gender": "",
            "Size": "",
            "Church": "",
            "Role": "CANDIDATE",
            "Department": "",
            "FullNameEN": "",
            "SubmittedBy": "",
            "ContactInformation": "",
            "CountryAndCity": "",
        }
        self.processed_words = set()

        self._extract_all_fields(all_words, text)
        self._postprocess_data()

        logger.debug("ParticipantParser result: %s", self.data)
        return self.data

    def _preprocess_text(
        self, text: str, is_update: bool
    ) -> tuple[str, Optional[Dict]]:
        text = text.strip()
        if is_template_format(text):
            logger.debug("Parsing using template format")
            return "", parse_template_format(text)

        if is_update:
            text = clean_text_from_confirmation_block(text)
            field_hint = detect_field_update_intent(text)
            if field_hint:
                logger.debug("Detected field update intent: %s", field_hint)
                return "", parse_field_update(text, field_hint)

        return text, None

    def _extract_all_fields(self, all_words: list[str], original_text: str):
        self._extract_contacts(all_words)
        self._extract_gender(all_words)
        self._extract_size(all_words)
        self._extract_role_and_department(all_words)
        self._extract_city(all_words)

        self._extract_church(all_words)
        self._extract_submitted_by(original_text)
        self._extract_names(all_words)

    def _postprocess_data(self):
        if not self.data.get("Gender"):
            self.data["Gender"] = "F"

    def _extract_submitted_by(self, text: str):
        """Извлекает информацию о том, кто подал заявку."""
        match = re.search(r"от\s+([А-ЯЁA-Z][А-Яа-яёA-Za-z\s]+)", text, re.IGNORECASE)
        if match:
            full_match = match.group(1).strip()
            words = full_match.split()

            valid_words = []
            for word in words:
                if word not in self.processed_words:
                    word_upper = word.upper()
                    if (
                        word_upper not in self._size_synonyms
                        and word_upper not in self._role_synonyms
                        and word_upper not in self._dept_synonyms
                    ):
                        valid_words.append(word)
                    else:
                        break

            if valid_words:
                self.data["SubmittedBy"] = " ".join(valid_words)
                for word in valid_words:
                    self.processed_words.add(word)
                self.processed_words.add("от")

    def _extract_contacts(self, all_words: list[str]):
        for word in all_words:
            if word in self.processed_words:
                continue

            token = word.strip(PUNCTUATION_CHARS)
            contact = extract_contact_info(token)
            if contact:
                self.data["ContactInformation"] = contact
                self.processed_words.add(word)
                break

    def _extract_gender(self, all_words: list[str]):
        """Извлекает пол участника с улучшенным разрешением конфликтов."""
        resolver = TokenConflictResolver(field_normalizer)

        gender_explicit = False
        for word in all_words:
            if word in self.processed_words:
                continue
            wu = word.strip(PUNCTUATION_CHARS).upper()
            if wu in field_normalizer.GENDER_MAPPINGS["F"]:
                self.data["Gender"] = "F"
                gender_explicit = True
                self.processed_words.add(word)
                return

        for idx, word in enumerate(all_words):
            if word in self.processed_words:
                continue
            wu = word.strip(PUNCTUATION_CHARS).upper()

            if wu in field_normalizer.GENDER_MAPPINGS["M"] and not gender_explicit:
                if wu == "M":
                    context = ConflictContext(
                        token=word,
                        token_index=idx,
                        surrounding_tokens=resolver.get_surrounding_context(
                            all_words, idx
                        ),
                        already_found_gender=bool(self.data.get("Gender")),
                        already_found_size=bool(self.data.get("Size")),
                    )

                    gender_value, size_value = resolver.resolve_m_conflict(context)

                    if gender_value:
                        self.data["Gender"] = gender_value
                        self.processed_words.add(word)
                        break
                    elif size_value:
                        self.data["Size"] = size_value
                        self.processed_words.add(word)
                else:
                    self.data["Gender"] = "M"
                    self.processed_words.add(word)
                    break

    def _extract_size(self, all_words: list[str]):
        for word in all_words:
            if word in self.processed_words:
                continue
            size_val = normalize_size(word)
            if size_val:
                self.data["Size"] = size_val
                self.processed_words.add(word)

    def _extract_role_and_department(self, all_words: list[str]):
        for word in all_words:
            if word in self.processed_words:
                continue
            role_val = normalize_role(word)
            if role_val:
                self.data["Role"] = role_val
                self.processed_words.add(word)
            elif not contains_hebrew(word):
                dept_val = normalize_department(word)
                if dept_val:
                    self.data["Department"] = dept_val
                    self.processed_words.add(word)

    def _extract_city(self, all_words: list[str]):
        for word in all_words:
            if word in self.processed_words or contains_hebrew(word):
                continue
            wu = word.strip(PUNCTUATION_CHARS).upper()
            if wu in self.israel_cities:
                self.data["CountryAndCity"] = word
                self.processed_words.add(word)

    def _extract_church(self, all_words: list[str]):
        for i, word in enumerate(all_words):
            if word in self.processed_words:
                continue
            word_upper = word.upper()
            if any(keyword in word_upper for keyword in CHURCH_KEYWORDS):
                church_words = []
                if (
                    i > 0
                    and all_words[i - 1] not in self.processed_words
                    and not contains_hebrew(all_words[i - 1])
                ):
                    church_words.append(all_words[i - 1])
                    self.processed_words.add(all_words[i - 1])
                church_words.append(word)
                self.processed_words.add(word)
                if (
                    i < len(all_words) - 1
                    and all_words[i + 1] not in self.processed_words
                    and not contains_hebrew(all_words[i + 1])
                ):
                    church_words.append(all_words[i + 1])
                    self.processed_words.add(all_words[i + 1])
                self.data["Church"] = " ".join(church_words)
                break

    def _extract_names(self, all_words: list[str]):
        unprocessed = [w for w in all_words if w not in self.processed_words]
        russian_words = []
        english_words = []
        for word in unprocessed:
            if word.isalpha() and all(ord(c) < 128 for c in word):
                english_words.append(word)
            else:
                russian_words.append(word)
        if russian_words:
            self.data["FullNameRU"] = " ".join(russian_words[:2])
        if english_words:
            self.data["FullNameEN"] = " ".join(english_words[:2])


def parse_participant_data(text: str, is_update: bool = False) -> Dict:
    """Извлекает данные участника из произвольного текста."""
    parser = ParticipantParser()
    return parser.parse(text, is_update)


def normalize_field_value(field_name: str, value: str) -> str:
    """Нормализует одно значение для указанного поля."""
    value = value.strip()

    if field_name == "Department":
        return normalize_department(value) or ""

    if field_name == "Gender":
        return normalize_gender(value) or ""

    if field_name == "Size":
        return normalize_size(value) or ""

    if field_name == "Role":
        return normalize_role(value) or "CANDIDATE"

    return value
