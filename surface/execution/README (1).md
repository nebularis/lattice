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
