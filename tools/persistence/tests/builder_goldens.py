# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The golden check on builder versions (formal-methods track H, slice H2.6, plan 4.4). A builder's version is a number in
``persistence.contract.BUILDER_VERSIONS`` that any change to the text the builder renders must bump. This module records the
version and a digest of the rendered text of every builder (`fixtures/ir/builder-goldens.json`), so a changed text fails
`test_builder_versions.py` until the version is bumped and the record is updated:

    mise run build:persistence-builder-goldens

The update refuses to record a changed text under an unchanged version."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from persistence.builders import BUILDERS, build
from persistence.contract import BUILDER_VERSIONS, stem_of
from persistence.ir_render import render

GOLDEN = Path(__file__).parent / "fixtures" / "ir" / "builder-goldens.json"


def current() -> dict:
    from test_builders import _first

    out = {}
    for key in sorted(BUILDERS):
        _, _, _, context = _first(key)
        text = render(build(key, context))
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
        GOLDEN.write_text(json.dumps(now, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"recorded {len(now)} builders in {GOLDEN}")
        return 0
    print("builder goldens are current" if now == before else "builder goldens are stale")
    return 0 if now == before else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
