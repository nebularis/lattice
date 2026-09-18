<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Generated surface packages

Any packages produced under canonicalisation contract `srf-canon/1` by the dependency-free compiler should be removed/deleted. The rdflib implementation hashes `rdflib.compare`'s canonical graph and therefore declares `srf-canon/2`. Per ADR-A12 a canonicalisation change is a planned estate-wide rehash.

Regenerate with:

```bash
python3 -m tools.surface compile \
    --contracts surface/examples/employment-job-family.ttl \
    --out surface/execution --verify-determinism --parity
```

A deployment's own packages live in that deployment's `execution/` directory. These three exist only to make the worked examples inspectable.

## Lowered MORK mapping graphs

`srf:ProjectionContract` examples (and any Promotion/Index contract lowered under `--promotion-index`) regenerate their MORK mapping graph with:

```bash
python3 -m tools.surface lower \
    --contracts surface/examples/saas-subscription-arr-projection.ttl \
    --out surface/execution/subscription-arr/mapping.ttl
```

No lowered mapping graph is committed here yet — `tools/surface/lowering.py` (ADR-A18) was written and tested by reading, not by running, in an environment with no Python interpreter. Run the command above and commit its output once Python is available, rather than trusting a hand-authored file to be byte-accurate.

