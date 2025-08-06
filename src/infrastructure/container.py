import logging
from dependency_injector import containers, providers


class Container(containers.DeclarativeContainer):
    # Start with basic dependencies
    config = providers.Configuration()
    logger = providers.Singleton(logging.getLogger, "bot")
    user_logger = providers.Singleton("src.utils.user_logger.UserActionLogger")

    # Keep existing components working
    legacy_participant_service = providers.Singleton(
        "src.services.participant_service.ParticipantService",
        repository=providers.Singleton(
            "src.repositories.airtable_participant_repository.AirtableParticipantRepository"  # ✅ Используем Airtable
        ),
    )

    # ✅ Domain Services
    participant_validator = providers.Factory(
        "src.domain.services.participant_validator.ParticipantValidator",
        legacy_validator=providers.Callable(
            "src.utils.validators.validate_participant_data"
        ),
    )

    # Repositories
    participant_repository = providers.Factory(
        "src.repositories.airtable_participant_repository.AirtableParticipantRepository"
    )

    # ✅ Duplicate checker and dispatcher
    duplicate_checker = providers.Factory(
        "src.domain.services.duplicate_checker.DuplicateCheckerService",
        repository=participant_repository,
    )

    event_dispatcher = providers.Singleton(
        "src.shared.event_dispatcher.EventDispatcher"
    )

    # Event Listeners
    participant_event_listener = providers.Factory(
        "src.application.event_handlers.participant_event_listener.ParticipantEventListener",
        logger=providers.Callable("logging.getLogger", "participant_events"),
    )

    # ✅ Use Cases
    add_participant_use_case = providers.Factory(
        "src.application.use_cases.add_participant.AddParticipantUseCase",
        repository=participant_repository,
        validator=participant_validator,
        duplicate_checker=duplicate_checker,
        event_dispatcher=event_dispatcher,
    )

    search_participants_use_case = providers.Factory(
        "src.application.use_cases.search_participant.SearchParticipantsUseCase",
        participant_service=legacy_participant_service,
    )

    list_participants_use_case = providers.Factory(
        "src.application.use_cases.list_participants.ListParticipantsUseCase",
        participant_service=legacy_participant_service,
    )

    get_participant_use_case = providers.Factory(
        "src.application.use_cases.get_participant.GetParticipantUseCase",
        participant_service=legacy_participant_service,
    )

    update_participant_use_case = providers.Factory(
        "src.application.use_cases.update_participant.UpdateParticipantUseCase",
        repository=participant_repository,
        validator=participant_validator,
        duplicate_checker=duplicate_checker,
        event_dispatcher=event_dispatcher,
    )

    delete_participant_use_case = providers.Factory(
        "src.application.use_cases.delete_participant.DeleteParticipantUseCase",
        participant_service=legacy_participant_service,
    )

    # UI Factory
    ui_factory = providers.Factory("src.presentation.ui.factory.UIFactory")

    # UI Services
    message_service = providers.Factory(
        "src.presentation.services.message_service.MessageService"
    )
    ui_service = providers.Factory(
        "src.presentation.services.ui_service.UIService",
        message_service=message_service,
    )

    # Controllers
    participant_controller = providers.Factory(
        "src.application.controllers.participant_controller.ParticipantController",
        container=providers.Self(),
    )

    # Handlers
    start_handler = providers.Factory(
        "src.presentation.handlers.command_handlers.StartCommandHandler",
        container=providers.Self(),
        ui_service=ui_service,
        message_service=message_service,
    )
    add_handler = providers.Factory(
        "src.presentation.handlers.command_handlers.AddCommandHandler",
        container=providers.Self(),
        message_service=message_service,
    )
    update_handler = providers.Factory(
        "src.presentation.handlers.command_handlers.UpdateParticipantHandler",
        container=providers.Self(),
        update_use_case=update_participant_use_case,
    )
    help_handler = providers.Factory(
        "src.presentation.handlers.command_handlers.HelpCommandHandler",
        container=providers.Self(),
        message_service=message_service,
    )
    list_handler = providers.Factory(
        "src.presentation.handlers.command_handlers.ListCommandHandler",
        container=providers.Self(),
        list_use_case=list_participants_use_case,
        ui_factory=ui_factory,
    )
    search_handler = providers.Factory(
        "src.presentation.handlers.command_handlers.SearchCommandHandler",
        container=providers.Self(),
        search_use_case=search_participants_use_case,
        ui_service=ui_service,
        message_service=message_service,
    )
    cancel_handler = providers.Factory(
        "src.presentation.handlers.command_handlers.CancelCommandHandler",
        container=providers.Self(),
        ui_service=ui_service,
    )

    add_callback_handler = providers.Factory(
        "src.presentation.handlers.callback_handlers.AddCallbackHandler",
        container=providers.Self(),
        message_service=message_service,
    )
    search_callback_handler = providers.Factory(
        "src.presentation.handlers.callback_handlers.SearchCallbackHandler",
        container=providers.Self(),
        search_use_case=search_participants_use_case,
        ui_service=ui_service,
    )
    main_menu_callback_handler = providers.Factory(
        "src.presentation.handlers.callback_handlers.MainMenuCallbackHandler",
        container=providers.Self(),
        ui_service=ui_service,
        message_service=message_service,
    )
    save_confirmation_callback_handler = providers.Factory(
        "src.presentation.handlers.callback_handlers.SaveConfirmationCallbackHandler",
        container=providers.Self(),
        ui_service=ui_service,
        add_use_case=add_participant_use_case,
        update_use_case=update_participant_use_case,
        search_use_case=search_participants_use_case,
        get_use_case=get_participant_use_case,
    )
    duplicate_callback_handler = providers.Factory(
        "src.presentation.handlers.callback_handlers.DuplicateCallbackHandler",
        container=providers.Self(),
    )

    def configure_events(self):
        """Configure event subscriptions"""
        dispatcher = self.event_dispatcher()
        listener = self.participant_event_listener()

        from src.domain.events.participant_events import (
            ParticipantAddedEvent,
            ParticipantUpdatedEvent,
        )

        dispatcher.subscribe(ParticipantAddedEvent, listener.on_participant_added)
        dispatcher.subscribe(
            ParticipantUpdatedEvent, listener.on_participant_updated
        )
