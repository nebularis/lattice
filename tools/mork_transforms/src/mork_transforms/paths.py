# SPDX-License-Identifier: MPL-2.0
"""The path languages a mapping writes in `mork:dataRef` and `mork:path` for an XML or JSON source (ADR-A148 decision 2).

Each is a subset that both an XSLT stylesheet and a JOLT chain can carry:

    xml   := '/'? step ( '/' step )*        step := '.' | '*' | '@' qname | qname     qname := ( prefix ':' )? NCName
    json  := ( '$' | key ) ( '.' key | '[*]' )*                                         key := [A-Za-z_][A-Za-z0-9_-]*

An XML path that starts with `/` starts at the document, and a JSON path that starts with `$` at the document's root
value. Any other path starts at the focus node. A prefix is one the mapping scheme declares with `sh:declare`, and an
unprefixed XML name is in no namespace, as in XPath. `.` is the focus itself, and an attribute ends a path."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping, Optional

from mork_rdf.paths import PathError

_NCNAME = re.compile(r"[A-Za-z_][A-Za-z0-9_.-]*")
_KEY = re.compile(r"[A-Za-z_][A-Za-z0-9_-]*")


@dataclass(frozen=True)
class Step:
    kind: str                     # "child", "attribute", "any" or "self" for XML, "key" or "each" for JSON
    namespace: Optional[str] = None
    name: Optional[str] = None


@dataclass(frozen=True)
class SourcePath:
    format: str                   # "xml" or "json"
    absolute: bool
    steps: tuple[Step, ...]
    text: str

    @property
    def iterates(self) -> bool:
        """Whether the path can reach several nodes from one, which a JSON path says with `[*]`."""
        return any(s.kind == "each" for s in self.steps)


def parse_xml(text: str, prefixes: Mapping[str, str]) -> SourcePath:
    source = text.strip()
    absolute = source.startswith("/")
    body = source[1:] if absolute else source
    if not body or "//" in source:
        raise PathError(f"{text!r} is not a path of the XML subset: no empty step, and no //")
    steps = []
    parts = body.split("/")
    for n, part in enumerate(parts):
        if part == ".":
            if len(parts) > 1 or absolute:
                raise PathError(f"{text!r}: . is a path of its own")
            steps.append(Step("self"))
        elif part == "*":
            steps.append(Step("any"))
        else:
            attribute = part.startswith("@")
            if attribute and n != len(parts) - 1:
                raise PathError(f"{text!r}: an attribute ends a path")
            namespace, name = _qname(part[1:] if attribute else part, prefixes, text)
            steps.append(Step("attribute" if attribute else "child", namespace, name))
    return SourcePath("xml", absolute, tuple(steps), source)


def _qname(part: str, prefixes: Mapping[str, str], text: str) -> tuple[Optional[str], str]:
    prefix, colon, name = part.rpartition(":")
    if not _NCNAME.fullmatch(name) or (colon and not _NCNAME.fullmatch(prefix)):
        raise PathError(f"{text!r}: {part!r} is not a qualified name")
    if not colon:
        return None, name
    if prefix not in prefixes:
        raise PathError(f"{text!r}: the scheme declares no prefix {prefix!r}")
    return prefixes[prefix], name


def parse_json(text: str, prefixes: Mapping[str, str] = {}) -> SourcePath:
    source = text.strip()
    absolute = source.startswith("$")
    at = 1 if absolute else 0
    steps = []
    if not absolute:
        key = _KEY.match(source)
        if key is None:
            raise PathError(f"{text!r} is not a path of the JSON subset: start with $ or a key")
        steps.append(Step("key", name=key.group()))
        at = key.end()
    while at < len(source):
        if source.startswith("[*]", at):
            steps.append(Step("each"))
            at += 3
        elif source.startswith(".", at) and (key := _KEY.match(source, at + 1)) is not None:
            steps.append(Step("key", name=key.group()))
            at = key.end()
        else:
            raise PathError(f"{text!r}: {source[at:]!r} is not .key or [*]")
    if not steps:
        raise PathError(f"{text!r}: a path names at least one key")
    return SourcePath("json", absolute, tuple(steps), source)
