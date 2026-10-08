"""Gateway client contract: OpenAI shape out, raw SSE bytes back."""

import json

import httpx2
import pytest
from api.chat.gateway import Gateway, GatewayError

CANNED = b'data: {"choices":[{"delta":{"content":"hi"}}]}\n\n'
MESSAGES = [{"role": "user", "content": "hello"}]


def _gateway(handler, url="http://gw.local:4000"):
    return Gateway(url, "secret-key", "test-model", transport=httpx2.MockTransport(handler))


@pytest.mark.anyio
async def test_stream_posts_openai_shape_and_yields_raw_bytes():
    seen = {}

    async def handler(request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        seen["body"] = json.loads(request.content)
        return httpx2.Response(200, content=CANNED)

    out = b"".join([chunk async for chunk in _gateway(handler).stream(MESSAGES)])

    assert out == CANNED
    assert seen["url"] == "http://gw.local:4000/v1/chat/completions"
    assert seen["auth"] == "Bearer secret-key"
    assert seen["body"] == {"model": "test-model", "stream": True, "messages": MESSAGES}


@pytest.mark.anyio
async def test_stream_with_explicit_model_overrides_the_configured_one():
    seen = {}

    async def handler(request):
        seen["body"] = json.loads(request.content)
        return httpx2.Response(200, content=CANNED)

    b"".join([chunk async for chunk in _gateway(handler).stream(MESSAGES, model="llama-3")])

    assert seen["body"]["model"] == "llama-3"


@pytest.mark.anyio
async def test_trailing_slash_in_url_still_hits_completions_path():
    seen = {}

    async def handler(request):
        seen["url"] = str(request.url)
        return httpx2.Response(200, content=CANNED)

    gw = _gateway(handler, url="http://gw.local:4000/")
    b"".join([chunk async for chunk in gw.stream(MESSAGES)])

    assert seen["url"] == "http://gw.local:4000/v1/chat/completions"


@pytest.mark.anyio
async def test_http_error_maps_to_gateway_error():
    async def handler(request):
        return httpx2.Response(502, content=b"bad gateway")

    with pytest.raises(GatewayError):
        [chunk async for chunk in _gateway(handler).stream(MESSAGES)]


@pytest.mark.anyio
async def test_connect_error_maps_to_gateway_error():
    async def handler(request):
        raise httpx2.ConnectError("refused")

    with pytest.raises(GatewayError):
        [chunk async for chunk in _gateway(handler).stream(MESSAGES)]
