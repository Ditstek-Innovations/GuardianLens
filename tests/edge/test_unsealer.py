"""Credential unsealing — the edge half of BR-S-03 (TRD 12.4).

The round-trip tests import the CONTROL-PLANE sealer deliberately and only
here: the two implementations must agree byte-for-byte on the sealed
format, and the test is the contract. The edge package itself must never
import ``guardian_lens.*`` (a site deployment does not ship the control
plane) — asserted statically at the bottom of this file.
"""

from __future__ import annotations

import base64
import re
from pathlib import Path

import pytest

# Control-plane import: TEST ONLY (see module docstring).
from guardian_lens.services.sealer import (
    AesGcmCredentialSealer,
    PlaceholderCredentialSealer,
)
from guardian_lens_edge.unsealer import (
    CredentialKeyIdMismatchError,
    CredentialUnsealError,
    CredentialUnsealer,
    PlaceholderSealedError,
    UnsealedStreamUrl,
)

KEY_HEX = "aa" * 32
KEY_ID = "site-key-2026-08"
STREAM_URL = "rtsp://operator:s3cret-cam-pw@10.0.40.17:554/stream1"


def make_unsealer(
    key_hex: str = KEY_HEX, key_id: str = KEY_ID
) -> CredentialUnsealer:
    return CredentialUnsealer(bytes.fromhex(key_hex), key_id)


def seal_for_document(plaintext: str) -> str:
    """Seal exactly as the control plane does, base64 as the config
    document carries it (repositories/config.agent_config_document)."""
    sealed = AesGcmCredentialSealer(KEY_HEX, KEY_ID).seal(plaintext)
    return base64.b64encode(sealed).decode()


# ---------------------------------------------------------------------------
# Cross-plane round trip
# ---------------------------------------------------------------------------


def test_round_trip_with_control_plane_sealer() -> None:
    sealed_b64 = seal_for_document(STREAM_URL)
    url = make_unsealer().unseal(sealed_b64, KEY_ID)
    assert url.reveal() == STREAM_URL


def test_round_trip_is_nonce_randomised_but_stable() -> None:
    first = seal_for_document(STREAM_URL)
    second = seal_for_document(STREAM_URL)
    assert first != second  # fresh 96-bit nonce per seal
    unsealer = make_unsealer()
    assert unsealer.unseal(first, KEY_ID).reveal() == STREAM_URL
    assert unsealer.unseal(second, KEY_ID).reveal() == STREAM_URL


# ---------------------------------------------------------------------------
# Failure surfaces
# ---------------------------------------------------------------------------


def test_wrong_key_id_names_both_ids() -> None:
    sealed_b64 = seal_for_document(STREAM_URL)
    with pytest.raises(CredentialKeyIdMismatchError) as excinfo:
        make_unsealer(key_id="site-key-2027-01").unseal(sealed_b64, KEY_ID)
    message = str(excinfo.value)
    assert KEY_ID in message
    assert "site-key-2027-01" in message


def test_placeholder_sealed_value_is_reported_as_such() -> None:
    sealed = PlaceholderCredentialSealer(KEY_ID).seal(STREAM_URL)
    sealed_b64 = base64.b64encode(sealed).decode()
    with pytest.raises(PlaceholderSealedError) as excinfo:
        make_unsealer().unseal(sealed_b64, KEY_ID)
    message = str(excinfo.value)
    # The operator must learn the control plane sealed without key
    # material — not chase a phantom key mismatch.
    assert "control plane" in message
    assert "GL_CAMERA_KEY" in message


def test_placeholder_detected_before_key_id_comparison() -> None:
    sealed = PlaceholderCredentialSealer("some-other-id").seal(STREAM_URL)
    sealed_b64 = base64.b64encode(sealed).decode()
    with pytest.raises(PlaceholderSealedError):
        make_unsealer().unseal(sealed_b64, "some-other-id")


