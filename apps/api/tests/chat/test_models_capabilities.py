"""Capability flags from the LiteLLM /model/info payload on the catalog."""

import httpx2
import pytest
from api.chat.models import get_model_catalog
from api.main import app
from api_testsupport import FakeClock, model_catalog, signin

LISTING = {
    "data": [
        {"id": "vision-pro"},
        {"id": "plain-llm"},
        {"id": "no-info-llm"},
        {"id": "legacy-llm"},
        {"id": "null-info-llm"},
        {"id": "text-embedder"},
    ]
}

INFO = {
    "data": [
        {
            "model_name": "vision-pro",
            "model_info": {
                "mode": "chat",
                "supports_vision": True,
                "supports_pdf_input": True,
                "supports_function_calling": True,
                "supports_tool_choice": True,
                "supports_audio_input": False,
            },
        },
        {
            "model_name": "plain-llm",
            "model_info": {
                "mode": "chat",
                "supports_vision": False,
                "supports_pdf_input": None,
                "supports_function_calling": True,
                "supports_tool_choice": False,
            },
        },
        # No mode key: an absent mode still serves chat completions.
        {"model_name": "legacy-llm", "model_info": {"supports_vision": True}},
        {"model_name": "null-info-llm", "model_info": None},
        {"model_name": "text-embedder", "model_info": {"mode": "embedding"}},
        # Info without a /v1/models entry must never list.
        {"model_name": "ghost-info", "model_info": {"mode": "chat", "supports_vision": True}},
    ]
}

FALSE_FLAGS = {
    "vision": False,
    "pdf_input": False,
    "function_calling": False,
    "tool_choice": False,
}


def _gateway(info=INFO, *, info_status=200, info_error=None):
    """Stubbed transport routing /v1/models and /model/info separately."""

    async def handler(request):
        if request.url.path == "/model/info":
            if info_error is not None:
                raise info_error
            return httpx2.Response(info_status, json=info)
        return httpx2.Response(200, json=LISTING)

    return handler


@pytest.mark.anyio
async def test_entries_carry_the_flags_from_model_info():
    catalog = model_catalog(_gateway(), default="vision-pro")

    models = await catalog.list()

    by_id = {entry["id"]: entry for entry in models}
    assert by_id["vision-pro"] == {
        "id": "vision-pro",
        "name": "vision-pro",
        "default": True,
        "vision": True,
        "pdf_input": True,
        "function_calling": True,
        "tool_choice": True,
    }
    # Null and absent supports_* keys both read as unsupported.
    assert by_id["plain-llm"] == {
        "id": "plain-llm",
        "name": "plain-llm",
        "vision": False,
        "pdf_input": False,
        "function_calling": True,
        "tool_choice": False,
    }


@pytest.mark.anyio
async def test_models_without_info_data_report_all_flags_false():
    catalog = model_catalog(_gateway())

    models = await catalog.list()

    by_id = {entry["id"]: entry for entry in models}
    assert by_id["no-info-llm"] == {"id": "no-info-llm", "name": "no-info-llm", **FALSE_FLAGS}
    assert by_id["null-info-llm"] == {
        "id": "null-info-llm",
        "name": "null-info-llm",
        **FALSE_FLAGS,
    }
    # The appended configured default carries the flags too.
    assert by_id["gpt-4o-mini"] == {
        "id": "gpt-4o-mini",
        "name": "gpt-4o-mini",
        "default": True,
        **FALSE_FLAGS,
    }


@pytest.mark.anyio
async def test_non_chat_modes_and_info_only_entries_never_list():
    catalog = model_catalog(_gateway())

    models = await catalog.list()
    allowed = await catalog.allowed_ids()

    ids = {entry["id"] for entry in models}
    assert "text-embedder" not in ids
    assert "ghost-info" not in ids
    assert "text-embedder" not in allowed
    # An info entry without a mode still lists.
    assert ids >= {"vision-pro", "plain-llm", "no-info-llm", "legacy-llm", "null-info-llm"}


@pytest.mark.anyio
async def test_failed_info_fetch_degrades_to_false_flags():
    catalog = model_catalog(_gateway(info_status=503))

    models = await catalog.list()

    by_id = {entry["id"]: entry for entry in models}
    assert by_id["vision-pro"] == {"id": "vision-pro", "name": "vision-pro", **FALSE_FLAGS}
    assert by_id["plain-llm"] == {"id": "plain-llm", "name": "plain-llm", **FALSE_FLAGS}


