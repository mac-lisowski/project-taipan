"""BreakerCipher unit tests. Fake clock, no sleeps, no threads, no live KMS."""

from crypto.breaker import BreakerCipher
from crypto.errors import CryptoCategory, CryptoError
from kms import KmsError


class ScriptCipher:
    """Cipher with scripted outcomes; counts calls per method."""

    def __init__(self) -> None:
        self.encrypt_calls = 0
        self.decrypt_calls = 0
        self.outcomes: list = []

    def encrypt(self, key_id: str, data: bytes) -> str:
        self.encrypt_calls += 1
        return self._next("wrapped")

    def decrypt(self, key_id: str, ciphertext: str) -> bytes:
        self.decrypt_calls += 1
        return self._next(b"plain")

    def _next(self, default):
        if self.outcomes:
            outcome = self.outcomes.pop(0)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome
        return default


class FakeClock:
    def __init__(self) -> None:
        self.now_value = 1000.0

    def now(self) -> float:
        return self.now_value

    def advance(self, seconds: float) -> None:
        self.now_value += seconds


def make_breaker(cipher, threshold=3, cooldown=30.0, clock=None):
    clock = clock or FakeClock()
    return BreakerCipher(cipher, threshold=threshold, cooldown_seconds=cooldown, clock=clock.now)


def expect_error(exc_type, fn, *args):
    try:
        fn(*args)
    except exc_type:
        return
    raise AssertionError(f"expected {exc_type.__name__}")


def test_closed_passes_decrypt_through():
    cipher = ScriptCipher()
    breaker = make_breaker(cipher)
    assert breaker.decrypt("key-1", "ciphertext") == b"plain"
    assert cipher.decrypt_calls == 1


def test_closed_passes_encrypt_through():
    cipher = ScriptCipher()
    assert make_breaker(cipher).encrypt("key-1", b"data") == "wrapped"
    assert cipher.encrypt_calls == 1


def test_kms_failures_below_threshold_propagate():
    cipher = ScriptCipher()
    cipher.outcomes = [KmsError("down"), KmsError("down")]
    breaker = make_breaker(cipher, threshold=3)
    for _ in range(2):
        expect_error(KmsError, breaker.decrypt, "key-1", "ciphertext")
    assert cipher.decrypt_calls == 2


def test_opens_at_threshold_and_fails_fast():
    cipher = ScriptCipher()
    cipher.outcomes = [KmsError("down")] * 3
    breaker = make_breaker(cipher, threshold=3)
    for _ in range(3):
        expect_error(KmsError, breaker.decrypt, "key-1", "ciphertext")
    assert cipher.decrypt_calls == 3
    try:
        breaker.decrypt("key-1", "ciphertext")
    except CryptoError as e:
        assert e.category is CryptoCategory.KMS_UNAVAILABLE
    else:
        raise AssertionError("expected CryptoError")
    assert cipher.decrypt_calls == 3


def open_breaker(threshold=2, cooldown=30.0):
    cipher = ScriptCipher()
    cipher.outcomes = [KmsError("down")] * threshold
    clock = FakeClock()
    breaker = make_breaker(cipher, threshold, cooldown, clock)
    for _ in range(threshold):
        expect_error(KmsError, breaker.decrypt, "key-1", "ciphertext")
    return cipher, clock, breaker


def test_probe_success_closes():
    cipher, clock, breaker = open_breaker()
    calls = cipher.decrypt_calls
    clock.advance(31.0)
    assert breaker.decrypt("key-1", "ciphertext") == b"plain"
    assert cipher.decrypt_calls == calls + 1
    assert breaker.decrypt("key-1", "ciphertext") == b"plain"
    assert cipher.decrypt_calls == calls + 2


