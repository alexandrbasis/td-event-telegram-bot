from dataclasses import dataclass, field
from dataclasses import dataclass, field
from typing import Optional, Union

from domain.value_objects import Gender
from models.participant import Participant as LegacyParticipant


@dataclass
class Participant:
    """Новая доменная модель участника."""

    id: Optional[Union[int, str]] = field(default=None, compare=False)
    full_name_ru: str = ""
    gender: Gender = Gender.FEMALE
    size: str = ""
    church: str = ""
    role: str = ""
    department: str = ""
    full_name_en: str = ""
    submitted_by: str = ""
    contact_information: str = ""
    country_and_city: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "Participant":
        """Создает участника из словаря старого формата."""
        return cls(
            id=data.get("id"),
            full_name_ru=data.get("FullNameRU", ""),
            gender=Gender.from_string(data.get("Gender", "F")),
            size=data.get("Size", ""),
            church=data.get("Church", ""),
            role=data.get("Role", ""),
            department=data.get("Department", ""),
            full_name_en=data.get("FullNameEN", ""),
            submitted_by=data.get("SubmittedBy", ""),
            contact_information=data.get("ContactInformation", ""),
            country_and_city=data.get("CountryAndCity", ""),
        )

    @classmethod
    def from_legacy(cls, legacy: LegacyParticipant) -> "Participant":
        """Конвертер из старой модели."""
        return cls(
            id=legacy.id,
            full_name_ru=legacy.FullNameRU,
            gender=Gender.from_string(legacy.Gender),
            size=legacy.Size,
            church=legacy.Church,
            role=legacy.Role,
            department=legacy.Department,
            full_name_en=legacy.FullNameEN,
            submitted_by=legacy.SubmittedBy,
            contact_information=legacy.ContactInformation,
            country_and_city=legacy.CountryAndCity,
        )

    def to_legacy(self) -> LegacyParticipant:
        """Конвертер в старую модель."""
        return LegacyParticipant(
            id=self.id,
            FullNameRU=self.full_name_ru,
            Gender=self.gender.value,
            Size=self.size,
            Church=self.church,
            Role=self.role,
            Department=self.department,
            FullNameEN=self.full_name_en,
            SubmittedBy=self.submitted_by,
            ContactInformation=self.contact_information,
            CountryAndCity=self.country_and_city,
        )
