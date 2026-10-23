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
  - "payloadChecks": the subjects of a payload that are neither the root nor reached from it by the owned edges of the shape
  - "eventChecks": the refusals of an append's rows and of its event triples
  - "callerChecks": the refusals of a request's parameters, of an xsd:long that is not exactly one, of a caller-named graph and of the log graphs
  - "auditOutcomes": clean, failed or nothing examined
  - "referenceChecks": an object on a pinned edge is a version and on an identity edge is not
  - "checkpointChecks": a checkpoint version lists every member

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


# ---- the payload checks (H2.8b). Each is written here from the rules of ADR-A123 and its addenda, and shares nothing with the library.


def spo(t: dict) -> tuple:
    """(subject, predicate, object) as plain IRI strings, the object None where it is a literal."""
    return t["s"]["iri"], t["p"]["iri"], t["o"].get("iri")


def walk(v: dict, owned_only: bool = True) -> set:
    """The (node, shape) states reached from the root, following edges from the shape a state is in, forward or inverse, over the payload alone."""
    if v["shape"] is None:
        return set()
    triples = [spo(t) for t in v["triples"]]
    edges = [e for e in v["edges"] if e["ownership"] == "Owned" or not owned_only]
    seen, todo = {(v["root"], v["shape"])}, [(v["root"], v["shape"])]
    while todo:
        node, shape = todo.pop()
        for e in edges:
            if e["source"] != shape:
                continue
            for s, p, o in triples:
                if p != e["predicate"] or o is None:
                    continue
                if e["inverse"]:
                    nxt = s if o == node else None
                else:
                    nxt = o if s == node else None
                if nxt is not None and (nxt, e["targetShape"]) not in seen:
                    seen.add((nxt, e["targetShape"]))
                    todo.append((nxt, e["targetShape"]))
    return seen


def outside(v: dict) -> list:
    if v["shape"] is None:
        return []
    reached = {n for n, _ in walk(v)}
    return sorted({s for s, _, _ in (spo(t) for t in v["triples"])} - reached)


def event_refusals(v: dict) -> list:
    out = set()
    rows = v["events"]
    if any(r["event"] is None or r["type"] is None or r["opSeq"] is None or r["occurredAt"] is None for r in rows):
        out.add("UndefInRow")
    rows = [r for r in rows if r["event"] is not None]
    if not rows:
        out.add("NoEvents")
    names = [r["event"] for r in rows]
    if len(set(names)) != len(names):
        out.add("DuplicateEvent")
    seqs = [r["opSeq"] for r in rows]
    if len(set(seqs)) != len(seqs):
        out.add("DuplicateOpSeq")
    for s, _, _ in (spo(t) for t in v["triples"]):
        if not any(s == n or s.startswith(n + "/part/") for n in names):
            out.add("EventOutsideBound")
    return sorted(out)


def encode_for_uri(text: str) -> str:
    return "".join(chr(b) if (chr(b).isascii() and (chr(b).isalnum() or chr(b) in "-_.~")) else f"%{b:02X}" for b in text.encode("utf-8"))


LONG_MIN, LONG_MAX = -(2 ** 63), 2 ** 63 - 1


def kind_refusal(kind: str, value: dict) -> str | None:
    """The refusal code for a value of the wrong kind, or None."""
    form = next(iter(value))
    if kind == "Iri":
        return None if form == "iri" and value["iri"] and not (FORBIDDEN_IRI & set(value["iri"])) else "WrongKind"
    if kind in ("Long", "Position"):
        if form == "int":
            return None if LONG_MIN <= value["int"] <= LONG_MAX else "IllTypedLiteral"
        if form != "literal":
            return "WrongKind"
        if value.get("datatype") != XSD_LONG:
            return "NotXsdLong"
        text = value["literal"]
        digits = text[1:] if text[:1] in "+-" else text
        return None if digits.isascii() and digits.isdigit() and LONG_MIN <= int(text) <= LONG_MAX else "IllTypedLiteral"
    if kind == "Digest":
        t = value.get("string")
        return None if t is not None and len(t) == 64 and all(c in "0123456789abcdef" for c in t) else "WrongKind"
    if kind == "RegistryList":
        return None if form == "strings" else "WrongKind"
    return "WrongKind"


