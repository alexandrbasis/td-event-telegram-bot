import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2] / "src"))

from infrastructure.container import Container


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
