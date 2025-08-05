import logging
from dependency_injector import containers, providers


class Container(containers.DeclarativeContainer):
    # Start with basic dependencies
    config = providers.Configuration()
    logger = providers.Singleton(logging.getLogger, "bot")

    # Keep existing components working
    legacy_participant_service = providers.Singleton(
        "services.participant_service.ParticipantService",
        repository=providers.Singleton(
            "repositories.participant_repository.SqliteParticipantRepository"
        ),
    )

    # Domain Services
    participant_validator = providers.Factory(
        "domain.services.participant_validator.ParticipantValidator",
        legacy_validator=providers.Callable(
            "utils.validators.validate_participant_data"
        ),
    )

    # Repositories
    participant_repository = providers.Factory(
        "infrastructure.repositories.participant_repository_adapter.ParticipantRepositoryAdapter",
        legacy_repository=providers.Factory(
            "repositories.participant_repository.SqliteParticipantRepository"
        ),
    )

    # Use Cases
    add_participant_use_case = providers.Factory(
        "application.use_cases.add_participant.AddParticipantUseCase",
        repository=participant_repository,
        validator=participant_validator,
    )

    # Controllers
    participant_controller = providers.Factory(
        "application.controllers.participant_controller.ParticipantController",
        add_use_case=add_participant_use_case,
    )

    # Handlers
    start_handler = providers.Factory(
        "presentation.handlers.command_handlers.StartCommandHandler",
        container=providers.Self(),
    )
