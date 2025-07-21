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
