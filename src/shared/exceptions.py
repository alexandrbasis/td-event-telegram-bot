class DomainError(Exception):
    """Базовое доменное исключение"""
    pass


class ValidationError(DomainError):
    def __init__(self, errors):
        if isinstance(errors, str):
            errors = [errors]
        self.errors = errors
        super().__init__(f"Validation failed: {', '.join(errors)}")


class BotException(DomainError):
    """Base exception for bot errors"""
    pass


class ParticipantNotFoundError(BotException):
    """Raised when a participant could not be found"""
    pass


class DuplicateParticipantError(BotException):
    """Raised when attempting to create a duplicate participant"""
    pass


class DatabaseError(BotException):
    """Related to database errors."""
    pass
