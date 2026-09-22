# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""RDF-term encoding, the injection-safety boundary for the ``instantiate``
stage (sketch §5.3, ADR-A79 point 4).

A value produced by the ``compile`` stage (a shard number, a graph-IRI
template, a property IRI drawn from the loaded ontology graphs) is untrusted
in the security sense: it may contain an adversarial or malformed string,
whether by accident or by a compromised upstream dependency. Every such
value must pass through exactly one of the encoders in this module before it
is placed into a Mustache template context. The template renderer
(:func:`persistence.render.render`) refuses, by a type check rather than a
runtime probe, any value that is a bare ``str`` rather than one of the
wrapped types below.

Templates themselves are Lattice-authored, reviewed source files, and are
treated as trusted structure. The security boundary is exactly, and only,
the line between adopter-supplied configuration data and these encoders.
"""

from __future__ import annotations

import re
from typing import Optional


class SparqlTermError(ValueError):
    """Raised when a value cannot be safely encoded as an RDF term."""


class SparqlTerm(str):
    """A string that has already been validated and escaped as a specific
    RDF term. The template renderer accepts only this type (or a subclass,
    or a plain ``int``, or a list of these), never a bare ``str``. A value
    that skipped an encoder is therefore a programming error caught by a
    type check, not a data problem caught by a runtime probe."""

    __slots__ = ()


# IRI references must not contain any of these characters unescaped
# (RFC 3987 excludes C0/C1 controls, space, and the delimiters below from
# ucschar/iunreserved/iprivate; SPARQL additionally cannot tolerate a
# `>` breaking out of `<...>` or a `\` beginning an unintended escape).
# Rather than percent-escape a hostile value into something that merely
# *looks* inert, an IRI containing any of these is refused outright.
_IRI_FORBIDDEN_CHARS = set('<>"{}|\\^`') | {chr(c) for c in range(0x00, 0x21)}


class Iri(SparqlTerm):
    """A validated, angle-bracket-wrapped IRI reference, e.g. ``<urn:g:x>``."""

    __slots__ = ()

    @classmethod
    def encode(cls, value: str) -> "Iri":
        if not isinstance(value, str) or not value:
            raise SparqlTermError(f"IRI must be a non-empty string, got {value!r}")
        forbidden = _IRI_FORBIDDEN_CHARS.intersection(value)
        if forbidden:
            raise SparqlTermError(
                f"IRI {value!r} contains disallowed character(s) {sorted(forbidden)!r}; "
                "refused rather than percent-escaped"
            )
        # Zero-width and bidirectional-override characters are a common
        # spoofing vector (an IRI that displays as one thing and parses as
        # another). Reject them explicitly rather than relying on the
        # forbidden-character set above, which targets syntax, not spoofing.
        for ch in value:
            cp = ord(ch)
            if cp in (0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF) or 0x202A <= cp <= 0x202E or 0x2066 <= cp <= 0x2069:
                raise SparqlTermError(
                    f"IRI {value!r} contains a zero-width or bidirectional-override "
                    f"character (U+{cp:04X}); refused"
                )
        return cls(f"<{value}>")


# SPARQL literal escapes (the ECHAR production): backslash, quote, and the
# usual C-style whitespace escapes. Order matters: backslash first, or a
# later substitution's backslash would itself be re-escaped.
_LITERAL_ESCAPES = (
    ("\\", "\\\\"),
    ('"', '\\"'),
    ("\n", "\\n"),
    ("\r", "\\r"),
    ("\t", "\\t"),
)

_LANG_TAG_RE = re.compile(r"^[A-Za-z]{1,8}(-[A-Za-z0-9]{1,8})*$")


class Literal(SparqlTerm):
    """A validated, quoted, and escaped RDF literal, optionally typed or
    language-tagged."""

    __slots__ = ()

    @classmethod
    def encode(
        cls,
        value: str,
        datatype: Optional[str] = None,
        lang: Optional[str] = None,
    ) -> "Literal":
        if not isinstance(value, str):
            raise SparqlTermError(f"Literal value must be a string, got {value!r}")
        if datatype and lang:
            raise SparqlTermError("a literal cannot carry both a datatype and a language tag")
        escaped = value
        for raw, esc in _LITERAL_ESCAPES:
            escaped = escaped.replace(raw, esc)
        quoted = f'"{escaped}"'
        if datatype:
            quoted += f"^^{Iri.encode(datatype)}"
        elif lang:
            if not _LANG_TAG_RE.match(lang):
                raise SparqlTermError(f"invalid language tag {lang!r}")
            quoted += f"@{lang}"
        return cls(quoted)


_VARNAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class Var(SparqlTerm):
    """A validated SPARQL variable reference, e.g. ``?entity``."""

    __slots__ = ()

    @classmethod
    def encode(cls, name: str) -> "Var":
        if not isinstance(name, str) or not _VARNAME_RE.match(name):
            raise SparqlTermError(f"invalid SPARQL variable name {name!r}")
        return cls(f"?{name}")


class Integer(SparqlTerm):
    """A validated bare integer literal, e.g. for a shard count."""

    __slots__ = ()

    @classmethod
    def encode(cls, value: int) -> "Integer":
        if isinstance(value, bool) or not isinstance(value, int):
            raise SparqlTermError(f"expected an int, got {value!r}")
        return cls(str(value))


__all__ = ["SparqlTerm", "SparqlTermError", "Iri", "Literal", "Var", "Integer"]
