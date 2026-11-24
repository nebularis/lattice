#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI
"""Replay the behaviour tests' histories through the interpreter exported from the multi-store model, and through the RDF realisation
on Oxigraph, and report the two times (MSA-I5, the multi-store sketch's section 4.6).

1. Builds and gates the session MultiStoreModel with ``check.py multi-store-model``, which builds the prelude and the shared session first.
2. Retrieves the generated Scala from the session's export area with ``isabelle export``, into ``.build/formal/multi-store-model/``.
3. Compiles it, as generated, with the spike's driver, ``replay/Replay.scala``, by ``isabelle scalac``.
4. Writes the histories of ``replay/histories.py`` for the driver, and runs the driver in its check mode, which writes the outcome and the
   state after every command.
5. Runs the same histories on Oxigraph and reads the state back after every command, and compares the two, line for line.
6. Times both, round by round, and prints each engine's version as its own run reports it.

Fails on a difference between the two states, on an outcome the test does not state, or on a step that does not build. Never fails on
time. MULTI_STORE_REPLAY_ROUNDS sets the rounds, 200 by default.

Usage: python tools/proofs/multi_store_replay.py
"""

from __future__ import annotations

import os
import platform
import statistics
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lattice_repo_catalogue import load  # noqa: E402

CATALOGUE = load()
ROOT = CATALOGUE.root
PROOFS = ROOT / CATALOGUE.area("tools") / "proofs"
SPIKE = ROOT / CATALOGUE.area("spikes") / "multi-store-model"
DRIVER = ROOT / CATALOGUE.area("spikes") / "formal-prover" / "env" / "driver.py"
OUT = ROOT / ".build" / "formal" / "multi-store-model"
SESSION = "MultiStoreModel"


def rel(path: Path) -> str:
    """A path as an Isabelle tool takes it from tools/proofs, relative and with forward slashes."""
    return Path(os.path.relpath(path, PROOFS)).as_posix()


def isabelle(*args: str) -> subprocess.CompletedProcess:
    command = [sys.executable, str(DRIVER), "--route", "native", "--workdir", str(PROOFS), "isabelle", *args]
    return subprocess.run(command, cwd=ROOT, capture_output=True, encoding="utf-8", errors="replace")


def step(title: str, result: subprocess.CompletedProcess) -> None:
    print(f"-- {title}: exit {result.returncode}", flush=True)
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        raise SystemExit(f"{title} failed")


def ms(ns: float) -> str:
    return f"{ns / 1e6:.3f} ms"


def summary(name: str, rounds: list[int]) -> tuple[float, float]:
    cold, warm = rounds[0], rounds[1:] or rounds
    print(f"{name}: first round {ms(cold)}, later rounds mean {ms(statistics.mean(warm))}, median {ms(statistics.median(warm))}, "
          f"min {ms(min(warm))}, over {len(rounds)} rounds")
    return float(cold), float(statistics.median(warm))


