from typing import Dict, Optional
import re

GENDER_KEYWORDS = {
    'M': ['M', 'МУЖ', 'МУЖСКОЙ', 'MALE', 'М', 'МУЖЧИНА'],
    'F': ['F', 'ЖЕН', 'ЖЕНСКИЙ', 'FEMALE', 'Ж', 'ЖЕНЩИНА']
}

ROLE_KEYWORDS = {
    'TEAM': ['TEAM', 'КОМАНДА', 'ТИМ', 'TIM', 'TEAM MEMBER', 'ЧЛЕН КОМАНДЫ', 'КОМАНДНЫЙ', 'СЛУЖИТЕЛЬ'],
    'CANDIDATE': ['CANDIDATE', 'КАНДИДАТ', 'УЧАСТНИК', 'КАНДИДАТКА']
}

DEPARTMENT_KEYWORDS = {
    'ROE': [
        'ROE', 'РОЕ', 'ROE ROOM', 'РОЕ РУМ', 'РОЭ', 'РОИ',
        'roe', 'рое', 'roe room', 'рое рум', 'роэ'
    ],
    'Chapel': ['CHAPEL', 'МОЛИТВЕННЫЙ', 'МОЛИТВА', 'PRAYER', 'ЧАСОВНЯ'],
    'Setup': ['SETUP', 'СЕТАП', 'НАСТРОЙКА', 'ПОДГОТОВКА', 'СЕТ АП'],
    'Palanka': ['PALANKA', 'ПАЛАНКА', 'ПОЛАНКА'],
    'Administration': ['ADMINISTRATION', 'АДМИНИСТРАЦИЯ', 'АДМИН', 'ADMIN', 'УПРАВЛЕНИЕ'],
    'Kitchen': ['KITCHEN', 'КУХНЯ', 'КИТЧЕН', 'КУЛИНАРИЯ', 'ПОВАРА'],
    'Decoration': ['DECORATION', 'ДЕКОРАЦИИ', 'ДЕКОР', 'DECO', 'DECOR', 'УКРАШЕНИЯ', 'ОФОРМЛЕНИЕ'],
    'Bell': ['BELL', 'ЗВОНАРЬ', 'БЕЛЛ', 'ЗВОН', 'КОЛОКОЛЬЧИК'],
    'Refreshment': ['REFRESHMENT', 'РЕФРЕШМЕНТ', 'УГОЩЕНИЯ', 'НАПИТКИ'],
    'Worship': ['WORSHIP', 'ПРОСЛАВЛЕНИЕ', 'ВОРШИП', 'МУЗЫКА', 'MUSIC'],
    'Media': ['MEDIA', 'МЕДИА', 'ВИДЕО', 'ФОТО', 'СЪЕМКА', 'КАМЕРА', 'ФОТОГРАФ'],
    'Духовенство': ['ДУХОВЕНСТВО', 'CLERGY', 'СВЯЩЕННИКИ'],
    'Ректорат': ['РЕКТОРАТ', 'RECTOR', 'РЕКТОРЫ']
}

CHURCH_KEYWORDS = ['ЦЕРКОВЬ', 'CHURCH', 'ХРАМ', 'ОБЩИНА']
SIZES = [
    'XS', 'EXTRA SMALL', 'EXTRASMALL',
    'S', 'SMALL',
    'M', 'MEDIUM',
    'L', 'LARGE',
    'XL', 'EXTRA LARGE', 'EXTRALARGE',
    'XXL', '2XL', 'EXTRA EXTRA LARGE',
    '3XL', 'XXXL'
]

