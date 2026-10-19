<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack — `identity-minting` M0

**Slice:** Decisions, contracts and anchors
**Plan:** [identity-minting.md](../plans/identity-minting.md#m0--decisions-contracts-and-anchors)
**Status:** [identity-minting.md](../status/identity-minting.md)
**Mode:** autonomous (granted 2026-09-23)

## What invariants does this slice protect?

1. **The anchors are independently correct.** Every anchor byte is recomputed by a verifier that shares no code with any minting library, using `openssl` for every digest and MAC.
2. **The anchors include the guide's published values**, so the specification, the guide and the anchors cannot drift apart: the SKU IRI `urn:ex:sku:XARXQP2R47P6MPFLTVC422KYQSO6EFWM` (guide Chapter 5) and the claim IRI `urn:key:person-email:v1:XUBJFDLLB7FTG552FYCFIMRUR4` (guide §6.1).
3. **The contracts are self-consistent.** Every recipe in the anchor file matches exactly one strategy branch of the recipe schema, and the anchor file validates against the anchors and vectors schemas.
4. **Tampering is detected** at every layer: an IRI, a MAC byte, a tuple component, and a recipe field changed without re-sealing its digest.

## Test case table

| ID | Given / When / Then | Level | Pass criterion | +/- |
|---|---|---|---|---|
| T1 | Given the anchor file, when `verify-anchors.py` runs with OpenSSL 3.4, then every check passes | L3 | `mise run check:minting-anchors`: 168 checks passed, 0 failed | + |
| T2 | Same, with the system LibreSSL (no binary-key HMAC flag, so the `-hmac` fallback) | L3 | `python contracts/identity/verify-anchors.py --openssl /usr/bin/openssl`: 168 passed | + |
| T3 | The three schemas are valid JSON Schema 2020-12, and the anchor file validates against them | L3 | `jsonschema` `Draft202012Validator.check_schema` on each, and zero validation errors on `anchor-vectors.json` (run during authoring, repeated in M1's test suite) | + |
| T4 | The authoring cross-checks: each normalization output hard-coded from its UCD citation equals a standard-library computation on Python 3.14 (Unicode 16.0.0), and the guide's two published IRIs are reproduced | L1 | assertions in the scratch authoring script, all passed | + |
| T5 | Corrupt the last character of a claim IRI | L3 | verifier exits 1: `claimIris: claim IRIs` | - |
| T6 | Change a recipe's `widthBits` without re-sealing its digest | L3 | verifier exits 1: `recipeDigest` mismatch | - |
| T7 | Change a tuple component (`v1` to `v2`) | L3 | verifier exits 1: `components … != …` | - |
| T8 | Flip one hex digit of a MAC | L3 | verifier exits 1: `mac` mismatch | - |

## Anchor coverage

Six sets, 16 positive, 7 negative and 1 format vector: derived hash (ASCII, whitespace and case, full-width compatibility forms; empty, unassigned), claimed surrogate with claim (ASCII, case and trim, zero-width space, soft hyphen, `ß`, a U+001F control that `White_Space` does not trim but Python's `str.strip` does, a Unicode 16.0 addition; unassigned, pattern mismatch, missing secret), natural key (two components, reserved characters, non-ASCII; missing component), position-derived (basic, maximum `xsd:long`; negative sequence), content-addressed (already-canonical bytes), random surrogate (format only).

## One command

```bash
mise run check:minting-anchors
```

## Deliberate non-coverage

- The verifier checks everything after normalization. Normalization is justified by UCD citations, and proven by the libraries against their pinned tables in M2 and M3.
- The anchor authoring script is not committed: the anchors are the artefact, and the committed verifier is what checks them.
