from enum import Enum, auto

class ConversationState(Enum):
    WAITING_FOR_PARTICIPANT = auto()
    CONFIRMING_PARTICIPANT = auto()
    CONFIRMING_DUPLICATE = auto()