def test_probe_failure_reopens():
    cipher, clock, breaker = open_breaker()
    cipher.outcomes = [KmsError("still down")]
    clock.advance(31.0)
    expect_error(KmsError, breaker.decrypt, "key-1", "ciphertext")
    calls = cipher.decrypt_calls
    try:
        breaker.decrypt("key-1", "ciphertext")
    except CryptoError as e:
        assert e.category is CryptoCategory.KMS_UNAVAILABLE
    else:
        raise AssertionError("expected CryptoError")
    assert cipher.decrypt_calls == calls
    clock.advance(29.0)
    try:
        breaker.decrypt("key-1", "ciphertext")
    except CryptoError as e:
        assert e.category is CryptoCategory.KMS_UNAVAILABLE
    else:
        raise AssertionError("expected CryptoError")
    assert cipher.decrypt_calls == calls
    clock.advance(1.0)
    assert breaker.decrypt("key-1", "ciphertext") == b"plain"
    assert cipher.decrypt_calls == calls + 1


def test_success_resets_failure_count():
    cipher = ScriptCipher()
    cipher.outcomes = [KmsError("down"), KmsError("down")]
    breaker = make_breaker(cipher, threshold=3)
    for _ in range(2):
        expect_error(KmsError, breaker.decrypt, "key-1", "ciphertext")
    assert breaker.decrypt("key-1", "ciphertext") == b"plain"
    cipher.outcomes = [KmsError("down"), KmsError("down")]
    for _ in range(2):
        expect_error(KmsError, breaker.decrypt, "key-1", "ciphertext")
    assert breaker.decrypt("key-1", "ciphertext") == b"plain"


def test_non_kms_errors_never_trip():
    cipher = ScriptCipher()
    cipher.outcomes = [ValueError("bad data")] * 5
    breaker = make_breaker(cipher, threshold=3)
    for _ in range(5):
        expect_error(ValueError, breaker.decrypt, "key-1", "ciphertext")
    assert cipher.decrypt_calls == 5


class ReentrantCipher:
    """The first decrypt re-enters the breaker mid-probe.

    Deterministic stand-in for a concurrent second caller while the
    probe is in flight: the nested call must be denied, the outer
    call completes and closes the breaker.
    """

    def __init__(self, fail_first: int) -> None:
        self.decrypt_calls = 0
        self.nested: list = []
        self._fail_first = fail_first
        self.breaker: BreakerCipher | None = None

    def encrypt(self, key_id: str, data: bytes) -> str:
        raise AssertionError("not used")

    def decrypt(self, key_id: str, ciphertext: str) -> bytes:
        self.decrypt_calls += 1
        if self.decrypt_calls <= self._fail_first:
            raise KmsError("down")
        if self.breaker is not None:
            breaker, self.breaker = self.breaker, None  # re-enter once: the probe
            try:
                breaker.decrypt(key_id, ciphertext)
            except CryptoError as e:
                self.nested.append(e.category)
        return b"plain"


def test_cooldown_admits_exactly_one_probe():
    # The probe call re-enters the breaker: the nested call is the
    # "second concurrent caller" and must be denied while probing.
    cipher = ReentrantCipher(fail_first=2)
    clock = FakeClock()
    breaker = make_breaker(cipher, 2, 30.0, clock)
    cipher.breaker = breaker
    for _ in range(2):
        expect_error(KmsError, breaker.decrypt, "key-1", "ciphertext")
    clock.advance(31.0)
    # Probe: outer call admitted, nested one denied, outer closes.
    assert breaker.decrypt("key-1", "ciphertext") == b"plain"
    assert cipher.nested == [CryptoCategory.KMS_UNAVAILABLE]
    # Closed again: the next call goes through the wrapped cipher.
    assert breaker.decrypt("key-1", "ciphertext") == b"plain"
    assert cipher.decrypt_calls == 4


def test_rejects_bad_config():
    cipher = ScriptCipher()
    for kwargs in ({"threshold": 0}, {"cooldown_seconds": 0}):
        try:
            BreakerCipher(cipher, **kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError(f"expected ValueError for {kwargs}")
