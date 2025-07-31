class BotException(Exception):
    """Base exception for bot errors"""
    pass


class ParticipantNotFoundError(BotException):
    """Raised when a participant could not be found"""
    pass


class DuplicateParticipantError(BotException):
    """Raised when attempting to create a duplicate participant"""
    pass


class ValidationError(BotException):
    """Raised when validation of data fails"""
    pass


class DatabaseError(BotException):
    """Related to database errors."""
    pass
