from dataclasses import dataclass
from typing import List


@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str]


class ParticipantValidator:
    """Новый валидатор, использующий старый как fallback"""

    def __init__(self, legacy_validator=None):
        self.legacy_validator = legacy_validator

    def validate(self, data: dict) -> ValidationResult:
        # Пока используем старую валидацию
        if self.legacy_validator:
            is_valid, error = self.legacy_validator(data)
            return ValidationResult(
                is_valid=is_valid,
                errors=[error] if error else [],
            )

        # Новая логика валидации будет добавлена позже
        return ValidationResult(is_valid=True, errors=[])
