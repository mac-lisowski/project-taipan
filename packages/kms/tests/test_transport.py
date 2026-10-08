"""Transport error mapping: the typed status rides on KmsError.

Structural, no live stack: a mocked HTTP layer proves the wiring
between a real response status and KmsError.status_code. If that
regresses, find_key re-raises 404 and ensure creates duplicates.
"""

import httpx2
import pytest
from kms import KmsError
from kms._infisical_transport import InfisicalTransport


def transport_for(handler) -> InfisicalTransport:
    transport = InfisicalTransport("http://kms.test", "unused-token")
    transport._client = httpx2.Client(
        base_url="http://kms.test", transport=httpx2.MockTransport(handler)
    )
    return transport


def test_http_status_lands_on_the_error() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(404, text="{}")

    with pytest.raises(KmsError) as caught:
        transport_for(handler).request("GET", "/api/v1/kms/keys/key-name/nope")
    assert caught.value.status_code == 404


def test_server_errors_carry_their_status() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(500, text="boom")

    with pytest.raises(KmsError) as caught:
        transport_for(handler).request("POST", "/api/v1/kms/keys")
    assert caught.value.status_code == 500
