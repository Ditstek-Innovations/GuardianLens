"""RFC-9562 UUIDv7 generation.

The runtime venv is Python 3.14, which ships ``uuid.uuid7()``, but this
codebase must remain importable on Python 3.11 (``requires-python >=3.11``),
so the function is implemented here: 48-bit Unix timestamp in milliseconds,
version and variant bits per RFC 9562 section 5.7, and 74 random bits from a
cryptographic source.

Event identifiers are UUIDv7 so that outbox drain order and identifier order
agree across a restart (DATABASE.md 3.4, ADR-014).
"""

from __future__ import annotations

import secrets
import time
import uuid

__all__ = ["generate_uuid7", "uuid7_unix_ms"]

_UNIX_TS_MS_BITS = 48
_VERSION = 7


def generate_uuid7(unix_ts_ms: int | None = None) -> uuid.UUID:
    """Return a UUIDv7 for the given millisecond timestamp.

    ``unix_ts_ms`` is injectable so callers that already hold an
    authoritative edge-clock reading (ADR-007) can stamp identifiers from it,
    and so tests can assert time-ordering deterministically.
    """
    if unix_ts_ms is None:
        unix_ts_ms = time.time_ns() // 1_000_000
    if unix_ts_ms < 0 or unix_ts_ms >= (1 << _UNIX_TS_MS_BITS):
        raise ValueError(f"timestamp out of UUIDv7 range: {unix_ts_ms}")

    # Layout (RFC 9562 5.7): unix_ts_ms(48) | ver(4) | rand_a(12) |
    # var(2) | rand_b(62)
    rand_a = secrets.randbits(12)
    rand_b = secrets.randbits(62)
    value = (
        (unix_ts_ms << 80)
        | (_VERSION << 76)
        | (rand_a << 64)
        | (0b10 << 62)
        | rand_b
    )
    return uuid.UUID(int=value)


def uuid7_unix_ms(value: uuid.UUID) -> int:
    """Extract the millisecond timestamp embedded in a UUIDv7."""
    if value.version != _VERSION:
        raise ValueError(f"not a UUIDv7: {value}")
    return value.int >> 80
