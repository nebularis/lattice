# SPDX-License-Identifier: MPL-2.0
"""An MCP server over standard input and output, so an agent such as Claude Desktop proposes MORK mappings with the
tools of this package: the teaching pack and codebook, cards of LATTICE's layers and of a source vocabulary, candidate
target terms for a source term, and the check of a proposal. It holds no model, and a proposal it checks is saved
nowhere, so a person reviews whatever the agent keeps.

Run it with `mise run mork:propose-mcp`."""

from __future__ import annotations

import json
from pathlib import Path

from rdflib import Graph

from . import cards as _cards
from .check import check
from .rank import candidates as _candidates

LAYERS = ("instrument", "eligibility", "party", "behaviour", "foundation", "quantification", "vocabulary", "wording")


def _mtp() -> Path:
    import lattice_repo_catalogue as reader
    catalogue = reader.load()
    return catalogue.root / catalogue.module("mork").directory("mtp")


def teaching_pack() -> str:
    """MTP's L0 and its doctrine, partition and worked cassettes, with MCN's codebook: what a model learns MCN from."""
    mtp = _mtp()
    parts = [(mtp / "out" / "l0.txt").read_text(encoding="utf-8")]
    for name in ("doctrine.yaml", "partition.yaml"):
        parts.append(f"# {name}\n" + (mtp / "data" / name).read_text(encoding="utf-8"))
    for cassette in sorted((mtp / "data" / "cassettes").glob("*.yaml")):
        parts.append(f"# cassette {cassette.stem}\n" + cassette.read_text(encoding="utf-8"))
    parts.append(_cards.codebook_card())
    return "\n\n".join(parts)


def target_cards(layers: list[str]) -> str:
    """The cards of the named LATTICE layers."""
    unknown = sorted(set(layers) - set(LAYERS))
    if unknown:
        raise ValueError(f"no layer {', '.join(unknown)}: choose from {', '.join(LAYERS)}")
    return "\n".join(_cards.render(m, _cards.layer_card(m)) for m in layers)


def _source(path: str) -> Graph:
    return Graph().parse(path)


def source_cards(path: str, namespace: str = "") -> str:
    """The cards of a source vocabulary in an RDF file, those under `namespace` when it is given."""
    g = _source(path)
    return _cards.render(Path(path).name, _cards.source_card(g, [namespace] if namespace else None))


def candidate_terms(path: str, term: str, layers: list[str], k: int = 8, namespace: str = "") -> str:
    """The target terms likeliest to match one source term, a CURIE or IRI of the source file, best first."""
    source = _cards.source_card(_source(path), [namespace] if namespace else None)
    found = [c for c in source if term in (c.curie, str(c.iri))]
    if not found:
        raise ValueError(f"{term} is not a term of {path}")
    targets = [c for m in layers for c in _cards.layer_card(m)]
    return "\n".join(f"{score:.2f} | {card.line()}" for card, score in _candidates(found[0], targets, k)) or "no candidate shares a word with the term"


def check_mapping(mcn: str, sample: str = "") -> str:
    """Decodes, validates and compiles a proposal in MCN, and runs it over a sample source file when one is given, as
    JSON: whether it decoded, its schemes, and every finding."""
    checked = check(mcn, sample=_source(sample) if sample else None)
    return json.dumps(checked.summary(), indent=1)


def main() -> None:
    from mcp.server.mcpserver import MCPServer

    server = MCPServer("lattice-mork-propose", instructions=(
        "Propose MORK mappings from a source vocabulary to LATTICE. Read teaching_pack first, then the cards of the source "
        "and of the target layers, ask candidate_terms where a source term's match is unclear, write the mapping scheme in "
        "MCN, and run check_mapping until it reports no error. Nothing is saved: a person reviews what you propose."))
    for tool in (teaching_pack, target_cards, source_cards, candidate_terms, check_mapping):
        server.tool()(tool)
    server.run("stdio")


if __name__ == "__main__":
    main()
