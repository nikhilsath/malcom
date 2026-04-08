from __future__ import annotations
import base64
import binascii
import hashlib
import hmac
import os
import secrets
from typing import Any

CONNECTOR_PROTECTION_VERSION = "enc_v1"
CONNECTOR_NONCE_BYTES = 16
CONNECTOR_SIGNATURE_BYTES = 32


def get_connector_protection_secret(*, root_dir: str | None = None, db_path: str | None = None) -> str:
    configured = os.environ.get("MALCOM_CONNECTOR_SECRET")
    if configured:
        return configured

    seed_parts = [str(root_dir or ""), str(db_path or ""), "malcom-connectors"]
    return "|".join(seed_parts)


def derive_connector_protection_key(protection_secret: str) -> bytes:
    return hashlib.sha256(protection_secret.encode("utf-8")).digest()


def _xor_bytes(left: bytes, right: bytes) -> bytes:
    return bytes(left_byte ^ right_byte for left_byte, right_byte in zip(left, right))


def build_connector_keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    output = bytearray()
    counter = 0

    while len(output) < length:
        block = hashlib.sha256(key + nonce + counter.to_bytes(4, "big")).digest()
        output.extend(block)
        counter += 1

    return bytes(output[:length])


def _encode_protected_connector_value(nonce: bytes, signature: bytes, ciphertext: bytes) -> str:
    token = base64.urlsafe_b64encode(nonce + signature + ciphertext).decode("ascii")
    return f"{CONNECTOR_PROTECTION_VERSION}:{token}"


def _decode_protected_connector_value(value: str | None) -> tuple[bytes, bytes, bytes] | None:
    if not value or not value.startswith(f"{CONNECTOR_PROTECTION_VERSION}:"):
        return None

    encoded = value.split(":", 1)[1]
    try:
        raw = base64.urlsafe_b64decode(encoded.encode("ascii"))
    except (ValueError, binascii.Error):
        return None

    minimum_size = CONNECTOR_NONCE_BYTES + CONNECTOR_SIGNATURE_BYTES
    if len(raw) < minimum_size:
        return None

    nonce = raw[:CONNECTOR_NONCE_BYTES]
    signature_end = CONNECTOR_NONCE_BYTES + CONNECTOR_SIGNATURE_BYTES
    signature = raw[CONNECTOR_NONCE_BYTES:signature_end]
    ciphertext = raw[signature_end:]
    return nonce, signature, ciphertext


def protect_connector_secret_value(value: str, protection_secret: str) -> str:
    key = derive_connector_protection_key(protection_secret)
    nonce = secrets.token_bytes(CONNECTOR_NONCE_BYTES)
    payload = value.encode("utf-8")
    keystream = build_connector_keystream(key, nonce, len(payload))
    ciphertext = _xor_bytes(payload, keystream)
    signature = hmac.new(key, nonce + ciphertext, hashlib.sha256).digest()
    return _encode_protected_connector_value(nonce, signature, ciphertext)


def unprotect_connector_secret_value(value: str | None, protection_secret: str) -> str | None:
    decoded = _decode_protected_connector_value(value)
    if decoded is None:
        return None

    nonce, signature, ciphertext = decoded
    key = derive_connector_protection_key(protection_secret)
    expected_signature = hmac.new(key, nonce + ciphertext, hashlib.sha256).digest()

    if not hmac.compare_digest(signature, expected_signature):
        return None

    keystream = build_connector_keystream(key, nonce, len(ciphertext))
    try:
        plaintext = _xor_bytes(ciphertext, keystream)
        return plaintext.decode("utf-8")
    except UnicodeDecodeError:
        return None


def mask_connector_secret(value: str | None) -> str | None:
    if not value:
        return None

    if len(value) <= 8:
        return "••••"

    return f"{value[:4]}••••{value[-4:]}"
