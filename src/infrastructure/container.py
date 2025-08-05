from dependency_injector import containers, providers


class Container(containers.DeclarativeContainer):
    # Start with basic dependencies
    config = providers.Configuration()

    # Keep existing components working
    legacy_participant_service = providers.Singleton(
        'services.participant_service.ParticipantService',
        repository=providers.Singleton('repositories.participant_repository.SqliteParticipantRepository')
    )
