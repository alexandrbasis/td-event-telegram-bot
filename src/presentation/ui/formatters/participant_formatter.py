from dataclasses import asdict

from domain.models.participant import Participant


def format_participant(participant: Participant) -> str:
    data = asdict(participant)
    return f"{data.get('FullNameRU')} ({data.get('Role')})"
