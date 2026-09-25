<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Ontology Semantic Versioning - Status

**Unit ID:** `ontology-semantic-versioning`
**Status:** Slices 1-4 implemented, at the human's explicit direction to
implement the plan autonomously (2026-09-25). ADR-A86 itself remains
Proposed — ratifying it is a separate human action this implementation does
not take on its own behalf.
**Last updated:** 2026-09-25
**Trigger:** human request, 2026-09-25 ("implement the semantic versioning
plan autonomously")
**Plan:** [ontology-semantic-versioning.md](../plans/ontology-semantic-versioning.md)
**Sketch:** [ontology-semantic-versioning.md](../sketches/ontology-semantic-versioning.md)
**ADR:** [ADR-A86](../../architecture/decisions/ADR-A86-ontology-semantic-versioning.md), Proposed

## Current position

All four slices are implemented. The human's instruction to implement is
treated as confirmation of the ADR's recommended defaults (the `0.2.0`
baseline, `owl:versionIRI` as the sole authoritative signal), per the working
pattern this repository has followed for other units executed the same way
(`vocabulary-temporal-binding`): implementation proceeds on the documented
recommendation, ADR ratification itself stays a distinct, later human action.

### Slice 1 — governance records

Done in a prior session: ADR-A86 (Proposed), the sketch, this plan, this
status record, and the ADR-index/`INDEX.md` entries.

### Slice 2 — developer/agent guidance

- New [`docs/architecture/ontology-versioning-policy.md`](../../architecture/ontology-versioning-policy.md):
  the MAJOR/MINOR/PATCH table, the versioning-unit rule, the import-pinning
  cascade checklist, where the number physically lives per layer, and a
  worked example from this repository's own history
  (`vocabulary-temporal-binding`'s MINOR addition).
- `CONTRIBUTING.md` "Where new content belongs" and
  `docs/architecture/ontology-architecture.md` §2 both cross-reference the
  new policy document.
- `mise run topology:links` was run after these additions: it reports the
  same pre-existing broken links this repository already carried (none of
  them in a file this unit touched) and zero new ones.

### Slice 3 — baseline reset

Every document the sketch's inventory named was reset to `0.2.0`, and every
`owl:imports` reference to one of the old IRIs anywhere in `ontology/` was
cascaded in the same change. Full before/after table:
[`ontology-versioning-policy.md`](../../architecture/ontology-versioning-policy.md#the-one-time-baseline-reset-2026-09-25).

**Deviation from the plan's literal text, recorded here because it matters:**
the plan said to make this edit "in the README's own `turtle-spec` block and
regenerate via `tools/literate_extract.py`." Running the tool first (in
`--check` mode, before touching anything) showed it already fails for every
one of the seven core layers today — Foundation's, Vocabulary's, and Party's
committed `spec/*.ttl` predate the extraction tool's conventions entirely
(different, hand-authored Turtle formatting, not a `turtle-spec`
concatenation), and the remaining four layers' README `turtle-shapes` blocks
don't agree with the tool's `--shapes` argument contract. Running the tool in
write mode would have overwritten large amounts of unrelated, already-drifted
content with a full regeneration — well outside this unit's scope and a real
risk to content this unit has no mandate to touch. The version/import lines
were therefore edited directly, by hand, in both the README (where one
mirrors the header) and the generated file, keeping the two identical for
that one block without invoking the extractor. This gap — extraction drift
across the whole 7-layer literate-spec set — is now recorded as a discovered,
separate problem in the policy document, not silently absorbed into this
unit's own scope.

**Also found and fixed as a genuine importer, beyond the sketch's original
inventory:** `tools/surface/src/surface/namespaces.py`'s `SURFACE_ONTOLOGY`
constant, which the Surface compiler (`compile.py`) stamps into every
generated surface's `owl:imports`. Updated to the new
`.../lattice/surface/0.2.0` IRI in the same change.

**Deliberately left alone:** MORK's own example/test fixtures
(`Meta_RML/GPTAttempt.ttl`, `Meta_RML/RMLMap.ttl`, `Zoo/Petstore.ttl`,
`Zoo/UncertainMappings.ttl`, `test/data/Demo.ttl`) that `owl:imports` MORK's
*bare, unversioned* ontology IRI. That IRI still exists and is still declared
`a owl:Ontology` — adding a `versionIRI` to `Mork.ttl` did not invalidate it —
and converting five example/test fixtures from "import whatever Mork
currently is" to "pin an exact version" is a bigger behavioural change than a
version-number reset, not something this unit's cascade obligation covers.
`mork/spec/Executable.ttl`, the one layer-level (non-example) importer of
Mork, was likewise left importing the bare IRI, matching that same existing
convention rather than introducing it as the sole exception.

### Slice 4 — narrow enforcement tooling

`tools/ontology_version_check.py` + `mise run check:ontology-versioning`
(wired into the aggregate `check` task). Validated two ways: a direct
function-level mutation probe (flags "content changed, `owl:versionIRI`
literal unchanged"; stays silent when both change together — both confirmed
manually in this session) and a real run against this unit's own working-tree
diff, which reported zero unbumped files across all 29 in-scope ontology
documents (every file this unit touched changed its version at the same
time, and every file it left alone was left alone).

## Decisions made during implementation (flagged for human review)

- **The baseline number: `0.2.0`.** Applied as recommended; not separately
  re-confirmed by a human before this session's implementation, per the
  explicit "implement autonomously" instruction.
- **`owl:versionInfo` dropped, not kept, on `applied/insurance/contract.ttl`.**
  `owl:versionIRI` is now that document's sole authoritative version signal;
  its `owl:priorVersion` was updated to point at `0.1.1` (its immediate
  predecessor) rather than removed.
- **`applied/insurance/contract.ttl`'s namespace family** (`neuro-semantic/insurance/...`,
  outside `lattice/`) was left exactly as it was, per the plan's explicit
  non-coverage — only its version number and its two disagreeing version
  signals were touched.
