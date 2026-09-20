"""CLI for deterministic structural MORK Teaching Pack generation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from . import doctrine, lens, lock, partition, render, routing
from .cassette import validate as validate_cassette
from .corpus import predicate_counts
from .facts import extract
from .mcnio import InProcessTool
from .mutate import evaluate, seed_mutations


def repository_root() -> Path:
    return Path(__file__).resolve().parents[4]


def build(out: Path, pack_version: str) -> int:
    root = repository_root()
    data = root / "mork" / "mtp" / "data"
    facts = extract(root / "mork" / "spec" / "Mork.ttl")
    doctrine_data = doctrine.load(data / "doctrine.yaml")
    partition_data = yaml.safe_load((data / "partition.yaml").read_text(encoding="utf-8"))
    out.mkdir(parents=True, exist_ok=True)
    l0 = render.render_l0(doctrine_data, facts)
    (out / "l0.txt").write_text(l0, encoding="utf-8")
    (out / "l0.json").write_text(json.dumps({"ontologyHash": facts.graph_hash, "termCount": len(facts.terms), "axiomCount": len(facts.axioms)}, indent=2) + "\n", encoding="utf-8")
    (out / "pairs.md").write_text("# Minimal pairs\n\n" + "\n".join(f"- {pair}" for pair in doctrine_data.get("minimal_pairs", [])) + "\n", encoding="utf-8")
    (out / "output_contract.txt").write_text("Use typed MCN code, reference, and minting positions. Keep confidence and uncertainty separate.\n", encoding="utf-8")
    counts = predicate_counts(root / "mork" / "examples")
    (out / "stats.md").write_text("# Corpus statistics\n\n" + "\n".join(f"- `{predicate}`: {count}" for predicate, count in counts.most_common(20)) + "\n", encoding="utf-8")
    lenses = [yaml.safe_load(path.read_text(encoding="utf-8")) for path in sorted((data / "lenses").glob("*.yaml"))]
    lens_dir = out / "lenses"
    lens_dir.mkdir(exist_ok=True)
    for item in lenses:
        (lens_dir / f"{item['id']}.txt").write_text(lens.render(item), encoding="utf-8")
    routes = yaml.safe_load((data / "routing.yaml").read_text(encoding="utf-8"))["routes"]
    (out / "routing.yaml").write_text(yaml.safe_dump({"routes": routes}, sort_keys=True), encoding="utf-8")
    cassette_dir = out / "cassettes"
    cassette_dir.mkdir(exist_ok=True)
    cassettes = [yaml.safe_load(path.read_text(encoding="utf-8")) for path in sorted((data / "cassettes").glob("*.yaml"))]
    outcomes = []
    tool = InProcessTool()
    for cassette in cassettes:
        (cassette_dir / f"{cassette['id']}.txt").write_text(cassette["mcn"] + "\n", encoding="utf-8")
        outcomes.extend({"cassette": cassette["id"], "mutation": outcome.mutation, "verdict": outcome.verdict, "codes": outcome.codes} for outcome in (evaluate(mutation, tool) for mutation in seed_mutations(cassette["mcn"])))
    (out / "diagnostics.json").write_text(json.dumps(outcomes, indent=2) + "\n", encoding="utf-8")
    (out / "partition.md").write_text("# Partition\n\nDefault lens: " + partition_data["defaultLens"] + "\n", encoding="utf-8")
    pins = {"ontology": facts.graph_hash, **{f"term:{term.iri}": term.logical_hash for term in facts.terms}}
    lock.write(data / "pins.lock.json", pins)
    files = [path for path in out.rglob("*") if path.is_file() and path.name != "manifest.json"]
    render.write_manifest(out, files, pack_version)
    return 0


def check(out: Path) -> int:
    root = repository_root()
    data = root / "mork" / "mtp" / "data"
    facts = extract(root / "mork" / "spec" / "Mork.ttl")
    doctrine_data = doctrine.load(data / "doctrine.yaml")
    findings = doctrine.check(doctrine_data, facts)
    expected = lock.read(data / "pins.lock.json")
    actual = {"ontology": facts.graph_hash, **{f"term:{term.iri}": term.logical_hash for term in facts.terms}}
    findings.extend(f"pin.changed:{key}" for key in lock.drift(expected, actual))
    partition_data = yaml.safe_load((data / "partition.yaml").read_text(encoding="utf-8"))
    findings.extend(partition.check(partition_data, facts))
    lenses = [yaml.safe_load(path.read_text(encoding="utf-8")) for path in sorted((data / "lenses").glob("*.yaml"))]
    findings.extend(lens.check(lenses))
    routes = yaml.safe_load((data / "routing.yaml").read_text(encoding="utf-8"))["routes"]
    findings.extend(routing.check(routes, {item["id"] for item in lenses}))
    tool = InProcessTool()
    for cassette_path in sorted((data / "cassettes").glob("*.yaml")):
        cassette = yaml.safe_load(cassette_path.read_text(encoding="utf-8"))
        valid, codes = validate_cassette(cassette, root, tool)
        if not valid:
            findings.append(f"cassette.not-isomorphic:{cassette['id']}:{','.join(codes)}")
    findings.extend(render.manifest_drift(out) if out.exists() else ["output.stale:missing"])
    if findings:
        print("\n".join(sorted(findings)))
        return 1
    print("MTP structural checks passed")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mtp")
    parser.add_argument("command", choices=["facts-report", "build", "check", "update-pins"])
    parser.add_argument("--out", type=Path, default=repository_root() / "mork" / "mtp" / "out")
    parser.add_argument("--pack-version", default="0.1.0")
    args = parser.parse_args(argv)
    if args.command == "facts-report":
        facts = extract(repository_root() / "mork" / "spec" / "Mork.ttl")
        print(json.dumps({"terms": len(facts.terms), "axioms": len(facts.axioms), "graphHash": facts.graph_hash}, indent=2))
        return 0
    if args.command == "build": return build(args.out, args.pack_version)
    if args.command == "update-pins":
        return build(args.out, args.pack_version)
    return check(args.out)


if __name__ == "__main__":
    raise SystemExit(main())