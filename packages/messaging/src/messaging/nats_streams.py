"""NATS stream operations for the broker: declare, drop, and replay.

The JetStream side of the adapter lives here, off the core link file,
so both stay under the repo size cap.
"""

import contextlib
import json
from collections.abc import AsyncIterator

from nats.errors import Error as NatsError
from nats.errors import TimeoutError as NatsTimeoutError
from nats.js.api import DeliverPolicy, RetentionPolicy, StreamConfig
from nats.js.errors import NotFoundError as JsNotFoundError

from messaging.seam import RETENTIONS, Message, MessagingError

# Retention policy per stream: the per-domain rule, not a global one.
_RETENTION = {
    "limits": RetentionPolicy.LIMITS,
    "interest": RetentionPolicy.INTEREST,
    "workqueue": RetentionPolicy.WORK_QUEUE,
}
# One vocabulary: seam owns the names; this map must mirror exactly those.
assert tuple(_RETENTION) == RETENTIONS

# Seconds of silence on a replay subject that ends the backlog read.
_REPLAY_QUIET = 0.5


class StreamOps:
    """Stream capability mixed into NatsBroker, which owns the link."""

    async def ensure_stream(
        self,
        name: str,
        subjects: list[str],
        retention: str = "limits",
    ) -> None:
        """Create the stream with the configured storage if it is missing."""
        policy = _RETENTION.get(retention)
        if policy is None:
            # Loud before any network use: a bad retention is a code bug.
            raise ValueError(f"retention must be one of {', '.join(RETENTIONS)}")
        try:
            await (await self._jetstream()).stream_info(name)
        except JsNotFoundError:
            config = StreamConfig(
                name=name,
                subjects=subjects,
                storage=self._storage,
                retention=policy,
            )
            try:
                await (await self._jetstream()).add_stream(config)
            except (NatsError, OSError) as err:
                await self._drop()
                raise MessagingError(f"stream {name} create failed: {err}") from err
        except (NatsError, OSError) as err:
            await self._drop()
            raise MessagingError(f"stream {name} lookup failed: {err}") from err

    async def drop_stream(self, name: str) -> None:
        """Delete the stream and its stored messages."""
        try:
            await (await self._jetstream()).delete_stream(name)
        except JsNotFoundError:
            return
        except (NatsError, OSError) as err:
            await self._drop()
            raise MessagingError(f"stream {name} delete failed: {err}") from err

    async def replay(self, stream: str, pattern: str) -> AsyncIterator[Message]:
        """Yield the stream's retained events for a subject filter.

        The ordered consumer is the one-off replay tool: ephemeral, ack
        free, and it recovers from gaps, so a replay never stores state
        on the broker. Iteration ends when the subject stays quiet.
        """
        js = await self._jetstream()
        try:
            sub = await js.subscribe(
                pattern,
                stream=stream,
                ordered_consumer=True,
                deliver_policy=DeliverPolicy.ALL,
            )
        except (NatsError, OSError) as err:
            await self._drop()
            raise MessagingError(f"replay of {stream} on {pattern} failed: {err}") from err
        try:
            while True:
                try:
                    raw = await sub.next_msg(timeout=_REPLAY_QUIET)
                except NatsTimeoutError:
                    return
                except (NatsError, OSError) as err:
                    await self._drop()
                    raise MessagingError(f"replay of {stream} on {pattern} failed: {err}") from err
                yield Message(
                    subject=raw.subject,
                    payload=json.loads(raw.data),
                )
        finally:
            # A broken-off reader must not leave the ephemeral consumer.
            with contextlib.suppress(Exception):
                await sub.unsubscribe()
