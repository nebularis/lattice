#!/usr/bin/env python3
"""Checks that track D's tool sources are reachable (mise task check:formal-network),
cross-platform. See env/probe-network.ps1 for a PowerShell equivalent with the same targets,
kept for quick manual diagnosis on Windows."""

from __future__ import annotations

import sys
import urllib.error
import urllib.request

TARGETS = {
    "opam releases (GitHub API)": "https://api.github.com/repos/ocaml/opam/releases/latest",
    "Rocq opam repository": "https://rocq-prover.org/opam/released/repo",
    "Isabelle Cambridge mirror": "https://www.cl.cam.ac.uk/research/hvg/Isabelle/dist/",
    "Docker Hub registry": "https://registry-1.docker.io/v2/",
}

BLOCK_MARKERS = ("Block Notice", "Not allowed to browse", "cgi-bin/notice")


def probe(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(url, headers={"Range": "bytes=0-65535"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(65536).decode("utf-8", "replace")
            final_url = resp.geturl()
    except urllib.error.HTTPError as exc:
        if exc.code == 401:  # the normal anonymous challenge from a container registry
            return "ok"
        body = exc.read().decode("utf-8", "replace") if exc.fp else ""
        final_url = str(exc.url or url)
        if any(m in body for m in BLOCK_MARKERS) or any(m in final_url for m in BLOCK_MARKERS):
            return "BLOCKED"
        return f"FAIL ({exc.code})"
    except Exception as exc:  # noqa: BLE001 - reported as a probe result, not raised
        return f"FAIL ({exc})"
    if any(m in body for m in BLOCK_MARKERS) or any(m in final_url for m in BLOCK_MARKERS):
        return "BLOCKED"
    return "ok"


def main() -> int:
    failed = False
    for name, url in TARGETS.items():
        status = probe(url)
        failed = failed or not status.startswith("ok")
        print(f"{name:<30} {status:<10} {url}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
