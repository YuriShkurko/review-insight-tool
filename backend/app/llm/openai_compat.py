import json

from openai import OpenAI

from app.llm.base import LLMProvider, ToolCall

LLM_TIMEOUT_SECONDS = 60


class OpenAICompatProvider(LLMProvider):
    """Single provider for OpenAI and OpenRouter (same SDK, different base_url)."""

    def __init__(
        self,
        api_key: str,
        default_model: str,
        base_url: str | None = None,
        timeout: float = LLM_TIMEOUT_SECONDS,
    ) -> None:
        self._client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
        self._default_model = default_model

    def complete(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.3,
        model: str | None = None,
    ) -> str:
        response = self._client.chat.completions.create(
            model=model or self._default_model,
            messages=messages,
            temperature=temperature,
        )
        return response.choices[0].message.content or ""

    def complete_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        *,
        temperature: float = 0.3,
        model: str | None = None,
    ) -> tuple[str, list[ToolCall]]:
        response = self._client.chat.completions.create(
            model=model or self._default_model,
            messages=messages,
            tools=tools,
            temperature=temperature,
        )
        message = response.choices[0].message
        text = message.content or ""
        tool_calls = []
        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append(
                    ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=json.loads(tc.function.arguments or "{}"),
                    )
                )
        return text, tool_calls
