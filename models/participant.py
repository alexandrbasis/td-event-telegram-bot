from dataclasses import dataclass, field
from typing import Optional, Union


@dataclass
class Participant:
    # Required field without a default
    FullNameRU: str

    # Optional fields with defaults
    Gender: str = "F"
    Size: str = ""
    Church: str = ""
    Role: str = ""
    Department: str = ""
    FullNameEN: str = ""
    SubmittedBy: str = ""
    ContactInformation: str = ""
    CountryAndCity: str = ""
    
    # Payment fields - added for TDB-1
    PaymentStatus: str = "Unpaid"
    PaymentAmount: int = 0  # Amount in shekels (integers only)
    PaymentDate: str = ""   # ISO format date string
    
    id: Optional[Union[int, str]] = field(default=None, compare=False)
