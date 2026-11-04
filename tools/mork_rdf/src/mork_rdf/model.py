# SPDX-License-Identifier: MPL-2.0
"""What the compiler reads and gives: findings, compiled queries and the compiled mapping (README §11)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from rdflib import Namespace, URIRef

MORK = Namespace("http://www.nebularis.org/ontologies/Mork#")
FND = Namespace("https://www.nebularis.org/neuro-semantic/lattice/foundation#")
SH = Namespace("http://www.w3.org/ns/shacl#")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")

COMPILER = "mork-rdf 0.1.0"
REFERENCE_GRAPH = "urn:mork-rdf:reference"


class Severity(Enum):
    INFO = "info"        # nothing lost, for example a mapping for another backend
    WARNING = "warning"  # compiled, but a reviewer should know, for example a broad match
    ERROR = "error"      # not compiled. In production mode any error fails the compilation


@dataclass(frozen=True, order=True)
class Finding:
    """One thing the compiler or a check found. `code` is from README §10, and `mapping` the node it is about."""

    code: str
    mapping: Optional[str]
    message: str
    severity: Severity = field(default=Severity.ERROR, compare=False)
    focus: Optional[str] = field(default=None, compare=False)
    value: Optional[str] = field(default=None, compare=False)


@dataclass(frozen=True)
class CompiledQuery:
    """A CONSTRUCT that writes one mapping's triples, or a check SELECT that reports where it could not."""

    mapping: str        # the mapping node the query comes from
    path: tuple[str, ...]  # the mapping nodes from the root to it, a template's child appearing under each instance
    kind: str           # "construct", "check", or "closure", a SELECT of the members of a class combination
    code: Optional[str]  # for a check, the finding code each row reports
    text: str
    box: str = "abox"   # "abox" for instance data, "tbox" for the classes, properties and axioms a mapping creates
    reads: tuple[str, ...] = ()  # the mappings whose output the query reads, which run in earlier strata
    stratum: int = 0    # the step of the run the query belongs to, after every stratum it reads (README §12)
    head: Optional[tuple[str, str, str]] = None  # for a closure, the property, rdfs:domain or rdfs:range, and the combination


@dataclass(frozen=True)
class CompiledMapping:
    scheme: str
    mapping_digest: str  # SHA-256 of the mapping graph's RDFC-1.0 canonical N-Quads (ADR-A143)
    at: str              # the instant the mapping graph was read at
    base: str
    mode: str            # the scheme's compilation mode: draft, review or production
    queries: tuple[CompiledQuery, ...]
    findings: tuple[Finding, ...]
    confidence: tuple[tuple[str, float], ...]  # each compiled mapping's effective confidence, sorted
    compiler: str = COMPILER

    @property
    def constructs(self) -> tuple[CompiledQuery, ...]:
        return tuple(q for q in self.queries if q.kind == "construct")

    @property
    def checks(self) -> tuple[CompiledQuery, ...]:
        return tuple(q for q in self.queries if q.kind == "check")

    @property
    def closures(self) -> tuple[CompiledQuery, ...]:
        return tuple(q for q in self.queries if q.kind == "closure")

    @property
    def strata(self) -> int:
        return 1 + max((q.stratum for q in self.queries), default=0)

    @property
    def errors(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.severity is Severity.ERROR)

    def text(self) -> str:
        """Every query in order, each headed by a comment naming its mapping, which is the artefact a reviewer reads."""
        lines = [
            f"# {self.compiler}, scheme <{self.scheme}>, read at {self.at}, mode {self.mode}",
            f"# mapping graph sha256:{self.mapping_digest}",
        ]
        for query in self.queries:
            lines += ["", f"# {query.kind}{' ' + query.code if query.code else ''} for <{query.mapping}>, {query.box}, stratum {query.stratum}",
                      "# via " + " > ".join(f"<{p}>" for p in query.path)]
            lines += ["# reads the output of " + ", ".join(f"<{r}>" for r in query.reads)] if query.reads else []
            lines += [f"# writes <{query.head[0]}> <{query.head[1]}> the <{query.head[2]}> of the members"] if query.head else []
            lines.append(query.text)
        return "\n".join(lines) + "\n"

    @property
    def digest(self) -> str:
        """SHA-256 of `text()`, the key a compiled artefact is cached by beside the mapping digest."""
        return hashlib.sha256(self.text().encode("utf-8")).hexdigest()


class CompileError(ValueError):
    """A mapping graph that cannot be compiled at all, or that has errors in production mode. `findings` says why."""

    def __init__(self, message: str, findings: tuple[Finding, ...] = ()):
        super().__init__(message)
        self.findings = findings


def local(node: URIRef | str) -> str:
    text = str(node)
    return text.rsplit("#", 1)[-1].rsplit("/", 1)[-1] or text
