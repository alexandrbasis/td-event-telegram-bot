from legacy_main import (
    _add_message_to_cleanup,
    _cleanup_messages,
    _show_main_menu,
    _send_response_with_menu_button,
    _show_search_prompt,
    _log_session_end,
)
from legacy_main import *  # noqa: F401,F403
from infrastructure.container import Container


def main() -> None:
    container = Container()
    container.configure_events()
    application, container = create_application(container)
    application.run_polling()


if __name__ == "__main__":
    main()
