#!/usr/bin/env python3
"""Checks that track D's tool sources are reachable (mise task check:formal-network),
cross-platform. See env/probe-network.ps1 for a PowerShell equivalent with the same targets,
kept for quick manual diagnosis on Windows.

A source is probed by the file the install will fetch, never by the directory holding it. Probing
the directory reported Isabelle reachable while the pinned bundle returned 404, because a mirror
that carries only the current release still serves its index. The Isabelle target is derived from
install_native.py, so the probe and the install can never name different files."""

from __future__ import annotations

import platform
import sys
import urllib.error
import urllib.request

import install_native

OTHER_TARGETS = {
    "opam releases (GitHub API)": "https://api.github.com/repos/ocaml/opam/releases/latest",
    "Rocq opam repository": "https://rocq-prover.org/opam/released/repo",
    "Docker Hub registry": "https://registry-1.docker.io/v2/",
}


def isabelle_target() -> tuple[str, str] | None:
    """The pinned Isabelle artefact for this host, or None where no native route is scripted."""
    if platform.system() == "Windows":
        return "Isabelle pinned installer", f"{install_native.ISABELLE_MIRROR}/{install_native.ISABELLE}.exe"
    try:
        bundle = install_native.isabelle_bundle()
    except SystemExit:
        return None
    return "Isabelle pinned bundle", f"{install_native.ISABELLE_MIRROR}/{bundle}.tar.gz"


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
    targets = dict(OTHER_TARGETS)
    isabelle = isabelle_target()
    if isabelle:
        targets[isabelle[0]] = isabelle[1]
    failed = False
    for name, url in targets.items():
        status = probe(url)
        failed = failed or not status.startswith("ok")
        print(f"{name:<30} {status:<10} {url}")
    if not isabelle:
        print(f"{'Isabelle':<30} {'skipped':<10} no native route scripted for {platform.system()}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
