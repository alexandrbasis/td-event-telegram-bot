from typing import Dict

VALID_SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL', '2XL', '3XL']

def validate_size(size: str) -> bool:
    return size.upper() in VALID_SIZES


def validate_participant_data(data: Dict) -> (bool, str):
    if data.get('Size') and not validate_size(data['Size']):
        return False, 'Недопустимый размер одежды'
    if data.get('Role') == 'TEAM' and not data.get('Department'):
        return False, 'Для роли TEAM необходимо указать департамент'
    return True, ''
