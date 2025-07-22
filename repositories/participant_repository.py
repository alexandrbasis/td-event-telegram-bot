from abc import ABC, abstractmethod
from typing import List, Dict, Optional

# Используем dataclass из models, чтобы работать с объектами, а не словарями
from models.participant import Participant


class AbstractParticipantRepository(ABC):
    """Абстрактный класс (контракт) для работы с хранилищем участников."""

    @abstractmethod
    def add(self, participant: Participant) -> int:
        """Добавляет участника и возвращает его ID."""
        pass

    @abstractmethod
    def get_by_id(self, participant_id: int) -> Optional[Participant]:
        """Находит участника по ID."""
        pass

    @abstractmethod
    def get_by_name(self, full_name_ru: str) -> Optional[Participant]:
        """Находит участника по полному имени."""
        pass

    @abstractmethod
    def get_all(self) -> List[Participant]:
        """Возвращает всех участников."""
        pass

    @abstractmethod
    def update(self, participant_id: int, data: Dict) -> bool:
        """Обновляет данные участника."""
        # Примечание: в идеале здесь тоже нужно принимать объект Participant,
        # но для упрощения пока оставим Dict, как в исходном коде.
        pass

    @abstractmethod
    def update_fields(self, participant_id: int, **fields) -> bool:
        """Обновляет указанные поля участника."""
        pass


import logging
from dataclasses import asdict

# Импортируем существующие низкоуровневые функции
# В идеале, весь код из database.py, кроме init_database, должен перейти сюда
from database import (
    add_participant,
    get_participant_by_id,
    find_participant_by_name,
    get_all_participants,
    update_participant,
    update_participant_field,
)

logger = logging.getLogger(__name__)


class SqliteParticipantRepository(AbstractParticipantRepository):
    """Конкретная реализация репозитория для работы с базой данных SQLite."""

    def add(self, participant: Participant) -> int:
        logger.info(f"Adding participant to SQLite: {participant.FullNameRU}")
        participant_data = asdict(participant)
        participant_data.pop("id", None)
        return add_participant(participant_data)

    def get_by_id(self, participant_id: int) -> Optional[Participant]:
        """
        ✅ ИСПРАВЛЕНО: теперь корректно обрабатывает None от database функции.
        """
        logger.info(f"Getting participant by ID from SQLite: {participant_id}")

        participant_dict = get_participant_by_id(participant_id)

        if participant_dict is None:
            logger.debug(f"Participant {participant_id} not found in database")
            return None

        valid_fields = {
            k: v
            for k, v in participant_dict.items()
            if k in Participant.__annotations__
        }
        return Participant(**valid_fields)

    def get_by_name(self, full_name_ru: str) -> Optional[Participant]:
        logger.info(f"Getting participant by name from SQLite: {full_name_ru}")
        participant_dict = find_participant_by_name(full_name_ru)
        if participant_dict:
            valid_fields = {
                k: v
                for k, v in participant_dict.items()
                if k in Participant.__annotations__
            }
            return Participant(**valid_fields)
        return None

    def get_all(self) -> List[Participant]:
        logger.info("Getting all participants from SQLite")
        participants_list_of_dicts = get_all_participants()
        return [
            Participant(
                **{k: v for k, v in p.items() if k in Participant.__annotations__}
            )
            for p in participants_list_of_dicts
        ]

    def update(self, participant_id: int, data: Dict) -> bool:
        logger.info(f"Updating participant in SQLite, ID: {participant_id}")
        return update_participant(participant_id, data)

    def update_fields(self, participant_id: int, **fields) -> bool:
        logger.info(
            f"Updating participant fields in SQLite, ID: {participant_id}, fields: {list(fields.keys())}"
        )
        return update_participant_field(participant_id, fields)