@pytest.mark.anyio
async def test_info_transport_error_degrades_to_false_flags():
    catalog = model_catalog(_gateway(info_error=httpx2.ConnectError("refused")))

    models = await catalog.list()

    by_id = {entry["id"]: entry for entry in models}
    assert by_id["vision-pro"]["vision"] is False
    assert "text-embedder" in by_id


@pytest.mark.anyio
async def test_malformed_info_payload_degrades_to_false_flags():
    catalog = model_catalog(_gateway(info={"data": "not-a-list"}))

    models = await catalog.list()

    by_id = {entry["id"]: entry for entry in models}
    assert by_id["vision-pro"]["vision"] is False


@pytest.mark.anyio
async def test_capabilities_resolves_flags_for_a_listed_model():
    catalog = model_catalog(_gateway())

    flags = await catalog.capabilities("vision-pro")

    assert flags == {
        "vision": True,
        "pdf_input": True,
        "function_calling": True,
        "tool_choice": True,
    }


@pytest.mark.anyio
async def test_capabilities_answers_all_false_for_unknown_and_default_ids():
    catalog = model_catalog(_gateway())

    assert await catalog.capabilities("never-heard-of-it") == FALSE_FLAGS
    # The configured default resolves even with no info entry.
    assert await catalog.capabilities("gpt-4o-mini") == FALSE_FLAGS
    # A listed model without info resolves too.
    assert await catalog.capabilities("no-info-llm") == FALSE_FLAGS


@pytest.mark.anyio
async def test_info_fetch_shares_the_listing_ttl_window():
    hits = []
    clock = FakeClock()

    async def handler(request):
        hits.append(request.url.path)
        if request.url.path == "/model/info":
            return httpx2.Response(200, json=INFO)
        return httpx2.Response(200, json=LISTING)

    catalog = model_catalog(handler, ttl_seconds=60, clock=clock)
    await catalog.list()
    await catalog.list()

    assert hits.count("/model/info") == 1
    assert hits.count("/v1/models") == 1

    clock.advance(61)
    await catalog.list()

    assert hits.count("/model/info") == 2
    assert hits.count("/v1/models") == 2


@pytest.mark.anyio
async def test_info_refetch_failure_keeps_the_listing_alive():
    clock = FakeClock()
    info_calls = []

    async def handler(request):
        if request.url.path == "/model/info":
            info_calls.append(1)
            if len(info_calls) > 1:
                return httpx2.Response(503, json={"error": "down"})
            return httpx2.Response(200, json=INFO)
        return httpx2.Response(200, json=LISTING)

    catalog = model_catalog(handler, ttl_seconds=60, clock=clock)
    warm = await catalog.list()
    assert "text-embedder" not in {entry["id"] for entry in warm}
    clock.advance(61)

    stale = await catalog.list()

    # The listing still succeeds with degraded info: unknown modes list and
    # every flag reads false.
    by_id = {entry["id"]: entry for entry in stale}
    assert by_id["vision-pro"] == {"id": "vision-pro", "name": "vision-pro", **FALSE_FLAGS}
    assert by_id["text-embedder"] == {
        "id": "text-embedder",
        "name": "text-embedder",
        **FALSE_FLAGS,
    }


@pytest.fixture
def catalog_override(client):
    def install(catalog):
        app.dependency_overrides[get_model_catalog] = lambda: catalog
        return catalog

    yield install
    app.dependency_overrides.pop(get_model_catalog, None)


def test_models_endpoint_serves_capability_flags(client, catalog_override):
    catalog_override(model_catalog(_gateway()))
    signin(client, "caps@x.com")

    resp = client.get("/api/chat/models")

    assert resp.status_code == 200
    by_id = {entry["id"]: entry for entry in resp.json()}
    assert by_id["vision-pro"]["vision"] is True
    assert by_id["vision-pro"]["pdf_input"] is True
    assert by_id["plain-llm"] == {
        "id": "plain-llm",
        "name": "plain-llm",
        "vision": False,
        "pdf_input": False,
        "function_calling": True,
        "tool_choice": False,
    }
    assert "text-embedder" not in by_id
