from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Participant:
    id: Optional[int] = field(default=None, compare=False)
    FullNameRU: str
    Gender: str = "F"
    Size: str = ""
    Church: str = ""
    Role: str = "CANDIDATE"
    Department: str = ""
    FullNameEN: str = ""
    SubmittedBy: str = ""
    ContactInformation: str = ""
    CountryAndCity: str = ""
