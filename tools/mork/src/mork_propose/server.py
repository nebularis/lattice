# SPDX-License-Identifier: MPL-2.0
"""An MCP server over standard input and output, so an agent such as Claude Desktop proposes MORK mappings with the
tools of this package: the teaching pack and codebook, cards of LATTICE's layers and of a source vocabulary, candidate
target terms for a source term, and the check of a proposal. It holds no model, and a proposal it checks is saved
nowhere, so a person reviews whatever the agent keeps.

Run it with `mise run mork:propose-mcp`."""

from __future__ import annotations

import functools
import json
from pathlib import Path

from rdflib import Graph

from . import cards as _cards
from .check import check
from .describe import describe_term as _describe
from . import translations as _translations
from .rank import candidates as _candidates

LAYERS = ("instrument", "eligibility", "party", "behaviour", "foundation", "quantification", "vocabulary", "wording")


def _mtp() -> Path:
    import lattice_repo_catalogue as reader
    catalogue = reader.load()
    return catalogue.root / catalogue.module("mork").directory("mtp")


def teaching_pack() -> str:
    """MTP's L0 and its doctrine, partition and worked cassettes, the translation table of a source's legal words, and
    MCN's codebook: what a model learns MCN from."""
    mtp = _mtp()
    parts = [(mtp / "out" / "l0.txt").read_text(encoding="utf-8")]
    for name in ("doctrine.yaml", "partition.yaml"):
        parts.append(f"# {name}\n" + (mtp / "data" / name).read_text(encoding="utf-8"))
    for cassette in sorted((mtp / "data" / "cassettes").glob("*.yaml")):
        parts.append(f"# cassette {cassette.stem}\n" + cassette.read_text(encoding="utf-8"))
    parts.append(_translations.card())
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
    ranked = _candidates(found[0], targets, k, aliases=_translations.aliases())
    return "\n".join(f"{score:.2f} | {card.line()}" for card, score in ranked) or "no candidate shares a word with the term"


def describe_term(term: str) -> str:
    """One LATTICE term in depth, a CURIE such as ins:Permission or an IRI: its comment and utility in full, where it
    sits, the properties of it and to it, its individuals, and the laws its layer's shapes state about it. Read it for
    each term a card leaves unclear, before writing a mapping to it."""
    return _describe(term, LAYERS)


@functools.lru_cache(maxsize=1)
def _target() -> tuple[Graph, Graph]:
    """Every layer's specification and vocabulary, and every layer's shapes, merged, which a proposal's target terms and
    what it writes are checked against."""
    from .describe import _shapes

    vocabulary, shapes = Graph(), Graph()
    for m in LAYERS:
        vocabulary += _cards._layer_graph(m)
        shapes += _shapes(m)
    return vocabulary, shapes


def check_mapping(mcn: str, sample: str = "") -> str:
    """Decodes, validates and compiles a proposal in MCN, checks that every target term is declared, and runs it over a
    sample source file when one is given, validating what it writes against the target layers' shapes, as JSON: whether
    it decoded, its schemes, and every finding, a shape's on the mapping that wrote its node. Give a sample whenever
    there is one, since only a run shows whether the meaning written keeps the layers' laws."""
    vocabulary, shapes = _target()
    checked = check(mcn, sample=_source(sample) if sample else None, target_vocabulary=vocabulary, target_shapes=shapes)
    return json.dumps(checked.summary(), indent=1)


def main() -> None:
    from mcp.server.mcpserver import MCPServer

    server = MCPServer("lattice-mork-propose", instructions=(
        "Propose MORK mappings from a source vocabulary to LATTICE. Read teaching_pack first, then the cards of the source "
        "and of the target layers, ask candidate_terms where a source term's match is unclear, read describe_term for each "
        "target term you mean to use, write the mapping scheme in "
        "MCN, and run check_mapping until it reports no error. Nothing is saved: a person reviews what you propose."))
    for tool in (teaching_pack, target_cards, source_cards, candidate_terms, describe_term, check_mapping):
        server.tool()(tool)
    server.run("stdio")


if __name__ == "__main__":
    main()
