"""Абстрактный класс для клиента."""
from abc import ABC, abstractmethod
from simulator.device import SimulatedDevice
from typing import Any


class GatewayClient(ABC):
    """Абстрактный класс для клиента."""

    @abstractmethod
    async def __aenter__(self) -> "GatewayClient":
        """Вход в менеджер контекста."""
        pass

    @abstractmethod
    async def __aexit__(self, *_: object) -> None:
        """Выход из контекста."""
        pass

    @abstractmethod
    async def send(self, body: dict[str, Any]) -> tuple[int, dict]:
        """Отправка сообщения с клиента."""
        pass

    @abstractmethod
    async def register(self, device: SimulatedDevice) -> tuple[int, Any]:
        """Регистрация девайса."""
        pass
