from typing import Dict, Optional
import re
import logging

from constants import (
    GENDER_KEYWORDS,
    ROLE_KEYWORDS,
    DEPARTMENT_KEYWORDS,
    SIZES,
    ISRAEL_CITIES,
    Gender,
    Role,
)

logger = logging.getLogger(__name__)

CHURCH_KEYWORDS = ['ЦЕРКОВЬ', 'CHURCH', 'ХРАМ', 'ОБЩИНА']

# Служебные слова, которые встречаются в блоке подтверждения
CONFIRMATION_NOISE_WORDS = {
    'ВОТ', 'ЧТО', 'Я', 'ПОНЯЛ', 'ИЗ', 'ВАШИХ', 'ДАННЫХ', 'ИМЯ', 'РУС', 'АНГЛ',
    'ПОЛ', 'РАЗМЕР', 'ГОРОД', 'КТО', 'ПОДАЛ', 'КОНТАКТЫ', 'НЕ', 'УКАЗАНО', 'РОЛЬ',
    'ДЕПАРТАМЕНТ', 'ВСЕГО', 'ПРАВИЛЬНО', 'ОТПРАВЬТЕ', 'ДА', 'ДЛЯ', 'СОХРАНЕНИЯ',
    'НЕТ', 'ОТМЕНЫ', 'ИЛИ', 'ПРИШЛИТЕ', 'ИСПРАВЛЕННЫЕ', 'ПО', 'ТЕМПЛЕЙТУ',
    'ПОЛНОЙ', 'CANCEL'
}

# Подсказки для определения поля при исправлении
FIELD_INDICATORS = {
    'Gender': ['ПОЛ', 'GENDER'],
    'Size': ['РАЗМЕР', 'SIZE'],
    'Role': ['РОЛЬ', 'ROLE'],
    'Department': ['ДЕПАРТАМЕНТ', 'DEPARTMENT'],
    'Church': ['ЦЕРКОВЬ', 'CHURCH'],
    'FullNameRU': ['ИМЯ', 'РУССКИЙ', 'NAME'],
    'FullNameEN': ['АНГЛИЙСКИЙ', 'ENGLISH', 'АНГЛ'],
    'CountryAndCity': ['ГОРОД', 'CITY', 'СТРАНА'],
    'SubmittedBy': ['ПОДАЛ', 'SUBMITTED'],
    'ContactInformation': ['КОНТАКТ', 'ТЕЛЕФОН', 'EMAIL', 'PHONE']
}

# Поля шаблона и их соответствие ключам базы данных
TEMPLATE_FIELD_MAP = {
    'Имя (рус)': 'FullNameRU',
    'Имя (англ)': 'FullNameEN',
    'Пол': 'Gender',
    'Размер': 'Size',
    'Церковь': 'Church',
    'Роль': 'Role',
    'Департамент': 'Department',
    'Город': 'CountryAndCity',
    'Кто подал': 'SubmittedBy',
    'Контакты': 'ContactInformation',
}


def is_template_format(text: str) -> bool:
    """Определяет, похоже ли сообщение на заполненный шаблон."""
    count = 0
    for field in TEMPLATE_FIELD_MAP.keys():
        if re.search(fr'{re.escape(field)}\s*:', text, re.IGNORECASE):
            count += 1
    result = count >= 3
    logger.debug("is_template_format=%s for text: %s", result, text)
    return result


def parse_template_format(text: str) -> Dict:
    """Парсит текст, оформленный по шаблону Ключ: Значение."""
    data: Dict = {}
    # Разделяем по переносу строк и возможным разделителям
    parts = re.split(r'[\n;]+', text)
    items = []
    for part in parts:
        items.extend(part.split(','))
    for item in items:
        if ':' not in item:
            continue
        key, value = item.split(':', 1)
        key = key.strip()
        value = value.strip()
        if value in ['➖ Не указано', '❌ Не указано']:
            value = ''
        for ru, eng in TEMPLATE_FIELD_MAP.items():
            if key.lower() == ru.lower():
                data[eng] = value or ''
                break
    logger.debug("parse_template_format parsed fields: %s", list(data.keys()))
    return data


def contains_hebrew(text: str) -> bool:
    return any('\u0590' <= char <= '\u05FF' for char in text)


def contains_emoji(text: str) -> bool:
    """Проверяет наличие эмодзи"""
    return any(
        '\U0001F600' <= char <= '\U0001F64F' or  # Emoticons
        '\U0001F300' <= char <= '\U0001F5FF' or  # Misc Symbols
        '\U0001F680' <= char <= '\U0001F6FF' or  # Transport & Map
        '\U0001F1E0' <= char <= '\U0001F1FF' or  # Regional
        '\U00002600' <= char <= '\U000027BF' or  # Misc
        '\U0001F900' <= char <= '\U0001F9FF'
        for char in text
    )


