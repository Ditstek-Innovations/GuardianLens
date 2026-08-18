"""UUIDv7 generator — RFC 9562 conformance the stdlib cannot provide on 3.11."""

from __future__ import annotations

import uuid

import pytest

from guardian_lens_edge.uuid7 import generate_uuid7, uuid7_unix_ms


def test_version_bits_are_7() -> None:
    value = generate_uuid7()
    assert value.version == 7


def test_variant_is_rfc_4122() -> None:
    value = generate_uuid7()
    assert value.variant == uuid.RFC_4122


def test_embedded_timestamp_round_trips() -> None:
    value = generate_uuid7(unix_ts_ms=1_755_000_000_123)
    assert uuid7_unix_ms(value) == 1_755_000_000_123


def test_time_ordering_across_milliseconds() -> None:
    base_ms = 1_755_000_000_000
    values = [generate_uuid7(unix_ts_ms=base_ms + offset) for offset in range(64)]
    as_strings = [str(value) for value in values]
    assert as_strings == sorted(as_strings)
    as_ints = [value.int for value in values]
    assert as_ints == sorted(as_ints)


def test_uniqueness_within_one_millisecond() -> None:
    values = {generate_uuid7(unix_ts_ms=1) for _ in range(256)}
    assert len(values) == 256


def test_timestamp_out_of_range_rejected() -> None:
    with pytest.raises(ValueError):
        generate_uuid7(unix_ts_ms=1 << 48)
    with pytest.raises(ValueError):
        generate_uuid7(unix_ts_ms=-1)


def test_extractor_rejects_non_v7() -> None:
    with pytest.raises(ValueError):
        uuid7_unix_ms(uuid.uuid4())