def main() -> int:
    rounds = int(os.environ.get("MULTI_STORE_REPLAY_ROUNDS", "200"))
    OUT.mkdir(parents=True, exist_ok=True)

    print("-- building and gating the session", flush=True)
    built = subprocess.run([sys.executable, str(PROOFS / "check.py"), "multi-store-model"], cwd=ROOT)
    if built.returncode != 0:
        raise SystemExit("the session did not build or its gate failed")

    export = OUT / "export"
    step("isabelle export", isabelle("export", "-d", "base", "-d", "shared", "-d", rel(SPIKE), "-n", "-O", rel(export),
                                     "-x", "'*:code/**'", SESSION))
    generated = export / f"{SESSION}.Export" / "code" / "multi_store_model.scala"
    if not generated.is_file():
        raise SystemExit(f"no generated Scala at {generated}")
    print(f"   generated {generated.relative_to(ROOT).as_posix()}, {generated.stat().st_size} bytes, used as generated")

    classes = OUT / "classes"
    classes.mkdir(exist_ok=True)
    compiled = isabelle("scalac", "-d", rel(classes), rel(generated), rel(SPIKE / "replay" / "Replay.scala"))
    step("isabelle scalac", compiled)
    warnings = [line for line in (compiled.stdout + compiled.stderr).splitlines() if "Warning" in line or "warnings found" in line]
    for line in warnings:
        print(f"   {line.strip()}")

    sys.path.insert(0, str(SPIKE / "replay"))
    import histories  # noqa: E402

    tsv = OUT / "histories.tsv"
    tsv.write_text(histories.to_tsv(), encoding="utf-8", newline="\n")
    absolute = lambda p: p.resolve().as_posix()  # noqa: E731 - the JVM takes the program's arguments as Windows or POSIX paths

    scala_check = OUT / "scala-check.txt"
    step("Scala check", isabelle("scala", "-cp", rel(classes), "Replay", "check", absolute(tsv), absolute(scala_check)))
    model = scala_check.read_text(encoding="utf-8").splitlines()
    rdf = histories.rdf_check()

    def states(lines: list[str]) -> dict:
        found, name = {}, None
        for line in lines:
            parts = line.split("\t", 2)
            if parts[0] == "H":
                name = parts[1]
            elif parts[0] == "S":
                found.setdefault((name, int(parts[1])), []).append(parts[2])
        return found

    outcomes = {}
    name = None
    for line in model:
        parts = line.split("\t")
        if parts[0] == "H":
            name = parts[1]
        elif parts[0] == "O":
            outcomes[(name, int(parts[1]))] = parts[2]

    problems = []
    model_states, rdf_states = states(model), states(rdf)
    steps = [(h.name, i, c) for h in histories.HISTORIES for i, c in enumerate(h.commands, 1)]
    for hname, i, c in steps:
        got = outcomes.get((hname, i))
        if got != c.expect:
            problems.append(f"{hname} step {i}: the model's outcome is {got}, the test states {c.expect}")
        m, r = sorted(model_states.get((hname, i), [])), sorted(rdf_states.get((hname, i), []))
        if m != r:
            problems.append(f"{hname} step {i}: the states differ")
            problems += [f"   only in the model:  {x}" for x in sorted(set(m) - set(r))]
            problems += [f"   only on Oxigraph:   {x}" for x in sorted(set(r) - set(m))]
    print(f"-- check: {len(histories.HISTORIES)} histories, {len(steps)} commands, the state compared after every command")
    for hname, i, c in steps:
        print(f"   {hname} step {i} {c.op}: {outcomes.get((hname, i))}")
    if problems:
        print("\n".join(problems))
        print("CHECK: fail")
        return 1
    print("CHECK: pass, the model's state equals Oxigraph's after every command, and every outcome is the one the test states")

    scala_time = OUT / "scala-time.txt"
    step("Scala timing", isabelle("scala", "-cp", rel(classes), "Replay", "time", absolute(tsv), absolute(scala_time), str(rounds)))
    report = scala_time.read_text(encoding="utf-8").splitlines()
    scala_rounds = [int(line.split("\t")[1]) for line in report if line.startswith("round_ns\t")]
    rdf_rounds = histories.rdf_time(rounds)

    import pyoxigraph

    print("-- timing")
    for line in report:
        if not line.startswith("round_ns\t"):
            print(f"   Scala run reports: {line}")
    print(f"   Oxigraph run reports: pyoxigraph {pyoxigraph.__version__}, Python {platform.python_version()} ({platform.python_implementation()})")
    print(f"   {len(histories.HISTORIES)} histories, {len(steps)} commands a round, {rounds} rounds, each store seeded outside the clock")
    scala_cold, scala_warm = summary("   exported interpreter (Scala)", scala_rounds)
    rdf_cold, rdf_warm = summary("   RDF realisation (Oxigraph)", rdf_rounds)
    print(f"   ratio, interpreter over RDF: first round {scala_cold / rdf_cold:.3f}, later rounds (median) {scala_warm / rdf_warm:.3f}")
    print(f"   within ten times the RDF realisation's time: first round {'yes' if scala_cold <= 10 * rdf_cold else 'no'}, "
          f"later rounds {'yes' if scala_warm <= 10 * rdf_warm else 'no'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
