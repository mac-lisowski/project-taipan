"""Circuit breaker over the Cipher port. Fail fast while the KMS is down."""

import threading
import time
from collections.abc import Callable
from typing import Any

from kms import KmsError
from kms.ports import Cipher

from crypto.errors import CryptoCategory, CryptoError


class BreakerCipher:
    """A Cipher that opens after N consecutive KMS failures.

    Closed calls pass through and count consecutive `KmsError`s.
    Open calls raise `kms_unavailable` without touching the wrapped
    cipher. After the cooldown one probe call goes through: success
    closes, `KmsError` re-opens. Other exceptions propagate and
    never move the state machine.
    """

    def __init__(
        self,
        cipher: Cipher,
        threshold: int = 3,
        cooldown_seconds: float = 30.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if threshold < 1:
            raise ValueError("threshold must be at least 1")
        if cooldown_seconds <= 0:
            raise ValueError("cooldown_seconds must be positive")
        self._cipher = cipher
        self._threshold = threshold
        self._cooldown = cooldown_seconds
        self._clock = clock
        self._lock = threading.Lock()
        self._failures = 0
        self._opened_at = 0.0
        self._open = False
        self._probing = False

    @property
    def wrapped(self) -> Cipher:
        return self._cipher

    @property
    def threshold(self) -> int:
        return self._threshold

    @property
    def cooldown_seconds(self) -> float:
        return self._cooldown

    def encrypt(self, key_id: str, data: bytes) -> str:
        return self._call(self._cipher.encrypt, key_id, data)

    def decrypt(self, key_id: str, ciphertext: str) -> bytes:
        return self._call(self._cipher.decrypt, key_id, ciphertext)

    def _call(self, method: Callable[..., Any], *args: Any) -> Any:
        with self._lock:
            if self._open and not self._admit_probe_locked():
                raise CryptoError(CryptoCategory.KMS_UNAVAILABLE, "key service unavailable")
            probe = self._open
        try:
            result = method(*args)
        except KmsError:
            with self._lock:
                self._on_kms_failure_locked(probe)
            raise
        except BaseException:
            with self._lock:
                self._probing = False
            raise
        with self._lock:
            self._failures = 0
            self._open = False
            self._probing = False
        return result

    def _admit_probe_locked(self) -> bool:
        # Cooldown over and no probe in flight: this call is the probe.
        if self._clock() - self._opened_at < self._cooldown or self._probing:
            return False
        self._probing = True
        return True

    def _on_kms_failure_locked(self, probe: bool) -> None:
        if probe:
            self._opened_at = self._clock()
            self._probing = False
            return
        self._failures += 1
        if self._failures >= self._threshold:
            self._open = True
            self._opened_at = self._clock()
