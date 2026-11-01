# SPDX-License-Identifier: MPL-2.0
"""Scenarios written against the client. Each returns its steps with the time each took, and raises `ScenarioError` naming the step whose reply was not the expected one."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .client import Client, Reply

SCHEME = "https://example.org/harness/scheme"
SKOS = "@prefix skos: <http://www.w3.org/2004/02/skos/core#> .\n@prefix ex: <https://example.org/harness/> .\n"


class ScenarioError(AssertionError):
    pass


@dataclass(frozen=True)
class Step:
    name: str
    status: int
    nanos: int


def vocabulary(label: str) -> str:
    """A concept scheme with one concept, which is the smallest unit a workspace can publish."""
    return (SKOS + f'<{SCHEME}> a skos:ConceptScheme ; skos:prefLabel "{label} scheme" .\n'
            f'ex:c1 a skos:Concept ; skos:inScheme <{SCHEME}> ; skos:prefLabel "{label} concept" .\n')


class _Run:
    def __init__(self) -> None:
        self.steps: List[Step] = []

    def expect(self, name: str, reply: Reply, *statuses: int) -> Reply:
        self.steps.append(Step(name, reply.status, reply.nanos))
        if reply.status not in statuses:
            raise ScenarioError(f"{name}: expected {'/'.join(map(str, statuses))}, got {reply.status}: {reply.text[:400]}")
        return reply

    def check(self, name: str, ok: bool, detail: str) -> None:
        if not ok:
            raise ScenarioError(f"{name}: {detail}")


def smoke(client: Client) -> List[Step]:
    """Create, save twice, a stale save refused with 412, read revision 1, publish, list the registry, lock, delete."""
    run = _Run()
    created = run.expect("create workspace", client.create_workspace("Smoke"), 201)
    ws = client.workspace_id(created)
    run.check("create workspace", bool(ws), "no Location")
    listed = run.expect("list workspaces", client.list_workspaces(), 200)
    run.check("list workspaces", ws in listed.text, "the new workspace is not listed")

    first = run.expect("save part (first)", client.save_part(ws, "vocabulary", vocabulary("first"), 0), 204)
    run.check("save part (first)", first.revision == 1, f"revision {first.revision}, expected 1")
    second = run.expect("save part (second)", client.save_part(ws, "vocabulary", vocabulary("second"), 1), 204)
    run.check("save part (second)", second.revision == 2, f"revision {second.revision}, expected 2")
    run.expect("save part (stale)", client.save_part(ws, "vocabulary", vocabulary("stale"), 1), 412)
    old = run.expect("read revision 1", client.read_part(ws, "vocabulary", 1), 200)
    run.check("read revision 1", "first concept" in old.text and "second concept" not in old.text, "revision 1 is not the first save")
    current = run.expect("read part", client.read_part(ws, "vocabulary"), 200)
    run.check("read part", "second concept" in current.text, "the current revision is not the second save")

    submitted = run.expect("submit publish job", client.submit_job(ws, "publish", "vocabulary", unit=SCHEME), 202)
    job = client.job_id(submitted)
    done = client.wait_job(job)
    run.expect("wait for publish job", done, 200)
    run.check("wait for publish job", "Succeeded" in done.text, f"the job failed: {done.text[:400]}")
    published = run.expect("publish", client.publish(ws, job), 200, 201)

    # Publishing waits for its rebuild (ADR-A149 decision 14), so the registry and the terms show it at once.
    listing = run.expect("list registry", client.registry(), 200)
    run.check("list registry", SCHEME in listing.text, f"the published scheme is not listed: {listing.text[:400]}")
    terms = run.expect("search terms", client.registry_terms("second concept"), 200)
    run.check("search terms", "second concept" in terms.text, f"the published concept is not found: {terms.text[:400]}")

    run.expect("lock", client.set_access(ws, "locked"), 200)
    run.expect("delete", client.delete_workspace(ws), 204)
    run.expect("read after delete", client.get_workspace(ws), 404)
    return run.steps