- **MORK's `Mork.ttl` and SPC's `spc.ttl` first `owl:versionIRI` values** use
  each ontology's *own* existing namespace family
  (`http://www.nebularis.org/ontologies/Mork/0.2.0` and
  `http://example.org/spc/0.2.0` respectively), not the `lattice/` tree —
  MORK is documented elsewhere as a pre-existing, independently-styled
  vocabulary, and SPC's namespace harmonisation to `nebularis.org` (ADR-A62)
  is itself still Proposed, not Accepted; assigning SPC a `lattice/`-based
  versionIRI now would have pre-empted that still-open decision.
- **Import-pinning strategy: kept exact, as recommended.** No dependency-range
  mechanism was introduced.
- **The Slice 4 check's home: a new standalone `check:ontology-versioning`
  task**, not folded into `topology:links`/`topology:preflight` — those two
  check documentation cross-references and the ADR-A77 migration manifest
  respectively, a different concern from ontology-file version hygiene.

## Human validation gate

Not yet performed. Before treating this unit as fully closed:

1. Ratify ADR-A86 (or amend it) — its status remains Proposed.
2. Spot-check the baseline-reset table in `ontology-versioning-policy.md`
   against a few of the actual files, and confirm the `applied/insurance`
   namespace-family question's disposition (left alone, as implemented).
3. Run `mise run check:ontology-versioning` in an environment with the
   repository's full git history available (this session validated it
   in-sandbox against the working tree, which is the same code path `mise`
   uses).
4. Decide, separately, whether the newly-discovered `tools/literate_extract.py`
   drift across the seven core layers (recorded in the policy document)
   becomes its own remediation unit.

## Blockers

None recorded against this unit's own four slices — all are implemented.
ADR-A86 ratification and the extraction-drift follow-up (both above) are
open items for a human, not blockers to what this unit set out to do.

