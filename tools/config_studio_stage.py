# SPDX-License-Identifier: MPL-2.0
"""Stages what the Configuration Studio's service serves (ADR-A136): the merged vocabulary, with the
layers' form shapes, and the samples. `python tools/config_studio_stage.py [--root .] [--out .build/config-studio]`.

The service reads only the staged files, so it needs neither the repository catalogue nor
rdflib, and finds every repository file through the catalogue here (STD-273).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable, List

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SH

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lattice_repo_catalogue  # noqa: E402

CST = Namespace("https://www.nebularis.org/neuro-semantic/lattice/config-studio#")
SAMPLE_PREFIX = "urn:lattice:studio:sample:"

# The modules whose specifications and vocabularies define what the studio's forms offer.
VOCABULARY = (
    ("persistence", "spec"), ("surface", "spec"), ("surface", "vocab"), ("foundation", "spec"), ("foundation", "vocab"), ("vocabulary", "spec"),
    ("quantification", "spec"), ("quantification", "vocab"), ("eligibility", "spec"), ("eligibility", "vocab"),
    ("wording", "spec"), ("wording", "vocab"), ("party", "spec"), ("party", "vocab"), ("behaviour", "spec"), ("behaviour", "vocab"),
    ("instrument", "spec"), ("instrument", "vocab"), ("mork", "spec"),
)

# The layers whose SHACL shapes place and constrain the forms' properties. The browser reads only
# node shapes and property shapes, so only the triples below are staged. SHACL-SPARQL constraints,
# messages and rules stay out. Party has no shapes (TD-110).
SHAPED = ("persistence", "surface", "foundation", "vocabulary", "quantification", "eligibility", "wording", "instrument")
SHAPE_PREDICATES = frozenset(
    SH[n] for n in ("targetClass", "property", "path", "datatype", "class", "nodeKind", "in", "minCount", "maxCount", "name", "description")
) | {RDF.first, RDF.rest}
SHAPE_TYPES = frozenset({SH.NodeShape, SH.PropertyShape, RDFS.Class, OWL.Class})


def _turtle(directory: Path) -> List[Path]:
    return sorted(directory.glob("*.ttl"))


def _merge(paths: Iterable[Path]) -> Graph:
    graph = Graph()
    for path in paths:
        graph.parse(path, format="turtle")
    return graph


def vocabulary_files(catalogue: lattice_repo_catalogue.Catalogue) -> List[Path]:
    root = catalogue.root
    return [path for module, role in VOCABULARY for path in _turtle(root / catalogue.module(module).directory(role))]


def shape_files(catalogue: lattice_repo_catalogue.Catalogue) -> List[Path]:
    return [path for module in SHAPED for path in _turtle(catalogue.root / catalogue.module(module).directory("shapes"))]


def form_shapes(shapes: Graph) -> Graph:
    """The triples of `shapes` that a form reads, with the prefixes of the source files."""
    kept = Graph()
    for prefix, namespace in shapes.namespaces():
        kept.bind(prefix, namespace)
    for s, p, o in shapes:
        if p in SHAPE_PREDICATES or (p == RDF.type and o in SHAPE_TYPES):
            kept.add((s, p, o))
    return kept


def sample_files(catalogue: lattice_repo_catalogue.Catalogue, manifest: Graph, sample: URIRef, samples_dir: Path) -> List[Path]:
    files = []
    for part in manifest.objects(sample, CST.part):
        name = str(manifest.value(part, CST.fileName))
        module = manifest.value(part, CST.module)
        if module is None:
            path = samples_dir / name
        else:
            role = str(manifest.value(part, CST.role))
            path = catalogue.root / catalogue.module(str(module)).directory(role) / name
        if not path.is_file():
            raise SystemExit(f"sample {sample} names {path.as_posix()}, which does not exist")
        files.append(path)
    return sorted(files)


def stage(root: Path, out: Path) -> None:
    catalogue = lattice_repo_catalogue.load(root)
    samples_dir = catalogue.root / catalogue.area("contracts") / "config-studio" / "samples"
    (out / "samples").mkdir(parents=True, exist_ok=True)

    vocabulary = _merge(vocabulary_files(catalogue))
    vocabulary += form_shapes(_merge(shape_files(catalogue)))
    vocabulary.serialize(out / "vocabulary.ttl", format="turtle", encoding="utf-8")

    manifest = Graph().parse(samples_dir / "samples.ttl", format="turtle")
    listing = Graph()
    listing.bind("cst", CST)
    for sample in sorted(manifest.subjects(RDF.type, CST.Sample)):
        if not str(sample).startswith(SAMPLE_PREFIX):
            raise SystemExit(f"sample {sample} is not named {SAMPLE_PREFIX}<id>")
        merged = _merge(sample_files(catalogue, manifest, sample, samples_dir))
        merged.serialize(out / "samples" / f"{str(sample)[len(SAMPLE_PREFIX):]}.ttl", format="turtle", encoding="utf-8")
        for p, o in manifest.predicate_objects(sample):
            if p != CST.part:
                listing.add((sample, p, o))
    listing.serialize(out / "samples.ttl", format="turtle", encoding="utf-8")
    # The units a workspace publishes (ADR-A149), which the service serves to the browser.
    units = catalogue.root / catalogue.area("contracts") / "config-studio" / "publication-units.ttl"
    (out / "publication-units.ttl").write_text(units.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
    # MORK's teaching pack's first layer, which the service's MCP server offers as a prompt.
    (out / "prompts").mkdir(parents=True, exist_ok=True)
    mtp = catalogue.root / catalogue.module("mork").directory("mtp") / "out" / "l0.txt"
    (out / "prompts" / "mtp-l0.txt").write_text(mtp.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
    stage_mork(out / "mork")
    print(f"staged {out.as_posix()}")


def stage_mork(folder: Path) -> None:
    """MORK's proposal tools that read no source, which the service's MCP server serves as staged: the teaching pack,
    each layer's cards, and every layer term in depth, by CURIE."""
    import json

    from mork_propose import server
    from mork_propose.cards import layer_card

    (folder / "cards").mkdir(parents=True, exist_ok=True)
    (folder / "teaching-pack.txt").write_text(server.teaching_pack(), encoding="utf-8", newline="\n")
    terms = {}
    for layer in server.LAYERS:
        (folder / "cards" / f"{layer}.txt").write_text(server.target_cards([layer]), encoding="utf-8", newline="\n")
        for card in layer_card(layer):
            terms.setdefault(card.curie, server.describe_term(card.curie))
    (folder / "describe.json").write_text(json.dumps(terms, indent=0, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main(argv: List[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=None)
    parser.add_argument("--out", default=None, help="default: <root>/.build/config-studio")
    args = parser.parse_args(argv)
    root = lattice_repo_catalogue.find_root(args.root)
    stage(root, Path(args.out) if args.out else root / ".build" / "config-studio")


if __name__ == "__main__":
    main()
