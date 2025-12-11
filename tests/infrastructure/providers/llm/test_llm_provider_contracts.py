"""Offline contract tests for LLM providers covering prompt build and retries."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast

import pytest
import tenacity.asyncio as tenacity_async

from src.application.interfaces.llm import LLMPrompt, LLMRequest, LLMResponse
from src.application.interfaces.secret import (
    ISecretManager,
    SecretMetadata,
    SecretVersion,
)
from src.infrastructure.providers.llm.base import (
    BaseLLMProvider,
    ComprehensiveAnalysisResponse,
    SectionAnalysisResponse,
)
from src.infrastructure.providers.llm.google import GoogleLLMProvider
from src.infrastructure.providers.llm.openai import OpenAILLMProvider
from src.shared.config.providers import LLMConfig
from src.shared.enums import FilingType
from src.shared.enums import LLMProvider as LLMProviderEnum
from src.shared.models import LLMModelInfo
from src.shared.types import RequestId


class StubSecretManager(ISecretManager):
    async def get_secret(
        self, secret_name: str, version_id: str | None = None, version_stage: str | None = None
    ) -> str:
        return f"secret-for-{secret_name}"

    async def get_secret_binary(
        self, secret_name: str, version_id: str | None = None, version_stage: str | None = None
    ) -> bytes:
        raise NotImplementedError

    async def create_secret(
        self, secret_name: str, secret_value: str | bytes, description: str | None = None, tags: dict[str, str] | None = None
    ) -> Any:
        raise NotImplementedError

    async def update_secret(
        self, secret_name: str, secret_value: str | bytes, version_stage: str | None = None
    ) -> Any:
        raise NotImplementedError

    async def delete_secret(
        self, secret_name: str, recovery_window_days: int | None = 30, force_delete: bool = False
    ) -> bool:
        raise NotImplementedError

    async def restore_secret(self, secret_name: str) -> Any:
        raise NotImplementedError

    async def rotate_secret(
        self, secret_name: str, rotation_config: Any | None = None
    ) -> bool:
        raise NotImplementedError

    async def list_secrets(
        self, prefix: str | None = None, include_deleted: bool = False
    ) -> list[SecretMetadata]:
        _ = prefix
        _ = include_deleted
        return []

    async def get_secret_metadata(self, secret_name: str) -> SecretMetadata:
        raise NotImplementedError

    async def list_secret_versions(
        self, secret_name: str, include_deprecated: bool = False
    ) -> list[SecretVersion]:
        _ = secret_name
        _ = include_deprecated
        return []

    async def tag_secret(self, secret_name: str, tags: dict[str, str]) -> bool:
        _ = secret_name
        _ = tags
        return True

    async def untag_secret(self, secret_name: str, tag_keys: list[str]) -> bool:
        _ = secret_name
        _ = tag_keys
        return True

    async def validate_secret(
        self, secret_name: str, validator_arn: str | None = None
    ) -> bool:
        _ = secret_name
        _ = validator_arn
        return True


class RecordingLLMProvider(BaseLLMProvider):
    def __init__(self, config: LLMConfig):
        super().__init__(
            config,
            LLMModelInfo(
                schema_version=1,
                model_name=config.model_name,
                model_version="test",
                provider=config.provider.value,
                supports_streaming=False,
                supports_functions=False,
                pricing_per_1k_tokens=0.0,
                capabilities=["chat"],
            ),
        )
        self.prompts: list[LLMPrompt] = []

    async def analyze_filing_sections(
        self,
        filing_sections: dict[str, str],
        filing_type: FilingType,
        company_name: str,
        analysis_focus: list[str] | None = None,
    ) -> ComprehensiveAnalysisResponse:
        raise NotImplementedError

    async def analyze_section(
        self,
        section_text: str,
        section_name: str,
        filing_type: FilingType,
        company_name: str,
    ) -> SectionAnalysisResponse:
        raise NotImplementedError

    async def generate_completion(
        self, prompt: LLMPrompt, request_id: str | None = None
    ) -> LLMResponse:
        self.prompts.append(prompt)
        return LLMResponse(
            schema_version=1,
            content="ok",
            model=self.model_info.model_name,
            provider=LLMProviderEnum.OPENAI,
            usage_tokens=0,
            prompt_tokens=0,
            completion_tokens=0,
            latency_ms=0,
            timestamp=datetime.now(UTC),
            request_id=RequestId(request_id) if request_id else None,
            cost=0.0,
        )

    async def count_tokens(self, text: str) -> int:
        return len(text) // 4


class FakeOpenAIUsage:
    def __init__(self, prompt_tokens: int, completion_tokens: int):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens


class FakeOpenAIResponse:
    def __init__(self, content: str, prompt_tokens: int, completion_tokens: int):
        self.choices = [SimpleNamespace(message=SimpleNamespace(content=content))]
        self.usage = FakeOpenAIUsage(prompt_tokens, completion_tokens)


class FakeOpenAICompletions:
    def __init__(self, response: FakeOpenAIResponse, *, fail_first: bool = False):
        self.calls: list[dict[str, Any]] = []
        self._response = response
        self._fail_first = fail_first

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        if self._fail_first and len(self.calls) == 1:
            raise RuntimeError("transient outage")
        return self._response


class FakeOpenAIClient:
    def __init__(self, completions: FakeOpenAICompletions):
        self.chat = SimpleNamespace(completions=completions)


class FakeGoogleResponse:
    def __init__(self, text: str, prompt_tokens: int, completion_tokens: int):
        self.text = text
        self.usage_metadata = SimpleNamespace(
            prompt_token_count=prompt_tokens,
            candidates_token_count=completion_tokens,
        )


class FakeGoogleModels:
    def __init__(self, response: FakeGoogleResponse, *, fail_first: bool = False):
        self.calls: list[dict[str, Any]] = []
        self._response = response
        self._fail_first = fail_first

    async def generate_content(self, *, model: str, contents: list[Any], config: Any) -> FakeGoogleResponse:
        self.calls.append({"model": model, "contents": contents, "config": config})
        if self._fail_first and len(self.calls) == 1:
            raise RuntimeError("temporary outage")
        return self._response


class FakeGoogleClient:
    def __init__(self, models: FakeGoogleModels):
        self.aio = SimpleNamespace(models=models)


@pytest.mark.asyncio
async def test_base_complete_builds_prompt_defaults() -> None:
    config = LLMConfig(
        provider=LLMProviderEnum.OPENAI,
        model_name="gpt-5-nano",
        api_key_secret_name="OPENAI_API_KEY",
    )
    provider = RecordingLLMProvider(config)

    request = LLMRequest(
        prompt="user payload",
        system_prompt=None,
        max_tokens=None,
        temperature=0.25,
        top_p=0.9,
        frequency_penalty=0.1,
        presence_penalty=0.2,
    )

    await provider.complete(request)
    [prompt] = provider.prompts

    assert prompt.system_prompt == "You are a helpful assistant."
    assert prompt.user_prompt == "user payload"
    assert prompt.max_tokens == 1000
    assert prompt.temperature == pytest.approx(0.25)
    assert prompt.top_p == pytest.approx(0.9)
    assert prompt.frequency_penalty == pytest.approx(0.1)
    assert prompt.presence_penalty == pytest.approx(0.2)


@pytest.mark.asyncio
async def test_openai_generate_completion_builds_payload_and_usage(monkeypatch: pytest.MonkeyPatch) -> None:
    config = LLMConfig(
        provider=LLMProviderEnum.OPENAI,
        model_name="gpt-5-nano",
        api_key_secret_name="OPENAI_API_KEY",
    )
    provider = OpenAILLMProvider(config, StubSecretManager())
    response = FakeOpenAIResponse("completion text", prompt_tokens=12, completion_tokens=8)
    completions = FakeOpenAICompletions(response)
    provider.client = cast(Any, FakeOpenAIClient(completions))
    provider.api_key = "static-key"

    async def _noop() -> None:
        return None

    monkeypatch.setattr(provider, "_ensure_client", _noop)

    prompt = LLMPrompt(
        schema_version=1,
        system_prompt="system",
        user_prompt="user",
        temperature=0.4,
        max_tokens=50,
        top_p=0.8,
        frequency_penalty=0.2,
        presence_penalty=0.3,
        stop_sequences=["\n\n"],
    )

    result = await provider.generate_completion(prompt)
    [call] = completions.calls

    assert call["model"] == config.model_name
    assert call["messages"][0]["content"] == "system"
    assert call["messages"][1]["content"] == "user"
    assert call["extra_body"]["usage"] == {"include": True}
    assert result.prompt_tokens == 12
    assert result.completion_tokens == 8
    assert result.usage_tokens == 20
    assert result.cost == pytest.approx(provider._calculate_cost(12, 8))


@pytest.mark.asyncio
async def test_openai_generate_completion_retries_on_transient_error(monkeypatch: pytest.MonkeyPatch) -> None:
    config = LLMConfig(
        provider=LLMProviderEnum.OPENAI,
        model_name="gpt-5-nano",
        api_key_secret_name="OPENAI_API_KEY",
    )
    provider = OpenAILLMProvider(config, StubSecretManager())
    response = FakeOpenAIResponse("steady response", prompt_tokens=1, completion_tokens=1)
    completions = FakeOpenAICompletions(response, fail_first=True)
    provider.client = cast(Any, FakeOpenAIClient(completions))
    provider.api_key = "static-key"

    async def _noop() -> None:
        return None

    async def _fast_sleep(_delay: float) -> None:
        await asyncio.sleep(0)

    monkeypatch.setattr(provider, "_ensure_client", _noop)
    monkeypatch.setattr(tenacity_async, "_portable_async_sleep", _fast_sleep)

    prompt = LLMPrompt(
        schema_version=1,
        system_prompt="system",
        user_prompt="user",
        temperature=0.0,
        max_tokens=5,
    )

    result = await provider.generate_completion(prompt)

    assert len(completions.calls) == 2
    assert result.content == "steady response"


@pytest.mark.asyncio
async def test_google_generate_completion_retries_and_tracks_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    config = LLMConfig(
        provider=LLMProviderEnum.GOOGLE,
        model_name="gemini-1.5",
        api_key_secret_name="GEMINI_API_KEY",
    )
    provider = GoogleLLMProvider(config, StubSecretManager())
    response = FakeGoogleResponse(text="gemini output", prompt_tokens=5, completion_tokens=9)
    models = FakeGoogleModels(response, fail_first=True)
    provider.client = cast(Any, FakeGoogleClient(models))

    async def _noop() -> None:
        return None

    async def _fast_sleep(_delay: float) -> None:
        await asyncio.sleep(0)

    monkeypatch.setattr(provider, "_ensure_initialized", _noop)
    monkeypatch.setattr(tenacity_async, "_portable_async_sleep", _fast_sleep)

    prompt = LLMPrompt(
        schema_version=1,
        system_prompt="system instruction",
        user_prompt="user body",
        temperature=0.6,
        max_tokens=25,
        top_p=0.7,
        stop_sequences=["--stop--"],
    )

    result = await provider.generate_completion(prompt)
    call = models.calls[-1]

    assert len(models.calls) == 2
    assert prompt.system_prompt in call["contents"][0]
    assert call["model"] == config.model_name
    assert result.prompt_tokens == 5
    assert result.completion_tokens == 9
    assert result.usage_tokens == 14
    assert result.cost == pytest.approx(provider._calculate_cost(5, 9))
