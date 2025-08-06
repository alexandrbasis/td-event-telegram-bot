import os

# Ensure AirtableClient initializes without env errors
os.environ.setdefault("AIRTABLE_TOKEN", "test_token")
os.environ.setdefault("AIRTABLE_BASE_ID", "base123")

from tests.fixtures.container import create_test_container
from src.domain.services.participant_validator import ParticipantValidator
from src.domain.services.duplicate_checker import DuplicateCheckerService
from src.shared.event_dispatcher import EventDispatcher
from src.application.use_cases.add_participant import AddParticipantUseCase
from src.repositories.airtable_participant_repository import AirtableParticipantRepository
from src.domain.events.participant_events import (
    ParticipantAddedEvent,
    ParticipantUpdatedEvent,
)


def test_participant_validator_provider():
    container = create_test_container()
    validator = container.participant_validator()
    assert isinstance(validator, ParticipantValidator)
    assert callable(validator.legacy_validator)


def test_duplicate_checker_provider():
    container = create_test_container()
    checker = container.duplicate_checker()
    assert isinstance(checker, DuplicateCheckerService)
    assert isinstance(checker.repository, AirtableParticipantRepository)


def test_event_dispatcher_provider_and_wiring():
    container = create_test_container()
    dispatcher = container.event_dispatcher()
    container.configure_events()
    assert isinstance(dispatcher, EventDispatcher)
    assert ParticipantAddedEvent in dispatcher._listeners
    assert ParticipantUpdatedEvent in dispatcher._listeners


def test_add_participant_use_case_provider():
    container = create_test_container()
    use_case = container.add_participant_use_case()
    assert isinstance(use_case, AddParticipantUseCase)
    assert isinstance(use_case.validator, ParticipantValidator)
    assert isinstance(use_case.duplicate_checker, DuplicateCheckerService)
    assert isinstance(use_case.event_dispatcher, EventDispatcher)
    assert isinstance(
        use_case.duplicate_checker.repository, AirtableParticipantRepository
    )


def test_container_wiring():
    from src.infrastructure.container import Container

    container = Container()
    container.check_dependencies()