ISRAEL_CITIES = [
    'ХАЙФА', 'HAIFA', 'ТЕЛ-АВИВ', 'TEL AVIV', 'ТЕЛЬ-АВИВ', 'ИЕРУСАЛИМ', 'JERUSALEM',
    'БЕЭР-ШЕВА', 'BEER SHEVA', 'НЕТАНИЯ', 'NETANYA', 'АШДОД', 'ASHDOD',
    'РИШОН-ЛЕ-ЦИОН', 'РИШОН ЛЕ ЦИОН', 'РИШОН-ЛЕ ЦИОН', 'РИШОН ЛЕЦИОН',
    'RISHON LEZION', 'RISHON-LEZION', 'RISHON LE ZION', 'RISHON-LE ZION',
    'ПЕТАХ-ТИКВА', 'PETAH TIKVA', 'РЕХОВОТ', 'REHOVOT',
    'БАТ-ЯМ', 'BAT YAM', 'КАРМИЭЛЬ', 'CARMIEL', 'МОДИИН', 'MODIIN', 'НАЗАРЕТ', 'NAZARETH',
    'КИРЬЯТ-ГАТ', 'KIRYAT GAT', 'ЭЙЛАТ', 'EILAT', 'АККО', 'ACRE', 'РАМАТ-ГАН', 'RAMAT GAN',
    'БНЕЙ-БРАК', 'BNEI BRAK', 'ЦФАТ', 'SAFED', 'ТВЕРИЯ', 'TIBERIAS', 'ГЕРЦЛИЯ', 'HERZLIYA',
    'АФУЛА', 'AFULA'
]

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
    return count >= 3


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
        if not value:
            continue
        for ru, eng in TEMPLATE_FIELD_MAP.items():
            if key.lower() == ru.lower():
                data[eng] = value
                break
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


def _extract_submitted_by(text: str, processed_words: set, data: Dict):
    # Ищем паттерн "от Имя Фамилия", но останавливаемся на уже обработанных словах
    match = re.search(r'от\s+([А-ЯЁA-Z][А-Яа-яёA-Za-z\s]+)', text, re.IGNORECASE)
    if match:
        full_match = match.group(1).strip()
        words = full_match.split()
        
        # Берем только те слова, которые еще не были обработаны
        valid_words = []
        for word in words:
            if word not in processed_words:
                # Проверяем, что это не ключевое слово размера/роли/департамента
                word_upper = word.upper()
                if (word_upper not in SIZES and 
                    word_upper not in [k for keys in ROLE_KEYWORDS.values() for k in keys] and
                    word_upper not in [k for keys in DEPARTMENT_KEYWORDS.values() for k in keys]):
                    valid_words.append(word)
                else:
                    break  # Останавливаемся на первом ключевом слове
        
        if valid_words:
            data['SubmittedBy'] = ' '.join(valid_words)
            # Добавляем в processed_words только валидные слова
            for word in valid_words:
                processed_words.add(word)
            processed_words.add('от')  # Добавляем предлог


def _extract_contacts(all_words: list, processed_words: set, data: Dict):
    for word in all_words:
        if word in processed_words:
            continue

        # Проверка email
        if '@' in word and '.' in word.split('@')[-1]:
            # Простая проверка: есть @ и точка после @
            if len(word) >= 5:  # минимальная длина email
                data['ContactInformation'] = word
                processed_words.add(word)
                break

        # Проверка телефона
        # Очищаем от всех не-цифровых символов кроме +
        cleaned_phone = ''.join(c for c in word if c.isdigit() or c == '+')

        # Считаем количество цифр
        digit_count = sum(1 for c in cleaned_phone if c.isdigit())

        # Телефон должен содержать минимум 7 цифр
        if digit_count >= 7:
            # Проверяем что это похоже на телефон
            if (
                word.startswith(('+', '8', '7')) or
                digit_count >= 10 or  # международный формат
                (digit_count >= 7 and any(char in word for char in ['-', '(', ')', ' ']))
            ):
                data['ContactInformation'] = word
                processed_words.add(word)
                break


