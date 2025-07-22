from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Set

# Используем dataclass из models, чтобы работать с объектами, а не словарями
from models.participant import Participant


class AbstractParticipantRepository(ABC):
    """
    ✅ ИСПРАВЛЕННЫЙ Repository pattern - работает с доменными объектами Participant.

    Принципы:
    1. Все методы работают с объектами Participant, не с Dict
    2. Repository отвечает только за персистентность, не за бизнес-логику
    3. Методы должны быть атомарными и предсказуемыми
    4. Поддержка как полного, так и частичного обновления
    """

    @abstractmethod
    def add(self, participant: Participant) -> int:
        """
        Добавляет участника и возвращает его ID.

        Args:
            participant: Объект участника для добавления

        Returns:
            int: ID созданного участника

        Raises:
            ValidationError: При неверных данных
            BotException: При ошибках БД
        """
        pass

    @abstractmethod
    def get_by_id(self, participant_id: int) -> Optional[Participant]:
        """
        Находит участника по ID.

        Args:
            participant_id: ID участника

        Returns:
            Participant или None если не найден
        """
        pass

    @abstractmethod
    def get_by_name(self, full_name_ru: str) -> Optional[Participant]:
        """
        Находит участника по полному имени.

        Args:
            full_name_ru: Полное имя на русском

        Returns:
            Participant или None если не найден
        """
        pass

    @abstractmethod
    def get_all(self) -> List[Participant]:
        """Возвращает всех участников."""
        pass

    @abstractmethod
    def update(self, participant: Participant) -> bool:
        """
        ✅ ИСПРАВЛЕНО: принимает объект Participant, а не Dict.

        Обновляет участника полностью. participant.id должен быть установлен.

        Args:
            participant: Объект участника с установленным ID

        Returns:
            bool: True если обновление успешно

        Raises:
            ParticipantNotFoundError: Если участник не найден
            ValidationError: При неверных данных
            ValueError: Если participant.id не установлен
        """
        pass

    @abstractmethod
    def update_fields(self, participant_id: int, **fields) -> bool:
        """
        ✅ НОВЫЙ МЕТОД: частичное обновление конкретных полей.

        Args:
            participant_id: ID участника
            **fields: Поля для обновления (FullNameRU="Новое имя", Gender="M", etc.)

        Returns:
            bool: True если обновление успешно

        Raises:
            ParticipantNotFoundError: Если участник не найден
            ValidationError: При неверных данных
            ValueError: Если переданы неизвестные поля

        Example:
            repo.update_fields(123, FullNameRU="Новое имя", Gender="M")
        """
        pass

    @abstractmethod
    def delete(self, participant_id: int) -> bool:
        """
        ✅ НОВЫЙ МЕТОД: удаление участника.

        Args:
            participant_id: ID участника для удаления

        Returns:
            bool: True если удаление успешно

        Raises:
            ParticipantNotFoundError: Если участник не найден
        """
        pass

    @abstractmethod
    def exists(self, participant_id: int) -> bool:
        """
        ✅ НОВЫЙ МЕТОД: проверка существования участника.

        Args:
            participant_id: ID участника

        Returns:
            bool: True если участник существует
        """
        pass


import logging
from dataclasses import asdict

# Импортируем существующие низкоуровневые функции
from database import (
    add_participant,
    get_participant_by_id,
    find_participant_by_name,
    get_all_participants,
    update_participant,
    delete_participant
)
from utils.exceptions import ParticipantNotFoundError, ValidationError, BotException

logger = logging.getLogger(__name__)


class SqliteParticipantRepository(AbstractParticipantRepository):
    """✅ ИСПРАВЛЕННАЯ конкретная реализация репозитория для SQLite."""

    def add(self, participant: Participant) -> int:
        logger.info(f"Adding participant to SQLite: {participant.FullNameRU}")
        participant_data = asdict(participant)
        participant_data.pop('id', None)  # Убираем ID перед добавлением
        return add_participant(participant_data)

    def get_by_id(self, participant_id: int) -> Optional[Participant]:
        logger.info(f"Getting participant by ID from SQLite: {participant_id}")

        participant_dict = get_participant_by_id(participant_id)

        if participant_dict is None:
            logger.debug(f"Participant {participant_id} not found in database")
            return None

        # Фильтруем только валидные поля для Participant dataclass
        valid_fields = {k: v for k, v in participant_dict.items() if k in Participant.__annotations__}
        return Participant(**valid_fields)

    def get_by_name(self, full_name_ru: str) -> Optional[Participant]:
        logger.info(f"Getting participant by name from SQLite: {full_name_ru}")
        participant_dict = find_participant_by_name(full_name_ru)
        if participant_dict:
            valid_fields = {k: v for k, v in participant_dict.items() if k in Participant.__annotations__}
            return Participant(**valid_fields)
        return None

    def get_all(self) -> List[Participant]:
        logger.info("Getting all participants from SQLite")
        participants_list_of_dicts = get_all_participants()
        return [
            Participant(**{k: v for k, v in p.items() if k in Participant.__annotations__})
            for p in participants_list_of_dicts
        ]

    def update(self, participant: Participant) -> bool:
        """
        ✅ ИСПРАВЛЕНО: принимает объект Participant вместо Dict.
        """
        if participant.id is None:
            raise ValueError("Participant ID must be set for update operation")

        logger.info(f"Updating participant in SQLite: {participant.FullNameRU} (ID: {participant.id})")

        # Конвертируем в Dict для database слоя
        participant_data = asdict(participant)
        participant_data.pop('id', None)  # Убираем ID из данных

        return update_participant(participant.id, participant_data)

    def update_fields(self, participant_id: int, **fields) -> bool:
        """
        ✅ НОВЫЙ МЕТОД: частичное обновление полей.
        """
        # Валидация: проверяем, что все поля существуют в Participant
        valid_field_names = set(Participant.__annotations__.keys())
        invalid_fields = set(fields.keys()) - valid_field_names

        if invalid_fields:
            raise ValueError(f"Invalid fields for Participant: {invalid_fields}")

        logger.info(
            f"Updating fields for participant {participant_id}: {list(fields.keys())}"
        )

        # Получаем текущего участника
        current = self.get_by_id(participant_id)
        if current is None:
            raise ParticipantNotFoundError(f"Participant with id {participant_id} not found")

        # Создаем обновленную копию
        current_dict = asdict(current)
        current_dict.update(fields)

        # Создаем новый объект и обновляем
        updated_participant = Participant(**current_dict)
        return self.update(updated_participant)

    def delete(self, participant_id: int) -> bool:
        """
        ✅ ОБНОВЛЕНО: теперь использует реальное удаление из БД.
        """
        logger.info(f"Deleting participant from SQLite: {participant_id}")
        return delete_participant(participant_id)

    def exists(self, participant_id: int) -> bool:
        """
        ✅ НОВЫЙ МЕТОД: проверка существования.
        """
        return self.get_by_id(participant_id) is not None
