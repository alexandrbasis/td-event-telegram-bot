from typing import Dict
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
    'ROE': ['ROE', 'РОЕ', 'ROE ROOM', 'РОЕ РУМ', 'РОЭ', 'РОИ'],
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
SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL', '2XL', '3XL', 'М', 'Л', 'С']

ISRAEL_CITIES = [
    'ХАЙФА', 'HAIFA', 'ТЕЛ-АВИВ', 'TEL AVIV', 'ТЕЛЬ-АВИВ', 'ИЕРУСАЛИМ', 'JERUSALEM',
    'БЕЭР-ШЕВА', 'BEER SHEVA', 'НЕТАНИЯ', 'NETANYA', 'АШДОД', 'ASHDOD',
    'РИШОН-ЛЕ-ЦИОН', 'RISHON LEZION', 'ПЕТАХ-ТИКВА', 'PETAH TIKVA', 'РЕХОВОТ', 'REHOVOT',
    'БАТ-ЯМ', 'BAT YAM', 'КАРМИЭЛЬ', 'CARMIEL', 'МОДИИН', 'MODIIN', 'НАЗАРЕТ', 'NAZARETH',
    'КИРЬЯТ-ГАТ', 'KIRYAT GAT', 'ЭЙЛАТ', 'EILAT', 'АККО', 'ACRE', 'РАМАТ-ГАН', 'RAMAT GAN',
    'БНЕЙ-БРАК', 'BNEI BRAK', 'ЦФАТ', 'SAFED', 'ТВЕРИЯ', 'TIBERIAS', 'ГЕРЦЛИЯ', 'HERZLIYA',
    'АФУЛА', 'AFULA'
]


def contains_hebrew(text: str) -> bool:
    return any('\u0590' <= char <= '\u05FF' for char in text)


def _extract_submitted_by(text: str, processed_words: set, data: Dict):
    match = re.search(r'от\s+([А-ЯЁA-Z][А-Яа-яёA-Za-z\s]+?)(?:\s*\+|\s*$)', text, re.IGNORECASE)
    if match:
        data['SubmittedBy'] = match.group(1).strip()
        for word in match.group(0).split():
            processed_words.add(word)


def _extract_contacts(all_words: list, processed_words: set, data: Dict):
    for word in all_words:
        if word in processed_words:
            continue
        if ('@' in word or
            (word.startswith(('+', '8', '7')) and len(word) > 5) or
            (word.replace('+', '').replace('-', '').replace('(', '').replace(')', '').replace(' ', '').isdigit() and len(word) > 7)):
            data['ContactInformation'] = word
            processed_words.add(word)
            break


def _extract_simple_fields(all_words: list, processed_words: set, data: Dict):
    gender_explicit = False
    for word in all_words:
        if word in processed_words:
            continue
        word_upper = word.upper()

        if word_upper in GENDER_KEYWORDS['F']:
            data['Gender'] = 'F'
            gender_explicit = True
            processed_words.add(word)
            continue

        if word_upper in GENDER_KEYWORDS['M']:
            if gender_explicit and data['Gender'] == 'F' and word_upper in SIZES:
                data['Size'] = word_upper
            else:
                data['Gender'] = 'M'
                gender_explicit = True
            processed_words.add(word)
            continue

        if word_upper in SIZES:
            data['Size'] = word_upper
            processed_words.add(word)
        elif any(keyword == word_upper for keyword in ROLE_KEYWORDS['TEAM']):
            data['Role'] = 'TEAM'
            processed_words.add(word)
        elif any(keyword == word_upper for keyword in ROLE_KEYWORDS['CANDIDATE']):
            data['Role'] = 'CANDIDATE'
            processed_words.add(word)
        elif not contains_hebrew(word):
            dept_found = False
            for dept, keywords in DEPARTMENT_KEYWORDS.items():
                if any(keyword == word_upper for keyword in keywords):
                    data['Department'] = dept
                    processed_words.add(word)
                    dept_found = True
                    break
            if not dept_found and word_upper in ISRAEL_CITIES:
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


def parse_participant_data(text: str) -> Dict:
    """Извлекает данные участника из произвольного текста."""
    text = text.strip()
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

    _extract_submitted_by(text, processed_words, data)
    _extract_contacts(all_words, processed_words, data)
    _extract_simple_fields(all_words, processed_words, data)
    _extract_church(all_words, processed_words, data)
    _extract_names(all_words, processed_words, data)

    return data
