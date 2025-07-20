from dataclasses import dataclass

@dataclass
class Participant:
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
