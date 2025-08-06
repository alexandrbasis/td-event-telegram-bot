from src.infrastructure.container import Container


def create_test_container():
    """Создает контейнер для тестов"""
    container = Container()
    container.config.from_dict(
        {
            "database": {"path": ":memory:"},
            "telegram": {"bot_token": "test_token"},
        }
    )
    return container
