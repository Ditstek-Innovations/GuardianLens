"""Camera credential sealing — BR-S-03, TRD 12.4.

cameras.stream_url_encrypted holds AES-256-GCM ciphertext of the RTSP URL.
The plaintext NEVER persists, never appears in a response schema and never
appears in a log line; the decryption key lives at the edge and the
control plane stores a credential it cannot read.

Two implementations behind one interface:

  * AesGcmCredentialSealer — the real thing, used when the `cryptography`
    package is importable and GL_CAMERA_KEY is set.
  * PlaceholderCredentialSealer — dev fallback for environments without
    `cryptography`. It stores a clearly marked, prefix-tagged BLAKE2 digest
    of the plaintext: not decryptable by anyone, but visibly NOT plaintext
    and NOT real ciphertext. Any consumer can detect the marker. This is a
    recorded gap, not a hidden one.
"""

from __future__ import annotations

import hashlib
import os
from abc import ABC, abstractmethod

__all__ = [
    "CredentialSealer",
    "AesGcmCredentialSealer",
    "PlaceholderCredentialSealer",
    "build_sealer",
]

#: Marks a placeholder-sealed value. Kept stable so tooling can find every
#: camera that needs re-sealing once real key material is configured.
PLACEHOLDER_PREFIX = b"gl-dev-sealed:v1:"


class CredentialSealer(ABC):
    key_id: str

    @abstractmethod
    def seal(self, plaintext: str) -> bytes:
        """Plaintext in, opaque bytes out. The plaintext must not be
        recoverable from the return value without key material that this
        process does not necessarily hold."""


class AesGcmCredentialSealer(CredentialSealer):
    """AES-256-GCM, 96-bit random nonce prepended to the ciphertext."""

    def __init__(self, key_hex: str, key_id: str) -> None:
        key = bytes.fromhex(key_hex)
        if len(key) != 32:
            raise ValueError("GL_CAMERA_KEY must be 32 bytes of hex (AES-256)")
        self._key = key
        self.key_id = key_id

    def seal(self, plaintext: str) -> bytes:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        nonce = os.urandom(12)
        ciphertext = AESGCM(self._key).encrypt(nonce, plaintext.encode(), None)
        return nonce + ciphertext


class PlaceholderCredentialSealer(CredentialSealer):
    """Not encryption — a salted digest with an explicit marker.

    Chosen over storing nothing so the NOT NULL column and the full
    configuration flow are exercised, and over reversible obfuscation so
    no one can mistake it for protection worth shipping. The URL cannot be
    recovered, which is acceptable at dev: the edge agent receives its
    config from a dev fixture, not from this column.
    """

    def __init__(self, key_id: str) -> None:
        self.key_id = key_id

    def seal(self, plaintext: str) -> bytes:
        salt = os.urandom(16)
        digest = hashlib.blake2b(salt + plaintext.encode(), digest_size=32).digest()
        return PLACEHOLDER_PREFIX + salt + digest


def build_sealer(camera_key_hex: str | None, key_id: str) -> CredentialSealer:
    """Pick the strongest sealer the environment supports. Never plaintext."""
    if camera_key_hex:
        try:
            import cryptography  # noqa: F401 — availability probe only

            return AesGcmCredentialSealer(camera_key_hex, key_id)
        except ImportError:
            pass
    return PlaceholderCredentialSealer(key_id)
