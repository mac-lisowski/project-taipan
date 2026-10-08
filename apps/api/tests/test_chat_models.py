"""Allowed chat models: the cached gateway listing behind the session gate."""

import httpx2
import pytest
from api.chat.models import get_model_catalog
from api.main import app
from api_testsupport import (
    CHAT_MODELS_LISTING,
    FakeClock,
    model_catalog,
    signin,
)


def _respond(payload, hits, status=200):
    async def handler(request):
        hits.append(request)
        return httpx2.Response(status, json=payload)

    return handler


@pytest.fixture
def catalog_override(client):
    """Swap the shared catalog behind the dependency; cleaned up per test."""

    def install(catalog):
        app.dependency_overrides[get_model_catalog] = lambda: catalog
        return catalog

    yield install
    app.dependency_overrides.pop(get_model_catalog, None)


@pytest.mark.anyio
async def test_list_maps_gateway_ids_and_marks_the_configured_default():
    hits = []
    catalog = model_catalog(_respond(CHAT_MODELS_LISTING, hits))

    models = await catalog.list()

    assert models == [
        {"id": "gpt-4o-mini", "name": "gpt-4o-mini", "default": True},
        {"id": "llama-3", "name": "llama-3"},
    ]
    assert hits[0].url.host == "gw.local"
    assert hits[0].url.path == "/v1/models"
    assert hits[0].headers["authorization"] == "Bearer secret-key"


@pytest.mark.anyio
async def test_list_appends_the_default_when_the_gateway_lacks_it():
    catalog = model_catalog(_respond({"data": [{"id": "llama-3"}]}, []))

    models = await catalog.list()

    assert models == [
        {"id": "llama-3", "name": "llama-3"},
        {"id": "gpt-4o-mini", "name": "gpt-4o-mini", "default": True},
    ]
    assert sum(1 for model in models if model.get("default")) == 1


@pytest.mark.anyio
async def test_list_reuses_the_cached_listing_inside_the_ttl():
    hits = []
    catalog = model_catalog(_respond(CHAT_MODELS_LISTING, hits), ttl_seconds=60)

    first = await catalog.list()
    second = await catalog.list()

    assert second == first
    assert len(hits) == 1


@pytest.mark.anyio
async def test_list_refetches_once_the_ttl_expires():
    hits = []
    clock = FakeClock()
    responses = iter([CHAT_MODELS_LISTING, {"data": [{"id": "fresh-model"}]}])

    async def handler(request):
        hits.append(request)
        return httpx2.Response(200, json=next(responses))

    catalog = model_catalog(handler, ttl_seconds=60, clock=clock)
    await catalog.list()
    clock.advance(61)

    models = await catalog.list()

    assert len(hits) == 2
    assert models == [
        {"id": "fresh-model", "name": "fresh-model"},
        {"id": "gpt-4o-mini", "name": "gpt-4o-mini", "default": True},
    ]


@pytest.mark.anyio
async def test_failed_refresh_keeps_the_last_good_listing():
    clock = FakeClock()
    outcomes = iter(
        [CHAT_MODELS_LISTING, httpx2.ConnectError("refused"), {"data": [{"id": "back"}]}]
    )

    async def handler(request):
        outcome = next(outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        return httpx2.Response(200, json=outcome)

    catalog = model_catalog(handler, ttl_seconds=60, clock=clock)
    warm = await catalog.list()
    clock.advance(61)

    stale = await catalog.list()

    assert stale == warm

    # A failure must not refresh the timestamp: the next call retries and recovers.
    recovered = await catalog.list()
    assert recovered[0] == {"id": "back", "name": "back"}


@pytest.mark.anyio
async def test_cold_failure_serves_only_the_default_model():
    async def handler(request):
        raise httpx2.ConnectError("refused")

    catalog = model_catalog(handler)

    assert await catalog.list() == [{"id": "gpt-4o-mini", "name": "gpt-4o-mini", "default": True}]


@pytest.mark.anyio
async def test_non_200_listing_counts_as_a_failed_fetch():
    catalog = model_catalog(_respond({"error": "nope"}, [], status=503))

    assert await catalog.list() == [{"id": "gpt-4o-mini", "name": "gpt-4o-mini", "default": True}]


@pytest.mark.anyio
async def test_non_listing_data_counts_as_a_failed_fetch():
    catalog = model_catalog(_respond({"data": 5}, []))

    assert await catalog.list() == [{"id": "gpt-4o-mini", "name": "gpt-4o-mini", "default": True}]


def test_models_endpoint_serves_the_catalog(client, catalog_override):
    hits = []
    catalog_override(model_catalog(_respond(CHAT_MODELS_LISTING, hits)))
    signin(client, "picker@x.com")

    resp = client.get("/api/chat/models")

    assert resp.status_code == 200
    assert resp.json() == [
        {"id": "gpt-4o-mini", "name": "gpt-4o-mini", "default": True},
        {"id": "llama-3", "name": "llama-3"},
    ]


def test_models_endpoint_requires_a_session(client, catalog_override):
    hits = []
    catalog_override(model_catalog(_respond(CHAT_MODELS_LISTING, hits)))

    resp = client.get("/api/chat/models")

    assert resp.status_code == 401
    assert hits == []