def clean_text_from_confirmation_block(text: str) -> str:
    """Удаляет эмодзи и служебные слова из текста подтверждения"""
    cleaned = ''.join(ch for ch in text if not contains_emoji(ch))
    cleaned = cleaned.replace('**', '').replace('*', '')
    cleaned = cleaned.replace('🔍', '').replace('•', '')

    field_labels = [
        'Имя (рус)', 'Имя (англ)', 'Пол', 'Размер', 'Церковь',
        'Роль', 'Департамент', 'Город', 'Кто подал', 'Контакты'
    ]

    for label in field_labels:
        cleaned = re.sub(fr'{label}\s*:', '', cleaned, flags=re.IGNORECASE)

    cleaned = cleaned.replace(':', '')

    words = cleaned.split()
    filtered = []
    for word in words:
        w = word.strip('.,!?:;').upper()
        if (
            w not in CONFIRMATION_NOISE_WORDS and
            not w.startswith('➖') and
            not w.startswith('❌') and
            len(w) > 0
        ):
            filtered.append(word)

    return ' '.join(filtered)


def detect_field_update_intent(text: str) -> Optional[str]:
    """Определяет, какое поле хочет обновить пользователь"""
    text_upper = text.upper()
    words = re.split(r'\s+', text_upper)

    for field, indicators in FIELD_INDICATORS.items():
        for ind in indicators:
            if ind in words:
                return field

    if any(word in GENDER_KEYWORDS['F'] + GENDER_KEYWORDS['M'] for word in words):
        return 'Gender'

    if any(word in SIZES for word in words):
        return 'Size'

    return None


def parse_field_update(text: str, field_hint: str) -> Dict:
    """Парсит исправление конкретного поля"""
    text_clean = clean_text_from_confirmation_block(text)
    words = text_clean.split()
    update: Dict = {}

    if field_hint == 'Gender':
        for word in words:
            wu = word.upper()
            if wu in GENDER_KEYWORDS['F']:
                update['Gender'] = 'F'
                break
            if wu in GENDER_KEYWORDS['M']:
                update['Gender'] = 'M'
                break

    elif field_hint == 'Size':
        for word in words:
            wu = word.upper()
            if wu in SIZES:
                if wu == 'MEDIUM':
                    update['Size'] = 'M'
                elif wu == 'LARGE':
                    update['Size'] = 'L'
                elif wu == 'SMALL':
                    update['Size'] = 'S'
                else:
                    update['Size'] = wu
                break

    elif field_hint == 'Role':
        for word in words:
            wu = word.upper()
            if wu in ROLE_KEYWORDS['TEAM']:
                update['Role'] = 'TEAM'
                break
            if wu in ROLE_KEYWORDS['CANDIDATE']:
                update['Role'] = 'CANDIDATE'
                break

    elif field_hint == 'Department':
        for dept, keys in DEPARTMENT_KEYWORDS.items():
            for word in words:
                if word.upper() in keys:
                    update['Department'] = dept
                    break
            if 'Department' in update:
                break

    elif field_hint == 'Church':
        church_words = []
        for word in words:
            if not any(kw in word.upper() for kw in CHURCH_KEYWORDS) and not contains_hebrew(word):
                church_words.append(word)
        if church_words:
            update['Church'] = ' '.join(church_words)

    elif field_hint == 'CountryAndCity':
        for word in words:
            if word.upper() in ISRAEL_CITIES:
                update['CountryAndCity'] = word
                break

    return update


