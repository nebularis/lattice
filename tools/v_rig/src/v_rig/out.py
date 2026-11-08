# SPDX-License-Identifier: MPL-2.0
"""Where a run's outputs go, and the guard on it. Everything derived from a rig is written under a path git reports as
ignored, by default `.local/v-rig/<rig digest>/` in the checkout, never under the rig, and the tool refuses any other
kind of path. The deny list it writes beside them is fed to the deny-terms check by naming the file."""

from __future__ import annotations

import json
import logging
import re
import subprocess
import sys
from pathlib import Path

from rdflib import RDF, Graph, Literal

from .lift import VRIG, blind, canonical_turtle, findings_graph
from .rig import Rig

log = logging.getLogger("v_rig")


class OutError(Exception):
    """An output path the tool refuses."""


def repository_root() -> Path:
    """The checkout the tool runs in, found by the repository catalogue's reader."""
    try:
        import lattice_repo_catalogue as reader
    except ImportError as error:
        raise OutError("the repository catalogue reader is not importable, so the checkout cannot be found: run the tool "
                       "through mise from inside the checkout") from error
    return reader.load().root


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, encoding="utf-8")


def is_ignored(root: Path, path: Path) -> bool:
    try:
        relative = path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return _git(root, "check-ignore", "-q", relative.as_posix()).returncode == 0


def resolve_out(rig: Rig, out: Path | str | None, root: Path | None = None) -> Path:
    """The output directory for a run, checked: inside the checkout, ignored by git, and not under the rig."""
    root = (root or repository_root()).resolve()
    path = (Path(out).expanduser() if out else root / ".local" / "v-rig" / rig.digest).resolve()
    rig_root = rig.root.resolve()
    if path == rig_root or rig_root in path.parents:
        raise OutError(f"the output path {path} is inside the rig, and the tool never writes inside a rig")
    if not is_ignored(root, path):
        raise OutError(f"the output path {path} is not a path git ignores in {root}, and everything derived from a rig "
                       "is written only under an ignored path")
    return path


def deny_terms(graph: Graph) -> list[str]:
    """One regular expression per line a staged change must not carry: every id, title, string value and body text of the
    rig, escaped, longest first, so that no rig text reaches a tracked line."""
    terms: set[str] = set()
    for predicate in (VRIG.rigId, VRIG["title"], VRIG.text, VRIG["term"], VRIG.value, VRIG.expression, VRIG.referenceText, RDF.first):
        for obj in graph.objects(None, predicate):
            if not isinstance(obj, Literal):
                continue
            text = str(obj)
            if len(text) >= 4 and not re.fullmatch(r"[\d.,:\- ]+", text):
                terms.add(re.escape(text))
    return sorted(terms, key=lambda t: (-len(t), t))


def write_outputs(rig: Rig, graph: Graph, out: Path, run_info: dict, projection=None) -> dict[str, Path]:
    out.mkdir(parents=True, exist_ok=True)
    if projection is not None:
        (out / "p1").mkdir(exist_ok=True)
        (out / "p1" / "source.ttl").write_text(canonical_turtle(projection.source), encoding="utf-8")
        (out / "p1" / "layers.ttl").write_text(canonical_turtle(projection.layers), encoding="utf-8")
        (out / "p1" / "compiled.sparql").write_text(projection.compiled_text + "\n", encoding="utf-8")
    written = {
        "ir": out / "ir.ttl",
        "blind": out / "blind.ttl",
        "findings": out / "findings.ttl",
        "run": out / "run.json",
        "deny-terms": out / "deny-terms",
    }
    written["ir"].write_text(canonical_turtle(graph), encoding="utf-8")
    written["blind"].write_text(canonical_turtle(blind(graph)), encoding="utf-8")
    written["findings"].write_text(canonical_turtle(findings_graph(graph)), encoding="utf-8")
    written["run"].write_text(json.dumps(run_info, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    header = ["# Generated from a rig by the v-rig tool. Feed it to the deny-terms check with",
              f"# LATTICE_DENY_TERMS={written['deny-terms']} mise run check:deny-terms", ""]
    written["deny-terms"].write_text("\n".join(header + deny_terms(graph)) + "\n", encoding="utf-8")
    if projection is not None:
        written.update({"p1 source": out / "p1" / "source.ttl", "p1 layers": out / "p1" / "layers.ttl", "p1 compiled": out / "p1" / "compiled.sparql"})
    log.info("wrote %d file(s) under %s", len(written), out)
    return written


def counts(graph: Graph) -> dict[str, int]:
    return {local: len(set(graph.subjects(RDF.type, VRIG[local])))
            for local in ("Document", "Fact", "BodyNode", "Reference", "Programme", "Layer", "Placement", "Event", "Finding")}
