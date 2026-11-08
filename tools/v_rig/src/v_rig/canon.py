# SPDX-License-Identifier: MPL-2.0
"""The canonicalisation rules of the v-rig module's README, section 9, versioned v1. Every digest and identifier the
tool writes comes from here, so a consumer can recompute and check them."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import unicodedata
from decimal import Decimal
from urllib.parse import quote

VERSION = "v1"
URN = f"urn:lattice-v-rig:{VERSION}:"

_WS = re.compile(r"\s+")


def normalise_text(text: str) -> str:
    """NFC, one line feed per line ending, each run of whitespace one space, trimmed."""
    text = unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))
    return _WS.sub(" ", text).strip()


def normalise_file(text: str) -> str:
    """A file normalised line by line, runs of blank lines kept as one, no leading or trailing blank line."""
    text = unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))
    lines: list[str] = []
    for raw in text.split("\n"):
        line = _WS.sub(" ", raw).strip()
        if line or (lines and lines[-1]):
            lines.append(line)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def sha256_hex(text: str | bytes) -> str:
    data = text.encode("utf-8") if isinstance(text, str) else text
    return hashlib.sha256(data).hexdigest()


def _json_default(value):
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"cannot render {type(value).__name__} as JSON")


def json_canonical(value) -> str:
    """JSON with keys sorted and no insignificant whitespace, dates as ISO strings."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=_json_default)


def fact_digest(key: str, value=None, *, unknown: bool = False, empty: bool = False) -> str:
    """Over the key, `=`, and the value as canonical JSON, `?` for the unknown marker, `[]` for the empty marker."""
    rendered = "?" if unknown else "[]" if empty else json_canonical(value)
    return sha256_hex(f"{key}={rendered}")


def mapping_digest(mapping: dict) -> str:
    """Over the canonical JSON of a mapping with its provenance key removed."""
    return sha256_hex(json_canonical({k: v for k, v in mapping.items() if k != "provenance"}))


def percent(value: str) -> str:
    return quote(value, safe="-._~")


def view_name(view: str, rendering: str | None = None) -> str:
    """`declared`, `blind` or `rendering:<name>`."""
    if view == "rendering":
        if not rendering:
            raise ValueError("a rendering view needs a rendering name")
        return f"rendering:{rendering}"
    if view not in ("declared", "blind"):
        raise ValueError(f"unknown view {view!r}")
    return view


def locator_string(document_id: str, view: str, *, section: str | None = None, clause: str | None = None,
                   row: str | None = None, key_path: str | None = None) -> str:
    """Document id, `@`, the view's name, then `/field=value` for each present field in order."""
    parts = [f"{percent(document_id)}@{percent(view)}"]
    for name, value in (("section", section), ("clause", clause), ("row", row), ("key-path", key_path)):
        if value is not None:
            parts.append(f"{name}={percent(str(value))}")
    return "/".join(parts)


def node_iri(locator: str) -> str:
    return f"{URN}node:{locator}"


def locator_iri(locator: str) -> str:
    return f"{URN}locator:{locator}"


def view_iri(document_id: str, rendering: str) -> str:
    return f"{URN}view:{percent(document_id)}:{percent(rendering)}"


def run_iri(rig_digest: str) -> str:
    return f"{URN}run:{rig_digest}"


def tuple_encode(parts: list[str]) -> bytes:
    """The identity minting specification's `length-prefixed-utf8/1`: each part as its UTF-8 byte count in decimal,
    `:`, then its bytes."""
    out = bytearray()
    for part in parts:
        data = part.encode("utf-8")
        out += f"{len(data)}:".encode("ascii") + data
    return bytes(out)


def finding_iri(kind: str, document_id: str, locator: str, key: str | None) -> str:
    """Over the tuple of the kind's local name, the document id, the locator's canonical string and the key or
    the empty string."""
    return f"{URN}finding:{sha256_hex(tuple_encode([kind, document_id, locator, key or '']))}"
