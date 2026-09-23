<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Identity Minting — Status

**Unit ID:** `identity-minting`
**Status:** 🚧 In progress, M0–M2 complete (M2 on 2026-09-24), M3 next
**Plan:** [identity-minting.md](../plans/identity-minting.md)
**Sketch:** [identity-minting.md](../sketches/identity-minting.md)

## Is this unit complete?

**No.** Slices M0–M4 are planned. M4 ends with a walk-through that only a human can do.

| Slice | Scope | Status |
|---|---|---|
| M0 | ADR-A82 amendment, ADR-A84, licence tracking, contracts and schemas, anchor vectors, specification skeleton | ✅ Complete — see [VP](../validation/identity-minting-m0.md) |
| M1 | Vocabulary, compiler recipe emission, `dal:claimsConstraint` checks, `export-recipes` | ✅ Complete, 629/629 `tools/persistence` tests — see [VP](../validation/identity-minting-m1.md) |
| M2 | Pinned Unicode 16.0 tables, Python library, vector generation | ✅ Complete, 51/51 library tests, 7 generated vectors files — see [VP](../validation/identity-minting-m2.md) |
| M3 | Java library | ⏳ Not started |
| M4 | Specification completion, READMEs, human walk-through | ⏳ Not started |

## Decisions awaiting human review

The plan records six agent design decisions (P1–P6): recipe stored as canonical JSON inside the compiled TTL, `dal:tuplePrefix` as a list, position widths as vocabulary, natural-key rendering, the JSON restrictions that make the recipe digest simple, and (taken in M1) `dal:keyConstraint` as the source of a derived or natural key, with its scope value first. P1–P6 are now built on; reversing one means reworking M1.

## Open question for the human

**Should `NfkcTrimUppercase` and `NfkcTrimLowercase` remove default-ignorable code points?** Today they do not, because NFKC keeps them. A SKU typed with a zero-width space therefore mints a different IRI from the same SKU without one, and a key of nothing but default-ignorables mints rather than failing with `EmptyKeyComponent`. `NfkcTrimCasefold` removes them. Options: (a) keep this, documented as specification §11 pitfall and vector `key-default-ignorable-only-survives`, (b) add a `remove_default_ignorable` step to both pipelines, which changes every recipe digest using them and needs a Default_Ignorable_Code_Point table. My recommendation is (b), before any adopter mints with these pipelines, since changing it later is a re-key. M3 proceeds on the current definition either way, and the change would touch the tables, both libraries, the anchors and the specification together.

## M0 delivery detail

- **ADRs:** ADR-A82 point 5 amended in place, with an amendment note. ADR-A84 (Proposed) written and indexed. ADR numbers A83 (eligibility, renumbered from A81) and A84 recorded in the decisions index.
- **Licence tracking:** `REUSE.toml` declares `contracts/**/*.json` MPL-2.0. `README.md` and `CONTRIBUTING.md` now cover `contracts/`, `packages/`, `platform/` and `workers/` (MPL-2.0; `platform/` per ADR-A71, `workers/` as platform code under the same ADR).
- **Contracts:** `contracts/identity/` with three schemas, the anchor file (6 sets), `verify-anchors.py`, and a README. `mise run check:minting-anchors`, included in the aggregate `check`.
- **Specification:** `docs/architecture/identity-minting-specification.md`, normative for recipes, the digest, Unicode steps, bytes, templates, every strategy, content-addressed caller obligations, secrets, named errors, vectors and verification without LATTICE code. One worked example (derived hash). Pitfalls and the remaining worked examples are M4.
- **Found on the way:** the plan's list of named errors lacked `PositionOutOfRange`, needed for negative positions; added. My first draft of the worked example had a wrongly grouped tuple and a digest I had not computed; both were replaced with computed values before this record was written.

## M1 delivery detail

- **Vocabulary** (`persistence.ttl` §12a, §11, `dal:ClaimScheme`): `dal:mintedIriTemplate`, `dal:keyConstraint`, `dal:claimsConstraint`, `dal:tuplePrefix`, `dal:surrogateKind` with `dal:UuidV4Surrogate` and `dal:CallerSuppliedSurrogate`, `dal:callerSuppliedPattern`, `dal:acceptedIriPattern`, `dal:epochWidth`, `dal:sequenceWidth`, `dal:selfReferenceRule` with three rules, `dal:canonicalizationWorkBudget`, `dal:unicodeVersion` (all three pipelines at `16.0.0`), `dal:claimKeyId`, `dal:claimDigestScheme`, `dal:claimIriTemplate`, and compiled output `dal:MintingRecipe`, `dal:mintingRecipe`, `dal:recipeDocument`, `dal:recipeDigest`, `dal:forRole`, `dal:recipeStrategy`. The `dal:ContentAddressedIdentity` comment states the caller obligations.
- **Shapes:** `dal:MintingRecipeMembersShape` (seven constraints), `dal:AcceptedIriPatternRequiredShape`, `dal:ClaimSchemeCompletenessShape`.
- **Compiler:** new `persistence.recipes` (build, seal, export); recipes built after the identity checks and emitted per compiled target; the `ContentAddressedCallerObligations` warning; `persistence export-recipes`.
- **Fixture:** `identity-minting-anchors.ttl`, compiling to the six anchor recipes.
- **Tests:** `test_identity_minting_m1.py` (35 cases), the SHACL engine-error guard, and the Slice 3 contract changes listed in the VP.

## M2 delivery detail

- **Tables:** `packages/minting/tools/generate_ucd_tables.py` writes eight files per library (assigned, white_space, nfkc_cf, upper, lower, cased, case_ignorable, SOURCES) from the UCD 16.0.0 files. `mise run check:minting-tables` regenerates and compares.
- **Library:** `packages/minting/python` (`lattice-minting`, standard library only): recipe parsing and digest check, the seven pipeline steps, every strategy with a full trace, `verify` and the `lattice-mint verify` command, and `vectors.generate`. Recipes whose claims carry different keys are refused.
- **Anchors:** a seventh set, random surrogates with `randomHex`, and the content-addressed `CanonicalizerNotDeclared` negative. The file now escapes non-ASCII. 187 independent checks.
- **Vectors:** `mise run build:minting-vectors` compiles `identity-minting-anchors.ttl` and writes seven recipes and seven vectors files to `packages/minting/testdata`, annotated MPL-2.0 in `REUSE.toml`.
- **Docs:** specification §6, §6.3–§6.6, §9, §10.1, §11 updated; `packages/minting/README.md` and `python/README.md`; root README layout and check list.
- **Tasks:** `bootstrap:minting-python` and `check:minting-python`, both in the aggregates.
