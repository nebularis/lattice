# SPDX-License-Identifier: MPL-2.0
"""A client over the studio's HTTP API whose methods are the studio's actions (contracts/config-studio/README.md).

Every method returns a `Reply` and never raises on a status, so a test asserts on the status it expects. Each request opens its own connection, so a client can be shared by threads."""

from __future__ import annotations

import http.client
import re
import time
import urllib.parse
from dataclasses import dataclass, field
from typing import Dict, Iterable, Optional

CST = "https://www.nebularis.org/neuro-semantic/lattice/config-studio#"
TURTLE = "text/turtle; charset=utf-8"


@dataclass(frozen=True)
class Reply:
    status: int
    body: bytes
    headers: Dict[str, str] = field(default_factory=dict)
    nanos: int = 0

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")

    @property
    def location(self) -> str:
        return self.headers.get("location", "")

    @property
    def revision(self) -> Optional[int]:
        """The revision an `ETag: "n"` names."""
        etag = self.headers.get("etag", "").strip('"')
        return int(etag) if etag.isdigit() else None


class Client:
    def __init__(self, base_url: str, principal: str = "developer", timeout: float = 60.0) -> None:
        parts = urllib.parse.urlsplit(base_url)
        self.host, self.port = parts.hostname or "127.0.0.1", parts.port or 80
        self.principal = principal
        self.timeout = timeout

    def request(self, method: str, path: str, body: bytes | str = b"", headers: Optional[Dict[str, str]] = None) -> Reply:
        data = body.encode("utf-8") if isinstance(body, str) else body
        sent = {"X-Lattice-Principal": self.principal, **(headers or {})}
        connection = http.client.HTTPConnection(self.host, self.port, timeout=self.timeout)
        start = time.perf_counter_ns()
        try:
            connection.request(method, path, body=data or None, headers=sent)
            response = connection.getresponse()
            content = response.read()
            elapsed = time.perf_counter_ns() - start
            return Reply(response.status, content, {k.lower(): v for k, v in response.getheaders()}, elapsed)
        finally:
            connection.close()

    # --- workspaces ------------------------------------------------------------------------------

    def health(self) -> Reply:
        return self.request("GET", "/api/health")

    def create_workspace(self, label: str = "Harness", baseline: str = "", sample: Optional[str] = None) -> Reply:
        """`baseline` is Turtle, which may carry the `cst:` prefix. The new workspace's id is `workspace_id(reply)`."""
        query = f"?sample={urllib.parse.quote(sample)}" if sample else ""
        return self.request("POST", f"/api/workspaces{query}", baseline or "@prefix ex: <https://example.org/> .\nex:a ex:p ex:b .\n",
                            {"Content-Type": TURTLE, "Slug": urllib.parse.quote(label)})

    @staticmethod
    def workspace_id(reply: Reply) -> str:
        return reply.location.rsplit("/", 1)[-1]

    def list_workspaces(self) -> Reply:
        return self.request("GET", "/api/workspaces", headers={"Accept": "text/turtle"})

    def get_workspace(self, ws: str) -> Reply:
        return self.request("GET", f"/api/workspaces/{ws}", headers={"Accept": "text/turtle"})

    def delete_workspace(self, ws: str) -> Reply:
        return self.request("DELETE", f"/api/workspaces/{ws}")

    def export_workspace(self, ws: str) -> Reply:
        return self.request("GET", f"/api/workspaces/{ws}/export")

    # --- parts -----------------------------------------------------------------------------------

    def read_part(self, ws: str, name: str, revision: Optional[int] = None) -> Reply:
        query = "" if revision is None else f"?revision={revision}"
        return self.request("GET", f"/api/workspaces/{ws}/graphs/{name}{query}", headers={"Accept": "text/turtle"})

    def save_part(self, ws: str, name: str, turtle: str, revision: int) -> Reply:
        """`revision` is the one the caller read, `0` for a part not yet saved. A stale one answers `412`."""
        return self.request("PUT", f"/api/workspaces/{ws}/graphs/{name}", turtle, {"Content-Type": TURTLE, "If-Match": f'"{revision}"'})

    # --- access and dependencies -----------------------------------------------------------------

    def set_access(self, ws: str, mode: str, owner: Optional[str] = None) -> Reply:
        query = f"mode={urllib.parse.quote(mode)}" + (f"&owner={urllib.parse.quote(owner)}" if owner else "")
        return self.request("POST", f"/api/workspaces/{ws}/access?{query}")

    def set_dependencies(self, ws: str, iris: Iterable[str]) -> Reply:
        objects = " , ".join(f"<{iri}>" for iri in iris)
        body = f"@prefix cst: <{CST}> .\n<urn:lattice:studio:ws:{ws}> " + (f"cst:dependsOn {objects} .\n" if objects else "a cst:Workspace .\n")
        return self.request("PUT", f"/api/workspaces/{ws}/dependencies", body, {"Content-Type": TURTLE})

    # --- jobs and publication --------------------------------------------------------------------

    def submit_job(self, ws: str, kind: str, target: str, body: bytes | str = b"", **params: str) -> Reply:
        query = urllib.parse.urlencode({"kind": kind, "target": target, **params})
        return self.request("POST", f"/api/workspaces/{ws}/jobs?{query}", body, {"Content-Type": TURTLE})

    @staticmethod
    def job_id(reply: Reply) -> str:
        return reply.location.rsplit("/", 1)[-1]

    def get_job(self, job: str) -> Reply:
        return self.request("GET", f"/api/jobs/{job}", headers={"Accept": "text/turtle"})

    def wait_job(self, job: str, timeout: float = 120.0, interval: float = 0.1) -> Reply:
        """Polls the job until it has `cst:Succeeded` or `cst:Failed`. The reply is the last read, with `nanos` the whole wait. Raises `TimeoutError` otherwise."""
        start = time.perf_counter_ns()
        deadline = time.monotonic() + timeout
        while True:
            reply = self.get_job(job)
            if reply.status == 200 and re.search(r"(?:cst:|config-studio#)(?:Succeeded|Failed)\b", reply.text):
                return Reply(reply.status, reply.body, reply.headers, time.perf_counter_ns() - start)
            if time.monotonic() > deadline:
                raise TimeoutError(f"job {job} did not finish within {timeout:.0f} s: {reply.status} {reply.text[:300]}")
            time.sleep(interval)

    def publish(self, ws: str, job: str) -> Reply:
        return self.request("POST", f"/api/workspaces/{ws}/publications?job={job}")

    def delete_job(self, job: str) -> Reply:
        return self.request("DELETE", f"/api/jobs/{job}")

    # --- the registry ----------------------------------------------------------------------------

    def registry(self) -> Reply:
        """Every published lineage with its current version, read from the registry projection."""
        return self.request("GET", "/api/registry", headers={"Accept": "text/turtle"})

    def registry_terms(self, text: str) -> Reply:
        return self.request("GET", "/api/registry/terms?q=" + urllib.parse.quote(text), headers={"Accept": "text/turtle"})

    def registry_holders(self, iri: str) -> Reply:
        return self.request("GET", "/api/registry/holders?iri=" + urllib.parse.quote(iri, safe=""), headers={"Accept": "text/turtle"})

    def registry_bundle(self, version: str) -> Reply:
        return self.request("GET", "/api/registry/bundle?iri=" + urllib.parse.quote(version, safe=""))
