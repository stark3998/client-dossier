# app/agent/mcp/base.py
from abc import ABC, abstractmethod
from typing import Optional


class MCPPluginBase(ABC):
    def __init__(self, name: str, endpoint: str = ""):
        self.name = name
        self.endpoint = endpoint
        self._connected = False

    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def close(self) -> None: ...

    @property
    def connected(self) -> bool:
        return self._connected
