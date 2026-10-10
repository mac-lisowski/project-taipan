"""Allowed chat models: the gateway listing cached behind a TTL."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Annotated

import httpx2
from fastapi import Depends

from api.chat.gateway import CONNECT_TIMEOUT_SECONDS, GatewayError
from api.config import get_config

# Short read: a hung listing must not stall the chat header poll.
LIST_TIMEOUT_SECONDS = 10.0

# /model/info carries LiteLLM's cost-map keys; absent or null means unsupported.
_FLAG_SOURCES = {
    "vision": "supports_vision",
    "pdf_input": "supports_pdf_input",
    "function_calling": "supports_function_calling",
    "tool_choice": "supports_tool_choice",
}


class ModelCatalog:
    """Cached `[{id, name}]` from GET /v1/models; failure keeps the last value."""

    def __init__(
        self,
        url: str,
        api_key: str,
        default_model: str,
        ttl_seconds: int,
        transport: httpx2.AsyncBaseTransport | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._url = url.rstrip("/")
        self._api_key = api_key
        self._default_model = default_model
        self._ttl_seconds = ttl_seconds
        self._transport = transport
        self._clock = clock
        self._cached: list[dict] | None = None
        self._info: dict[str, dict] = {}
        self._fetched_at = 0.0

    async def list(self) -> list[dict]:
        """Return the allowed models; the configured default always appears once."""
        if self._cached is None or self._clock() - self._fetched_at >= self._ttl_seconds:
            try:
                self._cached, self._info = await self._fetch()
                # Only success moves the timestamp, so a failed refresh retries next call.
                self._fetched_at = self._clock()
            except GatewayError:
                pass
        return self._with_default(self._cached or [])

    async def allowed_ids(self) -> set[str]:
        """The id set behind list(); the completion validator shares it."""
        return {entry["id"] for entry in await self.list()}

    async def capabilities(self, model_id: str) -> dict[str, bool]:
        """The flag set for a resolved id; unknown ids answer all-false."""
        await self.list()
        return self._flags_for(model_id)

    async def _fetch(self) -> tuple[list[dict], dict[str, dict]]:
        client = httpx2.AsyncClient(
            timeout=httpx2.Timeout(LIST_TIMEOUT_SECONDS, connect=CONNECT_TIMEOUT_SECONDS),
            transport=self._transport,
        )
        try:
            response = await client.get(
                f"{self._url}/v1/models",
                headers={"Authorization": f"Bearer {self._api_key}"},
            )
            if response.status_code != 200:
                raise GatewayError(f"gateway returned {response.status_code}")
            data = response.json().get("data", [])
            # A non-list `data` would TypeError below and escape as a 500.
            if not isinstance(data, list):
                raise GatewayError("model listing returned a malformed payload")
            entries = [
                {"id": item["id"], "name": item["id"]}
                for item in data
                # Wildcard or malformed entries list as-is; only the id is real.
                if isinstance(item, dict) and isinstance(item.get("id"), str)
            ]
            return entries, await self._fetch_info(client)
        except (httpx2.HTTPError, ValueError, AttributeError) as exc:
            raise GatewayError(f"model listing failed: {type(exc).__name__}") from exc
        finally:
            await client.aclose()

    async def _fetch_info(self, client: httpx2.AsyncClient) -> dict[str, dict]:
        """Best-effort /model/info keyed by model_name; any failure yields no flags."""
        try:
            response = await client.get(
                f"{self._url}/model/info",
                headers={"Authorization": f"Bearer {self._api_key}"},
            )
            if response.status_code != 200:
                return {}
            data = response.json().get("data", [])
            if not isinstance(data, list):
                return {}
            info: dict[str, dict] = {}
            for item in data:
                if not isinstance(item, dict):
                    continue
                name = item.get("model_name")
                model_info = item.get("model_info")
                if isinstance(name, str):
                    info[name] = model_info if isinstance(model_info, dict) else {}
            return info
        except (httpx2.HTTPError, ValueError):
            # Fail closed on input flags only; the listing still succeeds.
            return {}

    def _is_chat(self, model_id: str) -> bool:
        """Non-chat deployments (embeddings, images) cannot serve completions."""
        info = self._info.get(model_id)
        if info is None:
            return True
        mode = info.get("mode")
        return mode is None or mode == "chat"

    def _flags_for(self, model_id: str) -> dict[str, bool]:
        info = self._info.get(model_id) or {}
        return {flag: bool(info.get(source)) for flag, source in _FLAG_SOURCES.items()}

    def _with_default(self, entries: list[dict]) -> list[dict]:
        models: list[dict] = []
        found = False
        for entry in entries:
            if not self._is_chat(entry["id"]):
                continue
            item = {"id": entry["id"], "name": entry["name"], **self._flags_for(entry["id"])}
            if entry["id"] == self._default_model and not found:
                item["default"] = True
                found = True
            models.append(item)
        if not found:
            # The configured model must stay callable even when unlisted.
            models.append(
                {
                    "id": self._default_model,
                    "name": self._default_model,
                    **self._flags_for(self._default_model),
                    "default": True,
                }
            )
        return models


_catalog: ModelCatalog | None = None


def get_model_catalog() -> ModelCatalog:
    """One shared catalog per process: the cache must outlive any request."""
    global _catalog
    if _catalog is None:
        chat = get_config().chat
        _catalog = ModelCatalog(
            chat.litellm_url,
            chat.litellm_api_key,
            chat.chat_model,
            chat.chat_models_ttl_seconds,
        )
    return _catalog


ModelCatalogDep = Annotated[ModelCatalog, Depends(get_model_catalog)]
