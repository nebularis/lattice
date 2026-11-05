# SPDX-License-Identifier: MPL-2.0
"""The studio's HTTP API under a fixed scenario, one report per run (ADR-A124, ADR-A150).

Starts the `single` topology on the `processes` runner through the harness, creates a workspace and measures, by the time of each reply:
- saving a part of 100, 1,000 and 3,000 triples and reading it back after each save, 10 times each
- listing the workspaces, 20 times
- publishing a concept scheme with a changed label, 5 times, as its job, its publication and the registry listing that follows

It uses only routes the studio had before phase D of the publication unit and has now, and waits for no promotion. Two warm-up repeats of each measure are discarded.
**A wrong reply or a wrong read-back fails the run. Time never does.** `--checkout PATH` measures another checkout of the repository, whose jars, staged assets and
worker code are used (see the harness README), and names the report for that checkout's commit."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

from lattice_testing_studio_harness import Topology, reports
from lattice_testing_studio_harness._build import ASSETS_ENV, JARS_ENV, WORKER_ROOT_ENV
from lattice_testing_studio_harness._tools import catalogue
from lattice_testing_studio_harness.client import Client, Reply
from lattice_testing_studio_harness.scenarios import SCHEME, SKOS, vocabulary

BENCHMARK = "studio-api"
SIZES = (100, 1_000, 3_000)
SAVES, LISTS, PUBLISHES, WARMUP = 10, 20, 5, 2


class WrongResult(AssertionError):
    """A reply or a read-back that is not what the studio should give. This is the one way the run fails."""


def expect(what: str, reply: Reply, *statuses: int) -> Reply:
    if reply.status not in statuses:
        raise WrongResult(f"{what}: expected {'/'.join(map(str, statuses))}, got {reply.status}: {reply.text[:300]}")
    return reply


def part(size: int, tag: str) -> str:
    """A concept scheme of exactly `size` triples. It has two triples of its own, five for each concept (the type, its scheme, a label, a note that is a blank node, and that
    blank node's label), and alternative labels on the first concept for the remainder. `tag` is in the scheme's label, so each save differs from the last in one triple."""
    out = [SKOS + f'<{SCHEME}> a skos:ConceptScheme ; skos:prefLabel "{tag}" .']
    count, i = 2, 0
    while count + 5 <= size:
        out.append(f'ex:c{i} a skos:Concept ; skos:inScheme <{SCHEME}> ; skos:prefLabel "Concept {i}" ; skos:note [ skos:prefLabel "Note {i}" ] .')
        count, i = count + 5, i + 1
    for j in range(size - count):
        out.append(f'ex:c0 skos:altLabel "Alternative {j}" .')
    return "\n".join(out) + "\n"


def triples(turtle: str) -> int:
    from rdflib import Graph
    return len(Graph().parse(data=turtle, format="turtle"))


class Samples:
    """The timed repeats of each measure, in milliseconds, the warm-up repeats left out."""

    def __init__(self) -> None:
        self.values: Dict[str, List[float]] = {}

    def add(self, name: str, reply: Reply, repeat: int) -> None:
        if repeat >= WARMUP:
            self.values.setdefault(name, []).append(reply.nanos / 1e6)

    def measures(self) -> List[dict]:
        return [reports.measure(name, "ms", values) for name, values in self.values.items()]


def scenario(client: Client) -> Samples:
    samples = Samples()
    ws = Client.workspace_id(expect("create workspace", client.create_workspace("Benchmark"), 201))
    revision = 0
    for size in SIZES:
        for i in range(WARMUP + SAVES):
            tag = f"{size} triples, save {i}"
            turtle = part(size, tag)
            saved = expect(f"save {size}", client.save_part(ws, "vocabulary", turtle, revision), 204)
            revision += 1
            if saved.revision != revision:
                raise WrongResult(f"save {size}: revision {saved.revision}, expected {revision}")
            samples.add(f"save part, {size} triples", saved, i)
            read = expect(f"read {size}", client.read_part(ws, "vocabulary"), 200)
            if tag not in read.text or triples(read.text) != size:
                raise WrongResult(f"read {size}: the part read back is not the one saved ({triples(read.text)} triples, expected {size})")
            samples.add(f"read part, {size} triples", read, i)
    for i in range(WARMUP + LISTS):
        listed = expect("list workspaces", client.list_workspaces(), 200)
        if ws not in listed.text:
            raise WrongResult("list workspaces: the workspace is not listed")
        samples.add("list workspaces", listed, i)

    pub = Client.workspace_id(expect("create publishing workspace", client.create_workspace("Benchmark publishing"), 201))
    revision = 0
    for i in range(WARMUP + PUBLISHES):
        label = f"label {i}"
        saved = expect("save scheme", client.save_part(pub, "vocabulary", vocabulary(label), revision), 204)
        revision = saved.revision or revision + 1
        submitted = expect("submit publish job", client.submit_job(pub, "publish", "vocabulary", unit=SCHEME), 202)
        job = Client.job_id(submitted)
        done = expect("wait for publish job", client.wait_job(job), 200)
        if "Succeeded" not in done.text:
            raise WrongResult(f"the publish job failed: {done.text[:300]}")
        samples.add("publish job (submit to done)", done, i)
        published = expect("publish", client.publish(pub, job), 200, 201)
        samples.add("publish", published, i)
        registry = expect("list registry", client.registry(), 200)
        if SCHEME not in registry.text:
            raise WrongResult(f"list registry: the published scheme is not listed: {registry.text[:300]}")
        samples.add("list registry", registry, i)
    return samples


def dirty(checkout: Path) -> bool:
    return bool(subprocess.run(["git", "-C", str(checkout), "status", "--porcelain"], capture_output=True, text=True).stdout.strip())


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--checkout", help="another checkout of the repository to measure, with its jars built and its assets staged. Default: this one")
    args = parser.parse_args(argv)
    root = catalogue.find_root()
    checkout = Path(args.checkout).resolve() if args.checkout else root
    if checkout != root:
        os.environ[JARS_ENV] = str(checkout / "platform")
        os.environ[ASSETS_ENV] = str(checkout / ".build" / "config-studio")
        os.environ[WORKER_ROOT_ENV] = str(checkout)
    kind = reports.machine()  # before the studio starts, so the load average is that of the machine and not of the run
    topology = Topology.load(root / "test" / "studio-integration" / "topologies" / "single.toml")
    with topology.start(runner="processes", root=root) as studio:
        samples = scenario(studio.client())
    notes = f"topology {topology.name} ({topology.writers} writer, {topology.workers} worker, {topology.store}), processes runner. Repeats after {WARMUP} discarded warm-up repeats"
    if dirty(checkout):
        notes += ". The checkout had uncommitted changes"
    path = reports.write(reports.build(BENCHMARK, reports.short_commit(checkout), samples.measures(), kind, notes=notes), root)
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
