from typing import Dict
from messages import MESSAGES

VALID_SIZES = [
    'XS', 'EXTRA SMALL', 'EXTRASMALL',
    'S', 'SMALL',
    'M', 'MEDIUM',
    'L', 'LARGE',
    'XL', 'EXTRA LARGE', 'EXTRALARGE',
    'XXL', '2XL', 'EXTRA EXTRA LARGE',
    '3XL', 'XXXL'
]

def validate_size(size: str) -> bool:
    return size.upper() in [s.upper() for s in VALID_SIZES]


def validate_participant_data(data: Dict) -> (bool, str):
    if not data.get('FullNameRU'):
        return False, MESSAGES['VALIDATION_ERRORS']['FullNameRU']

    if data.get('Gender') not in ('M', 'F'):
        return False, MESSAGES['VALIDATION_ERRORS']['Gender']

    if not data.get('Church'):
        return False, MESSAGES['VALIDATION_ERRORS']['Church']

    if not data.get('Role'):
        return False, MESSAGES['VALIDATION_ERRORS']['Role']

    if data.get('Role') == 'TEAM' and not data.get('Department'):
        return False, MESSAGES['VALIDATION_ERRORS']['Department']

    if data.get('Size') and not validate_size(data['Size']):
        return False, MESSAGES['VALIDATION_ERRORS']['Size']

    return True, ''
