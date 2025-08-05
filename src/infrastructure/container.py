import logging
from dependency_injector import containers, providers


class Container(containers.DeclarativeContainer):
    # Start with basic dependencies
    config = providers.Configuration()
    logger = providers.Singleton(logging.getLogger, "bot")
    user_logger = providers.Singleton("utils.user_logger.UserActionLogger")

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

    duplicate_checker = providers.Factory(
        "domain.services.duplicate_checker.DuplicateCheckerService",
        repository=participant_repository,
    )

    event_dispatcher = providers.Singleton("shared.event_dispatcher.EventDispatcher")

    # Use Cases
    add_participant_use_case = providers.Factory(
        "application.use_cases.add_participant.AddParticipantUseCase",
        repository=participant_repository,
        validator=participant_validator,
        duplicate_checker=duplicate_checker,
        event_dispatcher=event_dispatcher,
    )

    search_participants_use_case = providers.Factory(
        "application.use_cases.search_participant.SearchParticipantsUseCase",
        participant_service=legacy_participant_service,
    )

    list_participants_use_case = providers.Factory(
        "application.use_cases.list_participants.ListParticipantsUseCase",
        participant_service=legacy_participant_service,
    )

    get_participant_use_case = providers.Factory(
        "application.use_cases.get_participant.GetParticipantUseCase",
        participant_service=legacy_participant_service,
    )

    update_participant_use_case = providers.Factory(
        "application.use_cases.update_participant.UpdateParticipantUseCase",
        repository=participant_repository,
        validator=participant_validator,
        duplicate_checker=duplicate_checker,
        event_dispatcher=event_dispatcher,
    )

    delete_participant_use_case = providers.Factory(
        "application.use_cases.delete_participant.DeleteParticipantUseCase",
        participant_service=legacy_participant_service,
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
    add_handler = providers.Factory(
        "presentation.handlers.command_handlers.AddCommandHandler",
        container=providers.Self(),
    )
    help_handler = providers.Factory(
        "presentation.handlers.command_handlers.HelpCommandHandler",
        container=providers.Self(),
    )
    list_handler = providers.Factory(
        "presentation.handlers.command_handlers.ListCommandHandler",
        container=providers.Self(),
    )
    search_handler = providers.Factory(
        "presentation.handlers.command_handlers.SearchCommandHandler",
        container=providers.Self(),
    )
    cancel_handler = providers.Factory(
        "presentation.handlers.command_handlers.CancelCommandHandler",
        container=providers.Self(),
    )

    add_callback_handler = providers.Factory(
        "presentation.handlers.callback_handlers.AddCallbackHandler",
        container=providers.Self(),
    )
    search_callback_handler = providers.Factory(
        "presentation.handlers.callback_handlers.SearchCallbackHandler",
        container=providers.Self(),
    )
    main_menu_callback_handler = providers.Factory(
        "presentation.handlers.callback_handlers.MainMenuCallbackHandler",
        container=providers.Self(),
    )
    save_confirmation_callback_handler = providers.Factory(
        "presentation.handlers.callback_handlers.SaveConfirmationCallbackHandler",
        container=providers.Self(),
    )
    duplicate_callback_handler = providers.Factory(
        "presentation.handlers.callback_handlers.DuplicateCallbackHandler",
        container=providers.Self(),
    )