def caller_refusals(v: dict) -> list:
    op, values, out = v["operation"], v["values"], set()
    declared = {p["name"]: p for p in op["parameters"]}
    for name in values:
        if name not in declared:
            out.add("UnknownParameter")
    for name, p in declared.items():
        if name not in values:
            if p["required"]:
                out.add("MissingParameter")
            continue
        bad = kind_refusal(p["kind"], values[name])
        if bad:
            out.add(bad)
        elif p["kind"] == "RegistryList":
            members = values[name]["strings"]
            if not members and not v.get("allowEmptyLogGraphs"):
                out.add("EmptyLogGraphs")
            if any(not m or FORBIDDEN_IRI & set(m) for m in members):
                out.add("LogGraphNotIri")
        if p.get("equalsGraphName") and "root" in values and kind_refusal("Iri", values["root"]) is None and bad is None:
            expected = op["graphPrefix"] + encode_for_uri(values["root"]["iri"]) + op["graphSuffix"]
            if values[name]["iri"] != expected:
                out.add("GraphNameMismatch")
    return sorted(out)


def audit_outcome(v: dict) -> str:
    if v["rows"] > 0:
        return "Failed"
    if (v["logGraphs"] is not None and len(v["logGraphs"]) == 0) or v["examined"] == 0:
        return "NothingExamined"
    return "Clean"


def reference_refusals(v: dict) -> list:
    versions, out = set(v["versions"]), set()
    triples = [spo(t) for t in v["triples"]]
    for node, shape in walk(v):
        for e in v["edges"]:
            if e["source"] != shape:
                continue
            for s, p, o in triples:
                if p != e["predicate"] or o is None:
                    continue
                if e["inverse"]:
                    target = s if o == node else None
                else:
                    target = o if s == node else None
                if target is None:
                    continue
                if e["mode"] == "Pinned" and target not in versions:
                    out.add("ReferenceModeViolation")
                if e["mode"] == "ByIdentity" and target in versions:
                    out.add("ReferenceModeViolation")
    return sorted(out)


def checkpoint_refusals(v: dict) -> list:
    version, prop = v["version"], v["membershipProperty"]
    listed = {o for s, p, o in map(spo, v["triples"]) if s == version and p == prop and o is not None}
    marked = any(t["s"]["iri"] == version and t["p"]["iri"] == PAT + "checkpoint" and t["o"].get("literal") == "true" for t in v["triples"])
    if v["checkpoint"]:
        return [] if marked and listed == set(v["members"]) else ["CheckpointNotFull"]
    return ["UnexpectedFullList"] if marked or listed else []


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
    for v in doc["payloadChecks"]:
        ok(outside(v) == v["outside"], f"{v['id']}: outside {outside(v)}, expected {v['outside']}")
    for v in doc["eventChecks"]:
        ok(event_refusals(v) == v["refusals"], f"{v['id']}: {event_refusals(v)}, expected {v['refusals']}")
    for v in doc["callerChecks"]:
        ok(caller_refusals(v) == v["refusals"], f"{v['id']}: {caller_refusals(v)}, expected {v['refusals']}")
    for v in doc["auditOutcomes"]:
        ok(audit_outcome(v) == v["outcome"], f"{v['id']}: {audit_outcome(v)}, expected {v['outcome']}")
    for v in doc["referenceChecks"]:
        ok(reference_refusals(v) == v["refusals"], f"{v['id']}: {reference_refusals(v)}, expected {v['refusals']}")
    for v in doc["checkpointChecks"]:
        ok(checkpoint_refusals(v) == v["refusals"], f"{v['id']}: {checkpoint_refusals(v)}, expected {v['refusals']}")
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
