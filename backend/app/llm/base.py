from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


class LLMProvider(ABC):
    @abstractmethod
    def complete(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.3,
        model: str | None = None,
    ) -> str: ...

    @abstractmethod
    def complete_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        *,
        temperature: float = 0.3,
        model: str | None = None,
    ) -> tuple[str, list[ToolCall]]: ...
