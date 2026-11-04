# SPDX-License-Identifier: MPL-2.0
"""SPARQL 1.1 property paths, as a MORK mapping writes them in `mork:dataRef` and `mork:path` for an RDF source.

A path is parsed into a tree and written back from the tree with every IRI in full, so no text from a mapping reaches a
query unparsed (PRI-55). The grammar is SPARQL 1.1's `Path` production (§9.1 of the recommendation):

    path     := seq ( '|' seq )*
    seq      := elt ( '/' elt )*
    elt      := '^'? primary ( '*' | '+' | '?' )?
    primary  := iri | 'a' | '(' path ')' | '!' negset
    negset   := one | '(' one ( '|' one )* ')'
    one      := '^'? ( iri | 'a' )
    iri      := '<' absolute IRI '>' | prefix ':' local

A prefixed name's prefix is one the mapping scheme declares with SHACL's `sh:declare` (see the README)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping, Union

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"

# RFC 3987 forbids these in an IRI, and SPARQL's IRIREF production excludes them.
_BAD_IRI = re.compile(r'[\x00-\x20<>"{}|^`\\]')
_PNAME = re.compile(r"([A-Za-z][A-Za-z0-9_.-]*)?:([A-Za-z0-9_](?:[A-Za-z0-9_.-]*[A-Za-z0-9_-])?)?")
_SCHEME = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*:")


class PathError(ValueError):
    """A path that does not parse, or names a prefix the scheme does not declare."""


@dataclass(frozen=True)
class Iri:
    value: str


@dataclass(frozen=True)
class Inverse:
    path: "Path"


@dataclass(frozen=True)
class Seq:
    parts: tuple["Path", ...]


@dataclass(frozen=True)
class Alt:
    parts: tuple["Path", ...]


@dataclass(frozen=True)
class Mod:
    path: "Path"
    mod: str  # '*', '+' or '?'


@dataclass(frozen=True)
class NegSet:
    members: tuple[tuple[bool, str], ...]  # (inverse, IRI)


Path = Union[Iri, Inverse, Seq, Alt, Mod, NegSet]


def iri(value: str) -> str:
    """An absolute IRI written for a query, refused if it is not one."""
    if not _SCHEME.match(value) or _BAD_IRI.search(value):
        raise PathError(f"not an absolute IRI: {value!r}")
    return f"<{value}>"


class _Parser:
    def __init__(self, text: str, prefixes: Mapping[str, str]):
        self.text, self.prefixes, self.at = text, prefixes, 0

    def _skip(self) -> None:
        while self.at < len(self.text) and self.text[self.at].isspace():
            self.at += 1

    def _peek(self) -> str:
        self._skip()
        return self.text[self.at] if self.at < len(self.text) else ""

    def _take(self, char: str) -> bool:
        if self._peek() == char:
            self.at += 1
            return True
        return False

    def _fail(self, what: str) -> PathError:
        return PathError(f"{what} at {self.at} in path {self.text!r}")

    def parse(self) -> Path:
        path = self._alt()
        if self._peek():
            raise self._fail("unexpected text")
        return path

    def _alt(self) -> Path:
        parts = [self._seq()]
        while self._take("|"):
            parts.append(self._seq())
        return parts[0] if len(parts) == 1 else Alt(tuple(parts))

    def _seq(self) -> Path:
        parts = [self._elt()]
        while self._take("/"):
            parts.append(self._elt())
        return parts[0] if len(parts) == 1 else Seq(tuple(parts))

    def _elt(self) -> Path:
        inverse = self._take("^")
        path = self._primary()
        char = self._peek()
        if char in ("*", "+", "?"):
            self.at += 1
            path = Mod(path, char)
        return Inverse(path) if inverse else path

    def _primary(self) -> Path:
        if self._take("("):
            path = self._alt()
            if not self._take(")"):
                raise self._fail("expected ')'")
            return path
        if self._take("!"):
            if self._take("("):
                members = [self._one()]
                while self._take("|"):
                    members.append(self._one())
                if not self._take(")"):
                    raise self._fail("expected ')'")
                return NegSet(tuple(members))
            return NegSet((self._one(),))
        return Iri(self._iri())

    def _one(self) -> tuple[bool, str]:
        inverse = self._take("^")
        return inverse, self._iri()

    def _iri(self) -> str:
        self._skip()
        rest = self.text[self.at:]
        if rest.startswith("<"):
            end = rest.find(">")
            if end < 0:
                raise self._fail("unclosed IRI")
            value = rest[1:end]
            iri(value)
            self.at += end + 1
            return value
        if rest.startswith("a") and (len(rest) == 1 or not (rest[1].isalnum() or rest[1] in ":_-.")):
            self.at += 1
            return RDF_TYPE
        match = _PNAME.match(rest)
        if not match or not match.group(0):
            raise self._fail("expected an IRI")
        prefix, local = match.group(1) or "", match.group(2) or ""
        if prefix not in self.prefixes:
            raise self._fail(f"undeclared prefix {prefix!r}")
        self.at += len(match.group(0))
        value = self.prefixes[prefix] + local
        iri(value)
        return value


def parse(text: str, prefixes: Mapping[str, str]) -> Path:
    return _Parser(text, prefixes).parse()


def write(path: Path) -> str:
    """The path as SPARQL, every IRI in full and every compound part parenthesised."""
    if isinstance(path, Iri):
        return iri(path.value)
    if isinstance(path, Inverse):
        return "^" + _group(path.path)
    if isinstance(path, Seq):
        return "/".join(_group(p) for p in path.parts)
    if isinstance(path, Alt):
        return "|".join(_group(p) for p in path.parts)
    if isinstance(path, Mod):
        return _group(path.path) + path.mod
    members = "|".join(("^" if inverse else "") + iri(value) for inverse, value in path.members)
    return f"!({members})"


def _group(path: Path) -> str:
    text = write(path)
    return text if isinstance(path, (Iri, NegSet)) else f"({text})"


def single(path: Path) -> str | None:
    """The IRI of a path that is one forward property, else None."""
    return path.value if isinstance(path, Iri) else None
