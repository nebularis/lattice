# SPDX-License-Identifier: MPL-2.0
"""What the surface compile job does with a configuration's projection contracts, and what a projection step reads back (contracts/config-studio/README.md,
Jobs, and Runs, "A projection step"; ADR-A154, addendum of 2026-11-25).

A projection contract is lowered with Surface's lowering into a MORK mapping scheme and the scheme is compiled with `mork_rdf`, a function of the
contract, the declarations the job reads and the job's time, so a repeat gives the same files. The compiled form of each scheme is an artefact of the
group `projections`, `{scheme}.compiled.ttl`, which `mork_rdf.from_rdf` reads back, beside the lowered scheme itself, `{scheme}.mork.ttl`, the graph the
lowering produced before compilation, which a reader draws the scheme's mappings and terms from. The group's `manifest.json` names each contract's key,
its scheme and both files, in the order of the scheme's IRI. A projection step reads the manifest and nothing else of the job, since it has no compiler.
Nothing here reads a clock or the broker."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable, Optional

from rdflib import Graph, URIRef
from rdflib.namespace import RDF

PROJECTIONS = "projections"
"""The group of the artefacts a surface compilation holds for the projection step, `manifest.json` and a `{scheme}.compiled.ttl` for each scheme."""
MANIFEST = f"{PROJECTIONS}/manifest.json"

_MORK = "http://www.nebularis.org/ontologies/Mork#"
SCHEME = URIRef(_MORK + "MappingScheme")


@dataclass(frozen=True)
class Compiled:
    """One projection contract after lowering and compilation. `scheme` and `compiled` are None for a contract that lowers into no scheme, which
    states nothing to write, and `refusal` says why a contract could not be lowered or compiled. `lowered` is the graph the lowering produced, which
    the compiler read, and it is held beside the compiled form."""

    iri: URIRef
    key: str
    kind: str
    scheme: Optional[str] = None
    compiled: Any = None
    refusal: Optional[str] = None
    lowered: Optional[Graph] = None


def base_for(namespace: str) -> str:
    """The namespace the nodes a projection mints fall under: the contract's target namespace, its `#` or missing `/` made a `/`, so a relative IRI
    a query builds is resolved below the namespace and never against a fragment."""
    text = str(namespace).rstrip("#/")
    return text + "/"


def artefact_name(scheme: str) -> str:
    """The name a scheme's compiled form has, as a mapping compilation names it, from the local name of the scheme."""
    return re.sub(r"[^A-Za-z0-9_-]+", "-", scheme.rsplit("#", 1)[-1].rsplit("/", 1)[-1]).strip("-") or "scheme"


def lower_and_compile(source: Graph, vocabulary: Graph, at: datetime) -> list[Compiled]:
    """Every projection contract of `source`, ordered by its key, lowered and compiled. A contract that cannot be lowered or compiled is returned with
    its refusal and the others are still compiled. `vocabulary` types the target terms."""
    import mork_rdf
    from surface.model import ContractError, read_projection_contracts
    from surface.lowering import lower_projection, lowers_to_scheme

    out: list[Compiled] = []
    for contract in sorted(read_projection_contracts(source), key=lambda c: c.key):
        kind = str(contract.projection_kind).rsplit("#", 1)[-1]
        try:
            lowered = lower_projection(contract)
            if not lowers_to_scheme(contract):
                out.append(Compiled(contract.iri, contract.key, kind))
                continue
            (scheme,) = sorted(lowered.subjects(RDF.type, SCHEME), key=str)
            compiled = mork_rdf.compile_scheme(lowered, scheme, base=base_for(contract.target_namespace), at=at, target_vocabulary=vocabulary)
        except (ContractError, mork_rdf.CompileError, ValueError) as error:
            out.append(Compiled(contract.iri, contract.key, kind, refusal=str(error)))
            continue
        out.append(Compiled(contract.iri, contract.key, kind, str(scheme), compiled, lowered=lowered))
    return out


def manifest(compiled: Iterable[Compiled]) -> list[dict[str, str]]:
    """The group's manifest, one entry for each contract that has a compiled form, ordered by the scheme's IRI. `mork` names the lowered scheme itself."""
    entries = [
        {
            "key": c.key, "contract": str(c.iri), "kind": c.kind, "scheme": c.scheme,
            "path": f"{PROJECTIONS}/{artefact_name(c.scheme)}.compiled.ttl", "mork": f"{PROJECTIONS}/{artefact_name(c.scheme)}.mork.ttl",
        }
        for c in compiled if c.scheme is not None and c.refusal is None
    ]
    return sorted(entries, key=lambda e: e["scheme"])


def manifest_text(entries: list[dict[str, str]]) -> str:
    return json.dumps(entries, indent=2) + "\n"
