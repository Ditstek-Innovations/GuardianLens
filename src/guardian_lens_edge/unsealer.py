"""Camera credential unsealing — the edge half of BR-S-03 / TRD 12.4.

The control plane stores and ships AES-256-GCM ciphertext it cannot read
(``guardian_lens.services.sealer.AesGcmCredentialSealer``); the key lives
only at the edge. This module mirrors that sealer's format exactly:

    base64( nonce[12] || AESGCM(key).encrypt(nonce, url_utf8, aad=None) )

with the 16-byte GCM tag appended by AESGCM itself. There is no prefix and
no associated data. The format is asserted by a cross-plane round-trip test
(tests/edge/test_unsealer.py) which imports the control-plane sealer IN THE
TEST ONLY — this package must never import ``guardian_lens.*``, because a
site deployment does not ship the control plane.

The dev-placeholder format (``gl-dev-sealed:v1:`` + salt + BLAKE2 digest)
is NOT ciphertext and cannot be decrypted by anyone; it is produced when the
control plane runs without GL_CAMERA_KEY. Its prefix is detected here and
reported as exactly that, so the operator fixes the control plane instead of
chasing a key mismatch.

DATABASE.md 11.5: the unsealed URL is held in process memory only. It is
never logged, never persisted, and every object carrying it redacts it from
``repr``/``str``.
"""

from __future__ import annotations

import base64

__all__ = [
    "CAMERA_KEY_ENV",
    "CAMERA_KEY_ID_ENV",
    "CredentialUnsealError",
    "CredentialKeyIdMismatchError",
    "CredentialUnsealer",
    "PlaceholderSealedError",
    "UnsealedStreamUrl",
]

#: Environment variables read ONLY at composition (agent ``main``): the key
#: is injected into the constructor as bytes, never re-read from here.
CAMERA_KEY_ENV = "GL_CAMERA_KEY"
CAMERA_KEY_ID_ENV = "GL_CAMERA_KEY_ID"

#: Prefix of the control plane's ``sealer.PLACEHOLDER_PREFIX``
#: (``gl-dev-sealed:v1:``). Deliberately version-agnostic — any
#: ``gl-dev-sealed:`` value is a placeholder, whatever its version — and
#: kept as a literal, not an import: see the module docstring.
_PLACEHOLDER_PREFIX = b"gl-dev-sealed:"

_NONCE_LENGTH = 12
_TAG_LENGTH = 16


class CredentialUnsealError(Exception):
    """A sealed camera credential could not be unsealed."""


class CredentialKeyIdMismatchError(CredentialUnsealError):
    """The credential was sealed under a different key id.

    This is the rotation surface: the message names both ids so an operator
    can see immediately whether the edge key or the control-plane sealing
    is behind.
    """

    def __init__(self, sealed_key_id: str, held_key_id: str) -> None:
        self.sealed_key_id = sealed_key_id
        self.held_key_id = held_key_id
        super().__init__(
            f"credential sealed under key id '{sealed_key_id}' but this "
            f"agent holds key id '{held_key_id}'; the camera credential "
            "must be re-sealed or the edge key rotated to match"
        )


class PlaceholderSealedError(CredentialUnsealError):
    """The control plane sealed with the dev placeholder, not encryption."""

    def __init__(self) -> None:
        super().__init__(
            "credential carries the dev placeholder marker "
            "('gl-dev-sealed:'): the control plane sealed it without real "
            "key material (GL_CAMERA_KEY unset there). A placeholder is a "
            "salted digest, not ciphertext — no key can recover the URL. "
            "Set GL_CAMERA_KEY at the control plane and re-save the camera."
        )


class UnsealedStreamUrl:
    """An RTSP URL held in memory only (DATABASE.md 11.5).

    ``repr``/``str`` redact the value; retrieval is an explicit ``reveal()``
    call so no formatting path — logging, f-strings, tracebacks over locals
    rendered with repr — can leak the credential embedded in the URL.
    """

    __slots__ = ("_value",)

    def __init__(self, value: str) -> None:
        self._value = value

    def reveal(self) -> str:
        """The plaintext URL. Pass it to the capture layer; never log it."""
        return self._value

    def __repr__(self) -> str:
        return "UnsealedStreamUrl(<redacted>)"

    def __str__(self) -> str:
        return "<redacted stream url>"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, UnsealedStreamUrl):
            return self._value == other._value
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._value)


class CredentialUnsealer:
    """Decrypts camera credentials sealed by the control plane.

    ``key`` is injected as bytes: the environment (GL_CAMERA_KEY, 32-byte
    hex) is read exactly once, at composition, by the caller — this class
    never touches ``os.environ``, so tests and rotation tooling control key
    material explicitly.
    """

    def __init__(self, key: bytes, key_id: str) -> None:
        if len(key) != 32:
            raise ValueError(
                "camera key must be exactly 32 bytes (AES-256); got "
                f"{len(key)} bytes — check GL_CAMERA_KEY is 64 hex chars"
            )
        if not key_id:
            raise ValueError("key_id must be non-empty")
        self._key = key
        self._key_id = key_id

    @property
    def key_id(self) -> str:
        return self._key_id

    def unseal(self, sealed_b64: str, sealed_key_id: str) -> UnsealedStreamUrl:
        """Base64 ciphertext from the config document → in-memory URL.

        Raises :class:`CredentialKeyIdMismatchError`,
        :class:`PlaceholderSealedError` or :class:`CredentialUnsealError`;
        none of the messages can contain URL or key material.
        """
        try:
            sealed = base64.b64decode(sealed_b64, validate=True)
        except ValueError as exc:  # binascii.Error subclasses ValueError
            raise CredentialUnsealError(
                f"sealed credential is not valid base64: {exc}"
            ) from exc
        if sealed.startswith(_PLACEHOLDER_PREFIX):
            raise PlaceholderSealedError()
        if sealed_key_id != self._key_id:
            raise CredentialKeyIdMismatchError(sealed_key_id, self._key_id)
        if len(sealed) < _NONCE_LENGTH + _TAG_LENGTH:
            raise CredentialUnsealError(
                f"sealed credential too short to be nonce+ciphertext+tag "
                f"({len(sealed)} bytes); the stored value is corrupt"
            )
        # Lazy import mirrors the sealer: the synthetic path runs with zero
        # crypto/vision dependencies (TRD 13.2).
        try:
            from cryptography.exceptions import InvalidTag
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        except ImportError as exc:  # pragma: no cover - installed in dev
            raise CredentialUnsealError(
                "the 'cryptography' package is required to unseal camera "
                "credentials and is not installed"
            ) from exc
        nonce = sealed[:_NONCE_LENGTH]
        ciphertext = sealed[_NONCE_LENGTH:]
        try:
            plaintext = AESGCM(self._key).decrypt(nonce, ciphertext, None)
        except InvalidTag as exc:
            raise CredentialUnsealError(
                f"decryption failed under key id '{self._key_id}': wrong "
                "key material or corrupted ciphertext"
            ) from exc
        return UnsealedStreamUrl(plaintext.decode("utf-8"))

    def __repr__(self) -> str:
        # Key id only — never key bytes.
        return f"CredentialUnsealer(key_id={self._key_id!r})"
