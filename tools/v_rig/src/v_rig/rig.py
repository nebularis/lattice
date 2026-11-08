# SPDX-License-Identifier: MPL-2.0
"""Reading a rig in place, read only, from its manifest. The format's layout is the contract: a manifest naming documents
by id, programmes by path and an events file, documents as YAML front matter over Markdown, renderings bound by the
manifest. Files the manifest does not name are never read. The provenance key of a document's front matter is dropped
at the gate and reaches no output."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .canon import normalise_file, sha256_hex

log = logging.getLogger("v_rig")

SUPPORTED_FORMAT_VERSIONS = ("1",)
DROPPED_KEYS = ("provenance",)


class RigError(Exception):
    """A rig the tool refuses, by the key and value that made it."""


@dataclass(frozen=True)
class Rendering:
    name: str
    path: str
    text: str


@dataclass(frozen=True)
class Document:
    id: str
    path: str
    front: dict
    body: str
    body_line: int
    renderings: tuple[Rendering, ...] = ()


@dataclass(frozen=True)
class Programme:
    id: str
    path: str
    mapping: dict


@dataclass(frozen=True)
class Events:
    path: str
    events: tuple[dict, ...]


@dataclass(frozen=True)
class Rig:
    root: Path
    format_version: str
    documents: tuple[Document, ...]
    programmes: tuple[Programme, ...]
    events: Events | None
    file_digests: dict[str, str] = field(default_factory=dict)

    @property
    def digest(self) -> str:
        lines = "\n".join(f"{path}={digest}" for path, digest in sorted(self.file_digests.items()))
        return sha256_hex(lines)

    def document(self, document_id: str) -> Document | None:
        return next((d for d in self.documents if d.id == document_id), None)

    def programme(self, programme_id: str) -> Programme | None:
        return next((p for p in self.programmes if p.id == programme_id), None)


def _read_text(root: Path, relative: str, digests: dict[str, str]) -> str:
    path = root / relative
    if not path.is_file():
        raise RigError(f"the manifest names {relative}, which is not a file of the rig")
    text = path.read_text(encoding="utf-8")
    digests[relative] = sha256_hex(normalise_file(text))
    return text


def _mapping(value, what: str) -> dict:
    if not isinstance(value, dict):
        raise RigError(f"{what} is not a mapping")
    return value


def split_front_matter(text: str) -> tuple[dict, str, int]:
    """The front matter as a mapping, the body, and the body's first line number, one-based."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}, text, 1
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            front = yaml.safe_load("\n".join(lines[1:index])) or {}
            return _mapping(front, "the front matter"), "\n".join(lines[index + 1:]), index + 2
    raise RigError("the front matter is not closed")


def read_rig(root: Path | str) -> Rig:
    root = Path(root).resolve()
    manifest_path = root / "manifest.yaml"
    if not manifest_path.is_file():
        raise RigError(f"no manifest.yaml under {root}")
    digests: dict[str, str] = {}
    manifest = _mapping(yaml.safe_load(_read_text(root, "manifest.yaml", digests)) or {}, "the manifest")
    if "format_version" not in manifest:
        raise RigError("the manifest has no format_version key, and the supported versions are "
                       + ", ".join(SUPPORTED_FORMAT_VERSIONS))
    version = str(manifest["format_version"])
    if version not in SUPPORTED_FORMAT_VERSIONS:
        raise RigError(f"the manifest's format_version is {version}, and the supported versions are "
                       + ", ".join(SUPPORTED_FORMAT_VERSIONS))

    documents: list[Document] = []
    for entry in manifest.get("documents") or []:
        entry = _mapping(entry, "a documents entry")
        document_id = str(entry["id"])
        relative = f"documents/{document_id}.md"
        front, body, body_line = split_front_matter(_read_text(root, relative, digests))
        if str(front.get("id", document_id)) != document_id:
            raise RigError(f"{relative}: the front matter's id is not {document_id}")
        for key in DROPPED_KEYS:
            front.pop(key, None)
        renderings = tuple(
            Rendering(Path(r).stem, r, _read_text(root, r, digests)) for r in entry.get("renderings") or []
        )
        documents.append(Document(document_id, relative, front, body, body_line, renderings))
        log.info("read document %s with %d rendering(s)", document_id, len(renderings))

    programmes: list[Programme] = []
    for relative in manifest.get("programmes") or []:
        mapping = _mapping(yaml.safe_load(_read_text(root, str(relative), digests)) or {}, f"{relative}")
        programme_id = str(mapping.get("id", Path(str(relative)).stem))
        programmes.append(Programme(programme_id, str(relative), mapping))
        log.info("read programme %s", programme_id)

    events = None
    if manifest.get("events"):
        relative = str(manifest["events"])
        mapping = _mapping(yaml.safe_load(_read_text(root, relative, digests)) or {}, relative)
        events = Events(relative, tuple(_mapping(e, "an event") for e in mapping.get("events") or []))
        log.info("read %d event(s)", len(events.events))

    return Rig(root, version, tuple(documents), tuple(programmes), events, digests)
