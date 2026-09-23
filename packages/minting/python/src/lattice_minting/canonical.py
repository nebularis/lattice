# SPDX-License-Identifier: MPL-2.0
"""Byte-level building blocks (identity-minting-specification.md §2.1, §4, §6)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json


def canonical_json(obj) -> bytes:
    """RFC 8785 for recipes: ASCII keys, no non-integer numbers (§2.1)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def tuple_bytes(components: list[str]) -> bytes:
    """length-prefixed-utf8/1: UTF-8 byte count, ':', bytes, per component (§4.1)."""
    out = bytearray()
    for c in components:
        b = c.encode("utf-8")
        out += str(len(b)).encode("ascii") + b":" + b
    return bytes(out)


def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def hmac_sha256(key: bytes, data: bytes) -> bytes:
    return hmac.new(key, data, hashlib.sha256).digest()


def encode(data: bytes, encoding: str) -> str:
    """§4.3: lowercase hex, RFC 4648 base32 (uppercase) or base64url, unpadded."""
    if encoding == "lowercase-hex":
        return data.hex()
    if encoding == "base32":
        return base64.b32encode(data).decode("ascii").rstrip("=")
    if encoding == "base64url":
        return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")
    raise ValueError(f"unknown encoding {encoding!r}")


_UNRESERVED = frozenset(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~")


def percent_encode(value: str) -> str:
    """§6.2: unreserved bytes kept, every other byte %XX in uppercase hex."""
    return "".join(chr(b) if b in _UNRESERVED else f"%{b:02X}" for b in value.encode("utf-8"))


def uuid4_from(random16: bytes) -> str:
    """A version 4 UUID from 16 random bytes (RFC 9562), lowercase 8-4-4-4-12 (§6.3)."""
    if len(random16) != 16:
        raise ValueError("a UUIDv4 needs exactly 16 random bytes")
    b = bytearray(random16)
    b[6] = (b[6] & 0x0F) | 0x40
    b[8] = (b[8] & 0x3F) | 0x80
    h = b.hex()
    return f"{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"
