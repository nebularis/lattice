# SPDX-License-Identifier: MPL-2.0
"""Stages what the Configuration Studio's service serves (ADR-A136): the merged vocabulary and
the samples. `python tools/config_studio_stage.py [--root .] [--out .build/config-studio]`.

The service reads only the staged files, so it needs neither the repository catalogue nor
rdflib, and finds every repository file through the catalogue here (STD-273).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable, List

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lattice_repo_catalogue  # noqa: E402

CST = Namespace("https://www.nebularis.org/neuro-semantic/lattice/poc/config-studio#")
SAMPLE_PREFIX = "urn:lattice:studio:sample:"

# The modules whose specifications and vocabularies define what the studio's forms offer.
VOCABULARY = (("persistence", "spec"), ("surface", "spec"), ("surface", "vocab"), ("foundation", "spec"), ("vocabulary", "spec"))


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

    _merge(vocabulary_files(catalogue)).serialize(out / "vocabulary.ttl", format="turtle", encoding="utf-8")

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
    print(f"staged {out.as_posix()}")


def main(argv: List[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=None)
    parser.add_argument("--out", default=None, help="default: <root>/.build/config-studio")
    args = parser.parse_args(argv)
    root = lattice_repo_catalogue.find_root(args.root)
    stage(root, Path(args.out) if args.out else root / ".build" / "config-studio")


if __name__ == "__main__":
    main()
