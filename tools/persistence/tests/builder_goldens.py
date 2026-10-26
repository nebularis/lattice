# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The golden check on builder versions (formal-methods track H, slice H2.6, plan 4.4). A builder's version is a number in
``persistence.contract.BUILDER_VERSIONS`` that any change to the text the builder renders must bump. This module records the
version and a digest of the rendered text of every builder (`fixtures/ir/builder-goldens.json`), so a changed text fails
`test_builder_versions.py` until the version is bumped and the record is updated. Each builder is rendered with one canonical context, so
the record is keyed by the operation and no fixture can move it:

    mise run build:persistence-builder-goldens

The update refuses to record a changed text under an unchanged version."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from rdflib import URIRef

from persistence.builders import BUILDERS, build
from persistence.contract import BUILDER_VERSIONS, stem_of
from persistence.ir_render import render
from persistence.paths import Opt, Step
from persistence.terms import Iri, Literal, PropertyPath

GOLDEN = Path(__file__).parent / "fixtures" / "ir" / "builder-goldens.json"


# The context every builder is rendered with, one for all, so a golden belongs to its builder and never to the first fixture that happens to
# generate it (H2.9-Q2, the finding of H2.6c). A new fixture cannot move another builder's recorded text. A builder reads the bindings it
# needs, and one that reads a binding this context lacks fails loudly.
CANONICAL_CONTEXT = {
    "shard": 17,
    "logGraphPrefix": Iri.encode("urn:g:txlog/"),
    "txnGraph": Iri.encode("urn:g:txn"),
    "keysGraph": Iri.encode("urn:g:keys"),
    "keyQuarantineGraph": Iri.encode("urn:g:key-quarantine"),
    "retentionGraph": Iri.encode("urn:g:retention"),
    "pinnedGraph": Iri.encode("urn:g:txlog/pinned"),
    "eventGraphPrefix": Iri.encode("urn:g:events/order/"),
    "metaGraphPrefix": Iri.encode("urn:g:meta/17"),
    "datasetGraph": Iri.encode("urn:g:dataset"),
    "datasetNode": Iri.encode("urn:g:dataset"),
    "graphPrefix": Literal.encode("urn:g:orders/"),
    "graphSuffix": Literal.encode("/data"),
    "guardProperty": Iri.encode("https://example.org/lending#status"),
    "ownedPath": PropertyPath.encode(Opt(Step(URIRef("https://example.org/lending#lineItem")))),
    "dataGraph": Iri.encode("urn:g:orders"),
    "payloadGraph": Iri.encode("urn:g:payload"),
    "constraintId": Literal.encode("example-constraint"),
    "mergeRelation": Iri.encode("https://example.org/lending#supersededBy"),
    "registryGraph": Iri.encode("urn:g:registry"),
}


def current() -> dict:
    out = {}
    for key in sorted(BUILDERS):
        text = render(build(key, dict(CANONICAL_CONTEXT)))
        out[key] = {"version": BUILDER_VERSIONS[stem_of(key)], "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}
    return out


def recorded() -> dict:
    return json.loads(GOLDEN.read_text(encoding="utf-8")) if GOLDEN.exists() else {}


def main(argv: list[str]) -> int:
    now, before = current(), recorded()
    refused = [
        key for key, entry in now.items()
        if key in before and before[key]["sha256"] != entry["sha256"] and before[key]["version"] >= entry["version"]
    ]
    if refused:
        print("the text of these builders changed and their version did not go up (BUILDER_VERSIONS in persistence/contract.py):")
        print("  " + "\n  ".join(refused))
        return 1
    if "--update" in argv:
        GOLDEN.write_text(json.dumps(now, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        print(f"recorded {len(now)} builders in {GOLDEN}")
        return 0
    print("builder goldens are current" if now == before else "builder goldens are stale")
    return 0 if now == before else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
