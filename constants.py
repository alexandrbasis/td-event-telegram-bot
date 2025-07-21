from enum import Enum

class Gender(Enum):
    MALE = 'M'
    FEMALE = 'F'

class Role(Enum):
    CANDIDATE = 'CANDIDATE'
    TEAM = 'TEAM'

GENDER_KEYWORDS = {
    Gender.MALE.value: ['M', 'МУЖ', 'МУЖСКОЙ', 'MALE', 'М', 'МУЖЧИНА'],
    Gender.FEMALE.value: ['F', 'ЖЕН', 'ЖЕНСКИЙ', 'FEMALE', 'Ж', 'ЖЕНЩИНА']
}

ROLE_KEYWORDS = {
    Role.TEAM.value: ['TEAM', 'КОМАНДА', 'ТИМ', 'TIM', 'TEAM MEMBER', 'ЧЛЕН КОМАНДЫ', 'КОМАНДНЫЙ', 'СЛУЖИТЕЛЬ'],
    Role.CANDIDATE.value: ['CANDIDATE', 'КАНДИДАТ', 'УЧАСТНИК', 'КАНДИДАТКА']
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
    'Decoration': ['DECORATION', 'ДЕКОРАЦИИ', 'ДЕКОР', 'DECO', 'DECOR', 'УКРАШЕНИЕ', 'ОФОРМЛЕНИЕ'],
    'Bell': ['BELL', 'ЗВОНАРЬ', 'БЕЛЛ', 'ЗВОН', 'КОЛОКОЛЬЧИК'],
    'Refreshment': ['REFRESHMENT', 'РЕФРЕШМЕНТ', 'УГОЩЕНИЯ', 'НАПИТКИ'],
    'Worship': ['WORSHIP', 'ПРОСЛАВЛЕНИЕ', 'ВОРШИП', 'МУЗЫКА', 'MUSIC'],
    'Media': ['MEDIA', 'МЕДИА', 'ВИДЕО', 'ФОТО', 'СЪЕМКА', 'КАМЕРА', 'ФОТОГРАФ'],
    'Духовенство': ['ДУХОВЕНСТВО', 'CLERGY', 'СВЯЩЕННИКИ'],
    'Ректорат': ['РЕКТОРАТ', 'RECTOR', 'РЕКТОРЫ']
}

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
