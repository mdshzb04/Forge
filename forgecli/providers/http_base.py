"""Async HTTP base class shared by real providers.

A minimal :class:`HTTPChatProvider` that:

* lazily resolves an API key from configuration;
* exposes a typed :class:`httpx.AsyncClient` with sane timeouts;
* logs request/response lifecycle through the standard :mod:`logging`.

Subclasses implement :meth:`_format_request` and :meth:`_parse_response`
to translate between the provider's wire format and ForgeCLI's
provider-agnostic dataclasses.
"""



from __future__ import annotations

import os
from collections.abc import Iterable
from typing import Any

import httpx

from forgecli.core.errors import ProviderError
from forgecli.providers.base import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    ModelInfo,
    Provider,
    Role,
)


class HTTPChatProvider(Provider[Any]):

    """Base class for providers that talk JSON over HTTP."""



    name = "abstract-http"



    def __init__(

        self,

        config: Any,

        *,

        api_key: str | None = None,

        base_url: str | None = None,

        timeout: float = 60.0,

        client: httpx.AsyncClient | None = None,

    ) -> None:

        super().__init__(config)

        self._api_key = api_key or self._resolve_api_key()

        self._base_url = (

            base_url or getattr(config, "base_url", None) or self._default_base_url()

        ).rstrip("/")

        self._timeout = timeout

        self._client = client or httpx.AsyncClient(timeout=timeout)











    def _default_base_url(self) -> str:

        raise NotImplementedError



    def _resolve_api_key(self) -> str | None:

        env_var = getattr(self.config, "api_key_env", None)

        if env_var:

            env_val = os.environ.get(env_var)

            if env_val:

                return env_val

        from forgecli.core.credentials import get_api_key





        val = get_api_key(self.name)

        if val:

            return val

        if self.name == "google":

            val = get_api_key("google") or get_api_key("gemini")

            if val:

                return val

        return None



    def _format_request(self, request: ChatRequest) -> dict[str, Any]:

        raise NotImplementedError



    def _parse_response(self, payload: dict[str, Any]) -> ChatResponse:

        raise NotImplementedError



    def _embeddings_url(self) -> str:  # pragma: no cover - optional

        raise NotImplementedError



    def _format_embeddings(self, request: EmbeddingRequest) -> dict[str, Any]:

        raise NotImplementedError



    def _parse_embeddings(self, payload: dict[str, Any]) -> EmbeddingResponse:

        raise NotImplementedError



    def _default_embedding_model(self) -> str:  # pragma: no cover - optional

        raise NotImplementedError



    def _auth_headers(self) -> dict[str, str]:

        if not self._api_key:

            return {}

        return {"Authorization": f"Bearer {self._api_key}"}











    async def aclose(self) -> None:

        if self._client is not None:

            await self._client.aclose()



    def validate(self) -> None:

        if not self._api_key:

            env_var = getattr(self.config, "api_key_env", "API_KEY")

            raise ProviderError(

                f"{self.name}: missing API key. Set the {env_var} environment variable."

            )











    async def chat(self, request: ChatRequest) -> ChatResponse:

        if not self._api_key:

            self.validate()

        body = self._format_request(request)

        response = await self._client.post(

            self._chat_url_for(request), json=body, headers=self._auth_headers()

        )

        if response.status_code >= 400:

            raise ProviderError(

                f"{self.name} chat failed ({response.status_code}): {response.text[:500]}"

            )

        return self._parse_response(response.json())



    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        if not self._api_key:
            self.validate()

        model = request.model or self._default_embedding_model()

        # Lookup in embedding cache
        from forgecli.optimizer.embedding_cache import EmbeddingCache
        from forgecli.utils.paths import ProjectPaths
        cache_path = ProjectPaths.from_env().cache_dir / "embedding_cache.db"
        cache = EmbeddingCache(cache_path)

        cached_vectors, missing_inputs = cache.lookup(model, request.inputs)

        if not missing_inputs:
            vectors = [cached_vectors[inp] for inp in request.inputs]
            return EmbeddingResponse(
                model=model,
                vectors=vectors,
                prompt_tokens=0,
                total_tokens=0
            )

        # Get embeddings for missing inputs only (incremental update)
        partial_request = EmbeddingRequest(
            model=model,
            inputs=missing_inputs
        )
        body = self._format_embeddings(partial_request)
        response = await self._client.post(
            self._embeddings_url(), json=body, headers=self._auth_headers()
        )
        if response.status_code >= 400:
            raise ProviderError(
                f"{self.name} embed failed ({response.status_code}): {response.text[:500]}"
            )

        partial_response = self._parse_embeddings(response.json())

        # Save new embeddings to cache
        new_embeddings = dict(zip(missing_inputs, partial_response.vectors, strict=False))
        cache.save(model, new_embeddings)

        # Merge cached and new embeddings in original order
        merged_vectors = {}
        merged_vectors.update(cached_vectors)
        merged_vectors.update(new_embeddings)

        final_vectors = [merged_vectors[inp] for inp in request.inputs]
        return EmbeddingResponse(
            model=model,
            vectors=final_vectors,
            prompt_tokens=partial_response.prompt_tokens,
            total_tokens=partial_response.total_tokens
        )



    async def list_models(self) -> list[ModelInfo]:

        try:



            if self.name == "mock":

                return self._known_models()

            response = await self._client.get(

                f"{self._base_url}/models", headers=self._auth_headers(), timeout=5.0

            )

            if response.status_code == 200:

                data = response.json()

                models_list = data.get("data", [])

                if models_list:

                    return [

                        ModelInfo(

                            id=str(m["id"]),

                            name=str(m.get("id")),

                            context_window=128_000,

                            supports_tools=True,

                            supports_vision=True,

                        )

                        for m in models_list

                        if isinstance(m, dict) and m.get("id") is not None

                    ]

        except Exception:

            pass

        return self._known_models()



    def _known_models(self) -> list[ModelInfo]:

        return []



    def _chat_url(self) -> str:

        """Default chat URL; providers may override :meth:`_chat_url_for`."""

        raise NotImplementedError



    def _chat_url_for(self, request: ChatRequest) -> str:

        """Return the chat URL for ``request``; default is the static URL."""

        return self._chat_url()















def messages_to_openai(messages: Iterable[ChatMessage]) -> list[dict[str, Any]]:

    """Translate :class:`ChatMessage` objects into the OpenAI schema."""

    out: list[dict[str, Any]] = []

    for message in messages:

        entry: dict[str, Any] = {"role": message.role.value, "content": message.content}

        if message.name:

            entry["name"] = message.name

        if message.role is Role.TOOL and message.tool_call_id:

            entry["tool_call_id"] = message.tool_call_id

        out.append(entry)

    return out





__all__ = ["HTTPChatProvider", "messages_to_openai"]

