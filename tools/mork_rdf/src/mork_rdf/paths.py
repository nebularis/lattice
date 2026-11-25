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


def _push(path: Path, inverted: bool = False) -> Path:
    """The same path with every inverse pushed down to the property it reads, `^(a/b)` being `^b/^a` and `^^a` being `a`."""
    if isinstance(path, Iri):
        return Inverse(path) if inverted else path
    if isinstance(path, Inverse):
        return _push(path.path, not inverted)
    if isinstance(path, Seq):
        parts = tuple(_push(p, inverted) for p in (reversed(path.parts) if inverted else path.parts))
        return Seq(parts)
    if isinstance(path, Alt):
        return Alt(tuple(_push(p, inverted) for p in path.parts))
    if isinstance(path, Mod):
        return Mod(_push(path.path, inverted), path.mod)
    return NegSet(tuple((i != inverted, v) for i, v in path.members)) if inverted else path


def _nullable(path: Path) -> bool:
    """Whether the path may reach the node it starts from without a step."""
    if isinstance(path, Mod):
        return path.mod in ("*", "?") or _nullable(path.path)
    if isinstance(path, Seq):
        return all(_nullable(p) for p in path.parts)
    if isinstance(path, Alt):
        return any(_nullable(p) for p in path.parts)
    if isinstance(path, Inverse):
        return _nullable(path.path)
    return False


def _first_steps(path: Path) -> list[Path]:
    if isinstance(path, Seq):
        steps: list[Path] = []
        for part in path.parts:
            steps += _first_steps(part)
            if not _nullable(part):
                break
        return steps
    if isinstance(path, Alt):
        return [step for part in path.parts for step in _first_steps(part)]
    if isinstance(path, Mod):
        return _first_steps(path.path)
    return [path]


def entry(path: Path) -> Path:
    """The first step of a path, the path that a node holds a value at when it can start the path at all. A sequence starts
    at its first part, and at the part after it where that part may take no step, an alternative at any of its parts, and an
    inverse at the inverse of the property the sequence ends in. A node with no value at the entry reaches nothing from it,
    which is a node that lacks the property and not a node whose collection is empty."""
    steps = _first_steps(_push(path))
    unique = list(dict.fromkeys(steps))
    return unique[0] if len(unique) == 1 else Alt(tuple(unique))


def closures(path: Path) -> list[tuple[Path | None, Path]]:
    """Each closure a path walks, as (the path that reaches the node it starts from, or None where the path's own start is
    that node, and the path the closure repeats). A closure is `*` or `+` over a path."""
    found: list[tuple[Path | None, Path]] = []

    def join(prefix: Path | None, step: Path) -> Path:
        return step if prefix is None else Seq((prefix, step))

    def walk(node: Path, prefix: Path | None) -> None:
        if isinstance(node, Seq):
            for i, part in enumerate(node.parts):
                walk(part, join(prefix, Seq(node.parts[:i])) if i > 1 else (join(prefix, node.parts[0]) if i == 1 else prefix))
        elif isinstance(node, Alt):
            for part in node.parts:
                walk(part, prefix)
        elif isinstance(node, Mod):
            if node.mod in ("*", "+"):
                found.append((prefix, node.path))
                walk(node.path, join(prefix, Mod(node.path, "*")))
            else:
                walk(node.path, prefix)

    walk(_push(path), None)
    unique: list[tuple[Path | None, Path]] = []
    for site in found:
        if site not in unique:
            unique.append(site)
    return unique
