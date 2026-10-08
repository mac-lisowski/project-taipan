"""LiteLLM gateway client: OpenAI SSE bytes in, nothing else."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

import httpx2
from fastapi import Depends, HTTPException

from api.config import ChatConfig, get_config

# Generous read: a thinking model may pause long between stream tokens.
READ_TIMEOUT_SECONDS = 300.0
CONNECT_TIMEOUT_SECONDS = 5.0


class GatewayError(Exception):
    """The gateway refused the completion or could not be reached."""


class Gateway:
    """Streams one chat completion as raw SSE bytes from the gateway."""

    def __init__(
        self,
        url: str,
        api_key: str,
        model: str,
        transport: httpx2.AsyncBaseTransport | None = None,
    ) -> None:
        self._url = url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._transport = transport

    async def stream(self, messages: list[dict], model: str | None = None) -> AsyncIterator[bytes]:
        client = httpx2.AsyncClient(
            timeout=httpx2.Timeout(READ_TIMEOUT_SECONDS, connect=CONNECT_TIMEOUT_SECONDS),
            transport=self._transport,
        )
        try:
            async with client.stream(
                "POST",
                f"{self._url}/v1/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    # None keeps the configured default; the route enforces membership.
                    "model": self._model if model is None else model,
                    "stream": True,
                    "messages": messages,
                },
            ) as response:
                # Fail here: a non-200 body is JSON, not SSE; callers send one error event.
                if response.status_code != 200:
                    raise GatewayError(f"gateway returned {response.status_code}")
                async for chunk in response.aiter_bytes():
                    yield chunk
        except httpx2.HTTPError as exc:
            raise GatewayError(f"gateway request failed: {type(exc).__name__}") from exc
        finally:
            await client.aclose()


def get_gateway() -> Gateway:
    """Build the gateway from config; the key never leaves the API process."""
    chat: ChatConfig = get_config().chat
    if not chat.litellm_api_key:
        # An unset key 401s mid-chat; refusing here names the missing env var.
        raise HTTPException(status_code=500, detail="API_LITELLM_API_KEY is not set")
    return Gateway(chat.litellm_url, chat.litellm_api_key, chat.chat_model)


GatewayDep = Annotated[Gateway, Depends(get_gateway)]