def test_wrong_key_material_fails_closed() -> None:
    sealed_b64 = seal_for_document(STREAM_URL)
    with pytest.raises(CredentialUnsealError) as excinfo:
        make_unsealer(key_hex="bb" * 32).unseal(sealed_b64, KEY_ID)
    assert STREAM_URL not in str(excinfo.value)


def test_corrupted_ciphertext_fails_closed() -> None:
    raw = bytearray(base64.b64decode(seal_for_document(STREAM_URL)))
    raw[-1] ^= 0xFF
    with pytest.raises(CredentialUnsealError):
        make_unsealer().unseal(base64.b64encode(bytes(raw)).decode(), KEY_ID)


def test_invalid_base64_and_truncated_values_fail_closed() -> None:
    unsealer = make_unsealer()
    with pytest.raises(CredentialUnsealError):
        unsealer.unseal("not//valid==base64!!", KEY_ID)
    with pytest.raises(CredentialUnsealError):
        unsealer.unseal(base64.b64encode(b"short").decode(), KEY_ID)


def test_key_must_be_exactly_32_bytes() -> None:
    with pytest.raises(ValueError):
        CredentialUnsealer(b"\xaa" * 16, KEY_ID)
    with pytest.raises(ValueError):
        CredentialUnsealer(b"", KEY_ID)


# ---------------------------------------------------------------------------
# Redaction — DATABASE.md 11.5: the URL lives in memory only
# ---------------------------------------------------------------------------


def test_unsealed_url_redacts_repr_and_str() -> None:
    url = UnsealedStreamUrl(STREAM_URL)
    assert STREAM_URL not in repr(url)
    assert STREAM_URL not in str(url)
    assert "s3cret-cam-pw" not in repr(url)
    assert "s3cret-cam-pw" not in str(url)
    assert url.reveal() == STREAM_URL


def test_unsealer_repr_shows_key_id_never_key_bytes() -> None:
    unsealer = make_unsealer()
    rendered = repr(unsealer)
    assert KEY_ID in rendered
    assert KEY_HEX not in rendered


def test_rtsp_source_repr_redacts_the_url() -> None:
    from guardian_lens_edge.rtsp import RtspSource

    class _NullListener:
        def stream_connected(self, camera_id, at): ...

        def stream_lost(self, camera_id, at): ...

        def stream_restored(self, camera_id, at): ...

        def stream_degraded(self, camera_id, at): ...

    source = RtspSource(
        "cam-1",
        UnsealedStreamUrl(STREAM_URL),
        sample_rate_fps=2.0,
        decode_failure_threshold=5,
        listener=_NullListener(),
    )
    rendered = repr(source)
    assert STREAM_URL not in rendered
    assert "s3cret-cam-pw" not in rendered


# ---------------------------------------------------------------------------
# The edge package never imports control-plane code
# ---------------------------------------------------------------------------

EDGE_PACKAGE_DIR = (
    Path(__file__).resolve().parents[2] / "src" / "guardian_lens_edge"
)

# `guardian_lens` not followed by `_edge`: `import guardian_lens_edge...`
# is the package importing itself and is fine.
_CONTROL_PLANE_IMPORT = re.compile(
    r"^\s*(?:from|import)\s+guardian_lens(?!_edge)\b", re.MULTILINE
)


def test_no_control_plane_import_anywhere_in_the_edge_package() -> None:
    """A site deployment ships guardian_lens_edge WITHOUT guardian_lens.

    Any `import guardian_lens...` in the edge package would make the agent
    unimportable at a real site. The sealed-format contract is instead
    asserted by the round-trip tests above, which live on the test side.
    """
    offenders: list[str] = []
    for module_path in sorted(EDGE_PACKAGE_DIR.rglob("*.py")):
        source_text = module_path.read_text(encoding="utf-8")
        for match in _CONTROL_PLANE_IMPORT.finditer(source_text):
            line_number = source_text.count("\n", 0, match.start()) + 1
            offenders.append(
                f"{module_path.name}:{line_number}: {match.group(0).strip()}"
            )
    assert offenders == [], (
        "guardian_lens_edge must never import control-plane code: "
        f"{offenders}"
    )
