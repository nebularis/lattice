#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Independent verifier for vectors.json.

Recomputes every canonical N-Triples line, every digest input and every digest of the persistence conformance vectors without any
LATTICE code. It serialises N-Triples with its own code, sorts the lines by their UTF-8 bytes, builds the digest input with its own tuple
encoding and takes SHA-256 with the `openssl` command line tool. It shares nothing with the lattice-persistence library, so an
error in the library cannot be mirrored here (ADR-A132 decision 4).

The vectors it checks, per entry:
  - "ntriples": the canonical lines of a set of triples, sorted and without duplicates
  - "refusals": that a payload with the named fault really has it (a blank node, a literal subject, an IRI with a forbidden character)
  - "digests": the canonical lines of each content part, the exact bytes that are hashed (as hex) and their SHA-256

Usage: python3 verify-vectors.py [vectors.json] [--openssl PATH] [--emit]
Exit status 0 when every check passes. --emit prints the computed expectations as JSON, for authoring a new vector.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
PAT = "https://example.org/lattice/patterns#"
XSD_LONG = "http://www.w3.org/2001/XMLSchema#long"
XSD_STRING = "http://www.w3.org/2001/XMLSchema#string"
FORBIDDEN_IRI = set('<>"{}|\\^`') | {chr(c) for c in range(0, 0x21)}
CONTENT_ROLES = ("PayloadPart", "EventPart", "AddPart", "DelPart")


class Refused(Exception):
    pass


def iri(t: dict) -> str:
    v = t["iri"]
    if not v or FORBIDDEN_IRI & set(v):
        raise Refused("InvalidIri")
    return f"<{v}>"


def term(t: dict, position: str) -> str:
    if "bnode" in t:
        raise Refused("BlankNode")
    if "literal" in t:
        if position != "o":
            raise Refused("LiteralSubject")
        v = t["literal"].replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r")
        dt = t.get("datatype")
        if dt == XSD_STRING:
            dt = None
        if dt:
            return f'"{v}"^^<{dt}>'
        if t.get("language"):
            return f'"{v}"@{t["language"].lower()}'
        return f'"{v}"'
    return iri(t)


def line(tr: dict) -> str:
    return f"{term(tr['s'], 's')} {term(tr['p'], 'p')} {term(tr['o'], 'o')} ."


def canonical(triples: list) -> list:
    """Sorted by UTF-8 bytes, no duplicate. `sort -u` under LC_ALL=C gives the same order."""
    return [b.decode("utf-8") for b in sorted({line(t).encode("utf-8") for t in triples})]


def row_triples(row: dict) -> list:
    e = {"iri": row["event"]}
    return [
        {"s": e, "p": {"iri": RDF_TYPE}, "o": {"iri": row["type"]}},
        {"s": e, "p": {"iri": PAT + "opSeq"}, "o": {"literal": str(row["opSeq"]), "datatype": XSD_LONG}},
        {"s": e, "p": {"iri": PAT + "occurredAt"}, "o": row["occurredAt"]},
    ]


def part_lines(part: dict) -> list:
    triples = list(part.get("triples", []))
    for r in part.get("rows", []):
        triples += row_triples(r)
    return canonical(triples)


def enc(components: list) -> bytes:
    out = bytearray()
    for c in components:
        b = c.encode("utf-8") if isinstance(c, str) else c
        out += str(len(b)).encode("ascii") + b":" + b
    return bytes(out)


def digest_input(v: dict) -> tuple:
    roles = [p["role"] for p in v["parts"]]
    if any(r not in CONTENT_ROLES for r in roles):
        raise ValueError(f"{v['id']}: unknown role in {roles}")
    lines = [part_lines(p) for p in v["parts"]]
    data = enc([v["operationKind"], v.get("target") or "", "" if v.get("expected") is None else str(v["expected"]),
                *(enc(ls) for ls in lines)])
    return lines, data


class Openssl:
    def __init__(self, exe: str):
        self.exe = exe

    def sha256(self, data: bytes) -> str:
        out = subprocess.run([self.exe, "dgst", "-sha256"], input=data, capture_output=True, check=True).stdout
        return out.decode().strip().split()[-1]


def check(path: Path, ossl: Openssl, emit: bool) -> int:
    doc = json.loads(path.read_text(encoding="utf-8"))
    failures, passed, emitted = [], 0, {"ntriples": {}, "digests": {}}

    def ok(cond: bool, message: str) -> None:
        nonlocal passed
        if cond:
            passed += 1
        else:
            failures.append(message)

    for v in doc["ntriples"]:
        got = canonical(v["triples"])
        emitted["ntriples"][v["id"]] = got
        ok(got == v["canonical"], f"{v['id']}: canonical lines differ\n  expected {v['canonical']}\n  computed {got}")
    for v in doc["refusals"]:
        try:
            canonical(v["triples"])
            failures.append(f"{v['id']}: no fault found, expected {v['refusal']}")
        except Refused as r:
            ok(str(r) == v["refusal"], f"{v['id']}: found {r}, expected {v['refusal']}")
    for v in doc["digests"]:
        lines, data = digest_input(v)
        sha = ossl.sha256(data)
        emitted["digests"][v["id"]] = {"canonicalParts": lines, "encodedHex": data.hex(), "sha256": sha}
        ok(lines == v["canonicalParts"], f"{v['id']}: canonical parts differ")
        ok(data.hex() == v["encodedHex"], f"{v['id']}: digest input differs\n  expected {v['encodedHex']}\n  computed {data.hex()}")
        ok(sha == v["sha256"], f"{v['id']}: sha256 {sha} != {v['sha256']}")
    if emit:
        print(json.dumps(emitted, ensure_ascii=False, indent=1))
    for f in failures:
        print("FAIL", f)
    print(f"{passed} checks passed, {len(failures)} failed")
    return 1 if failures else 0


def main(argv: list) -> int:
    args, exe, emit = argv[1:], "openssl", False
    if "--openssl" in args:
        i = args.index("--openssl")
        exe = args[i + 1]
        del args[i:i + 2]
    if "--emit" in args:
        emit = True
        args.remove("--emit")
    path = Path(args[0]) if args else Path(__file__).with_name("vectors.json")
    return check(path, Openssl(exe), emit)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
