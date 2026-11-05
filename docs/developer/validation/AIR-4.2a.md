<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: AIR-4.2a, shared exposure members (TD-49)

**Unit:** [`applied-insurance-reference`](../status/applied-insurance-reference.md)
**Machine:** R, taking over from S. **Branch:** `air/applied-reference`, commits `[AIR-4.2a] …`
**Plan:** [Phase 4 plan](../plans/applied-insurance-reference-phase-4.md) (AIR-4.2a)
**Decisions:** the maintainer's correction of 2026-10-14 (TD-49), and its scope of 2026-10-14: every
inverse-functional property of the module

## Invariant

An unchanged member of an exposure set is shared by every version of the set it holds for, by
identity, and is never copied to make a new version. No property of the module says a member
belongs to one set, one location or one assessment. A reasoner therefore never merges two schedule
versions, two location versions or two assessments that list one node.

## Test cases

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| AIR42a-01 | the module's spec / read for `owl:InverseFunctionalProperty` / none declared | L1 | − |
| AIR42a-02 | `examples/versions.ttl`, two schedule versions listing one location, one asset and one valuation / the module's structural and cross-node shapes / conforms | L3 | + |
| AIR42a-03 | the core fixture with a second exposure set listing its factory / the shapes / no violation (restates AIR41-09) | L3 | + |
| AIR42a-04 | the spec with `owl:InverseFunctionalProperty` restored on `aeo:hasLocation`, and a reasoner over `versions.ttl` / consistency and `owl:sameAs` between the two schedule versions / the two versions merge | L4 | − |
| AIR42a-05 | the README / literate `--check` / consistent | L0 | + |

Rows 01, 03 and 04 are written into the AIR-deferred-testing slice (Phase 4 plan), under the
amendment of 2026-10-14.

## One command

```bash
mise exec -- python tools/literate_extract.py ontology/applied/insurance/exposure/README.md --layer applied/insurance/exposure --root . --shapes shapes/structural.ttl shapes/constraints.ttl shapes/profiles/construction-protection.ttl shapes/profiles/cyber-posture.ttl --check
```

## Artefacts to inspect

- The exposure README, §4.2 prose, the eight property definitions, the shapes table and §9.
- `examples/versions.ttl`.
- `tools/test_exposure_ontology.py`, where AIR41-09 is restated.

## Deliberate non-coverage

A shape that two versions of one location identity are not listed by one set at once. Whether a
set version lists the right members is the instrument's or the deployment's concern. Shared
designations and attribute values are allowed, and nothing yet says which assessment last
restated one.

## Handoff

- **Built:** `aeo:hasLocation`, `hasAsset`, `hasInterest`, `hasValuation`, `hasAssessment`,
  `zoneDesignation`, `poolParticipation` and `hasAttribute` are plain object properties.
  `aeo:MembershipShape` is withdrawn, with its row in the shapes table and its test restated.
  §4.2's prose no longer says a member "belongs to exactly one" set. `examples/versions.ttl` added.
  The spec and `constraints.ttl` regenerated from the README. No version bump, the module being
  new on this branch.
- **Run, with the result:** the literate extraction (spec and constraints regenerated, the other
  files unchanged). `examples/versions.ttl` validated against the structural and cross-node shapes
  with pySHACL (`advanced=True`, `inference="none"`): conforms.
- **Not run, and why:** `tools/test_exposure_ontology.py` and the catalog checks. Testing for the
  applied insurance modules is deferred (amendment of 2026-10-14).
- **Check first:** §4.2's prose, then the two `utility` strings that replace "Inverse
  functional" on the designation and attribute properties.
- **Deviations from the plan:** none. TD-49 is removed from the technical debt register.

## Results

| ID | Result |
|---|---|
| AIR42a-02 | `versions.ttl` against every exposure shape with pySHACL: conforms (run by hand) |
| AIR42a-03 | AIR41-09 restated as "sharing is accepted" in `test_exposure_ontology.py`, inside `check:ontology-catalog`: pass |
| AIR42a-05 | literate extraction: the generated files match the README |
| AIR42a-01, 04 | not built, in AIR-deferred-testing |

`check:full-sweep` against `main` on 2026-10-14, then `check:ontology-catalog` again after one fix:

| Check | Result |
|---|---|
| ontology versions, release register, import guard, python root, deny terms | pass |
| `check:vocabulary` | 16 passed |
| `check:mork-compilers` | pass |
| `check:reference-eligibility` | 58 passed |
| `check:formal-freshness`, `build:mtp`, `check:mtp`, `check:agent-guidance` | pass |
| `check:persistence` | 2549 passed, 207 skipped, 1 xfailed |
| `check:ontology-catalog` | first run 772 passed and 1 failed (`test_applied_shared_contracts.py` pinned nine `insurance/common` contracts, AIR-4.4 adds a tenth, test restated in `5492e39`). Rerun: 773 passed, catalog consistent with 2 known defects in MORK example files |