class ParticipantParser:
    def __init__(self):
        self.data: Dict = {}
        self.processed_words: set[str] = set()

    def parse(self, text: str, is_update: bool = False) -> Dict:
        """Основной метод парсинга."""
        text, early = self._preprocess_text(text, is_update)
        if early is not None:
            return early

        all_words = text.split()
        self.data = {
            'FullNameRU': '',
            'Gender': 'F',
            'Size': '',
            'Church': '',
            'Role': 'CANDIDATE',
            'Department': '',
            'FullNameEN': '',
            'SubmittedBy': '',
            'ContactInformation': '',
            'CountryAndCity': ''
        }
        self.processed_words = set()

        self._extract_all_fields(all_words, text)
        self._postprocess_data()

        logger.debug("ParticipantParser result: %s", self.data)
        return self.data

    def _preprocess_text(self, text: str, is_update: bool) -> tuple[str, Optional[Dict]]:
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
        self._extract_simple_fields(all_words)
        self._extract_church(all_words)
        self._extract_submitted_by(original_text)
        self._extract_names(all_words)

    def _postprocess_data(self):
        pass

    def _extract_submitted_by(self, text: str):
        """Извлекает информацию о том, кто подал заявку."""
        match = re.search(r'от\s+([А-ЯЁA-Z][А-Яа-яёA-Za-z\s]+)', text, re.IGNORECASE)
        if match:
            full_match = match.group(1).strip()
            words = full_match.split()

            valid_words = []
            for word in words:
                if word not in self.processed_words:
                    word_upper = word.upper()
                    if (
                        word_upper not in SIZES and
                        word_upper not in [k for keys in ROLE_KEYWORDS.values() for k in keys] and
                        word_upper not in [k for keys in DEPARTMENT_KEYWORDS.values() for k in keys]
                    ):
                        valid_words.append(word)
                    else:
                        break

            if valid_words:
                self.data['SubmittedBy'] = ' '.join(valid_words)
                for word in valid_words:
                    self.processed_words.add(word)
                self.processed_words.add('от')

    def _extract_contacts(self, all_words: list[str]):
        for word in all_words:
            if word in self.processed_words:
                continue

            if '@' in word and '.' in word.split('@')[-1]:
                if len(word) >= 5:
                    self.data['ContactInformation'] = word
                    self.processed_words.add(word)
                    break

            cleaned_phone = ''.join(c for c in word if c.isdigit() or c == '+')
            digit_count = sum(1 for c in cleaned_phone if c.isdigit())

            if digit_count >= 7:
                if (
                    word.startswith(('+', '8', '7')) or
                    digit_count >= 10 or
                    (digit_count >= 7 and any(char in word for char in ['-', '(', ')', ' ']))
                ):
                    self.data['ContactInformation'] = word
                    self.processed_words.add(word)
                    break

    def _extract_simple_fields(self, all_words: list[str]):
        """Извлекает простые поля с учетом приоритетов"""
        gender_explicit = False

        for word in all_words:
            if word in self.processed_words:
                continue
            wu = word.upper()
            if wu in GENDER_KEYWORDS['F']:
                self.data['Gender'] = 'F'
                gender_explicit = True
                self.processed_words.add(word)
                break

        for idx, word in enumerate(all_words):
            if word in self.processed_words:
                continue
            wu = word.upper()

            if wu in GENDER_KEYWORDS['M'] and not gender_explicit:
                if wu == 'M' and not self.data.get('Size'):
                    ctx = []
                    if idx > 0:
                        ctx.append(all_words[idx - 1].upper())
                    if idx < len(all_words) - 1:
                        ctx.append(all_words[idx + 1].upper())

                    if any('РАЗМЕР' in c or 'SIZE' in c for c in ctx):
                        self.data['Size'] = 'M'
                    else:
                        self.data['Gender'] = 'M'
                else:
                    self.data['Gender'] = 'M'
                self.processed_words.add(word)
                continue

            if wu in SIZES:
                if wu == 'MEDIUM':
                    self.data['Size'] = 'M'
                elif wu == 'LARGE':
                    self.data['Size'] = 'L'
                elif wu == 'SMALL':
                    self.data['Size'] = 'S'
                else:
                    self.data['Size'] = wu
                self.processed_words.add(word)

            elif any(keyword == wu for keyword in ROLE_KEYWORDS['TEAM']):
                self.data['Role'] = 'TEAM'
                self.processed_words.add(word)
            elif any(keyword == wu for keyword in ROLE_KEYWORDS['CANDIDATE']):
                self.data['Role'] = 'CANDIDATE'
                self.processed_words.add(word)
            elif not contains_hebrew(word):
                dept_found = False
                for dept, keywords in DEPARTMENT_KEYWORDS.items():
                    if any(keyword == wu for keyword in keywords):
                        self.data['Department'] = dept
                        self.processed_words.add(word)
                        dept_found = True
                        break

                if not dept_found and wu in ISRAEL_CITIES:
                    self.data['CountryAndCity'] = word
                    self.processed_words.add(word)

    def _extract_church(self, all_words: list[str]):
        for i, word in enumerate(all_words):
            if word in self.processed_words:
                continue
            word_upper = word.upper()
            if any(keyword in word_upper for keyword in CHURCH_KEYWORDS):
                church_words = []
                if (
                    i > 0 and
                    all_words[i - 1] not in self.processed_words and
                    not contains_hebrew(all_words[i - 1])
                ):
                    church_words.append(all_words[i - 1])
                    self.processed_words.add(all_words[i - 1])
                church_words.append(word)
                self.processed_words.add(word)
                if (
                    i < len(all_words) - 1 and
                    all_words[i + 1] not in self.processed_words and
                    not contains_hebrew(all_words[i + 1])
                ):
                    church_words.append(all_words[i + 1])
                    self.processed_words.add(all_words[i + 1])
                self.data['Church'] = ' '.join(church_words)
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
            self.data['FullNameRU'] = ' '.join(russian_words[:2])
        if english_words:
            self.data['FullNameEN'] = ' '.join(english_words[:2])


def parse_participant_data(text: str, is_update: bool = False) -> Dict:
    """Извлекает данные участника из произвольного текста."""
    parser = ParticipantParser()
    return parser.parse(text, is_update)
