from enum import Enum
from dataclasses import dataclass


class Gender(Enum):
    MALE = "M"
    FEMALE = "F"

    @classmethod
    def from_string(cls, value: str) -> "Gender":
        """Совместимость со старым кодом"""
        if value in ("M", "муж", "мужской", "male"):
            return cls.MALE
        return cls.FEMALE
