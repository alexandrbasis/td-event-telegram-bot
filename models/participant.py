from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Participant:
    # Required field without a default
    FullNameRU: str

    # Optional fields with defaults
    Gender: str = "F"
    Size: str = ""
    Church: str = ""
    Role: str = "CANDIDATE"
    Department: str = ""
    FullNameEN: str = ""
    SubmittedBy: str = ""
    ContactInformation: str = ""
    CountryAndCity: str = ""
    id: Optional[int] = field(default=None, compare=False)
