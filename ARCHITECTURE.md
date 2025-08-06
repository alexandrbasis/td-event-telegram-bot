# Architecture

The bot follows a layered architecture:

- **Application**: use cases, controllers and workflows.
- **Domain**: entities, services and events.
- **Infrastructure**: adapters and dependency container.
- **Presentation**: handlers, UI components and middleware.

Use cases encapsulate business logic. Controllers coordinate user flows and rely on `UIFactory` to render responses. Middleware modules provide cross-cutting concerns such as authentication and logging.