def _extract_simple_fields(all_words: list, processed_words: set, data: Dict):
    """Извлекает простые поля с учетом приоритетов"""
    gender_explicit = False

    # Сначала ищем явное указание на женский пол
    for word in all_words:
        if word in processed_words:
            continue
        wu = word.upper()

        if wu in GENDER_KEYWORDS['F']:
            data['Gender'] = 'F'
            gender_explicit = True
            processed_words.add(word)
            break

    # Затем обрабатываем оставшиеся слова
    for idx, word in enumerate(all_words):
        if word in processed_words:
            continue
        wu = word.upper()

        if wu in GENDER_KEYWORDS['M'] and not gender_explicit:
            if wu == 'M' and not data.get('Size'):
                ctx = []
                if idx > 0:
                    ctx.append(all_words[idx - 1].upper())
                if idx < len(all_words) - 1:
                    ctx.append(all_words[idx + 1].upper())

                if any('РАЗМЕР' in c or 'SIZE' in c for c in ctx):
                    data['Size'] = 'M'
                else:
                    data['Gender'] = 'M'
            else:
                data['Gender'] = 'M'
            processed_words.add(word)
            continue

        if wu in SIZES:
            if wu == 'MEDIUM':
                data['Size'] = 'M'
            elif wu == 'LARGE':
                data['Size'] = 'L'
            elif wu == 'SMALL':
                data['Size'] = 'S'
            else:
                data['Size'] = wu
            processed_words.add(word)

        elif any(keyword == wu for keyword in ROLE_KEYWORDS['TEAM']):
            data['Role'] = 'TEAM'
            processed_words.add(word)
        elif any(keyword == wu for keyword in ROLE_KEYWORDS['CANDIDATE']):
            data['Role'] = 'CANDIDATE'
            processed_words.add(word)
        elif not contains_hebrew(word):
            dept_found = False
            for dept, keywords in DEPARTMENT_KEYWORDS.items():
                if any(keyword == wu for keyword in keywords):
                    data['Department'] = dept
                    processed_words.add(word)
                    dept_found = True
                    break

            if not dept_found and wu in ISRAEL_CITIES:
                data['CountryAndCity'] = word
                processed_words.add(word)


def _extract_church(all_words: list, processed_words: set, data: Dict):
    for i, word in enumerate(all_words):
        if word in processed_words:
            continue
        word_upper = word.upper()
        if any(keyword in word_upper for keyword in CHURCH_KEYWORDS):
            church_words = []
            if (i > 0 and all_words[i-1] not in processed_words and not contains_hebrew(all_words[i-1])):
                church_words.append(all_words[i-1])
                processed_words.add(all_words[i-1])
            church_words.append(word)
            processed_words.add(word)
            if (i < len(all_words) - 1 and all_words[i+1] not in processed_words and not contains_hebrew(all_words[i+1])):
                church_words.append(all_words[i+1])
                processed_words.add(all_words[i+1])
            data['Church'] = ' '.join(church_words)
            break


def _extract_names(all_words: list, processed_words: set, data: Dict):
    unprocessed = [w for w in all_words if w not in processed_words]
    russian_words = []
    english_words = []
    for word in unprocessed:
        if word.isalpha() and all(ord(c) < 128 for c in word):
            english_words.append(word)
        else:
            russian_words.append(word)
    if russian_words:
        data['FullNameRU'] = ' '.join(russian_words[:2])
    if english_words:
        data['FullNameEN'] = ' '.join(english_words[:2])


def parse_participant_data(text: str, is_update: bool = False) -> Dict:
    """Извлекает данные участника из произвольного текста."""
    text = text.strip()

    if is_template_format(text):
        return parse_template_format(text)

    if is_update:
        text = clean_text_from_confirmation_block(text)
        field_hint = detect_field_update_intent(text)
        if field_hint:
            return parse_field_update(text, field_hint)

    all_words = text.split()

    data = {
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

    processed_words: set = set()

    _extract_contacts(all_words, processed_words, data)
    _extract_simple_fields(all_words, processed_words, data)
    _extract_church(all_words, processed_words, data)
    _extract_submitted_by(text, processed_words, data)
    _extract_names(all_words, processed_words, data)

    return data
