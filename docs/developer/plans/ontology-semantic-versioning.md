<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Plan: Semantic versioning for ontology documents

**Unit ID:** `ontology-semantic-versioning`
**Status:** Proposed, awaiting human review before implementation
**Trigger:** human request, 2026-09-25
**Sketch:** [ontology-semantic-versioning.md](../sketches/ontology-semantic-versioning.md)
**Status record:** [ontology-semantic-versioning.md](../status/ontology-semantic-versioning.md)
**ADR:** [ADR-A86](../../architecture/decisions/ADR-A86-ontology-semantic-versioning.md), Proposed

## Problem and corrected scope

Every `owl:Ontology` document under `ontology/` carries an ungoverned
`owl:versionIRI`, or none, with no documented rule for when it changes. This
unit adopts SemVer 2.0.0 for ontology documents (ADR-A86), documents the
MAJOR/MINOR/PATCH classification for a human or agentic contributor to apply,
resets every in-scope document to one common baseline, and adds a narrow
mechanical check that a version literal actually moved when content did. It
does not build an automatic change-classifier, does not touch `shapes/*.ttl`
or `projection/*.ttl` versioning independence, and does not change what any
layer's ontology says.

## Governing decision

[ADR-A86](../../architecture/decisions/ADR-A86-ontology-semantic-versioning.md)
(Proposed) records: SemVer 2.0.0 per `owl:Ontology` document; `spec/*.ttl` and
`vocab/*.ttl` remain independently versioned; the PATCH/MINOR/MAJOR mapping
table; import-pinning retained as-is with a same-change cascade obligation;
the `0.2.0` baseline reset target; and the versionIRI base-URI normalisation
bundled into that same reset. No implementation slice below starts until this
ADR, the mapping table, the versioning unit, and the baseline number are
confirmed at ratification.

## Deliverables

### 1. Governance records (this slice's own output)

- This plan, its [sketch](../sketches/ontology-semantic-versioning.md), and
  [status record](../status/ontology-semantic-versioning.md), cross-linked.
- ADR-A86 filed as Proposed.
- `docs/architecture/decisions/README.md` index updated with the A-86 row.
- `docs/developer/INDEX.md` updated with this unit's entry, in the same shape
  as the `vocabulary-temporal-binding` entry it sits alongside.
- Traceability rows added to `docs/traceability/matrix.csv` for ADR-A86 and
  each invariant in the sketch, once slices are numbered against test/check
  IDs (Slice 4 introduces the first checkable one).

### 2. Developer and agent guidance

- New `docs/architecture/ontology-versioning-policy.md`:
  - The MAJOR/MINOR/PATCH table from the sketch, with the two repository
    examples it already cites (`vocabulary-temporal-binding`'s MINOR addition,
    and a worked hypothetical MAJOR narrowing) kept as illustrations.
  - The versioning-unit rule (one version per `owl:Ontology` document; how
    `shapes/`/`projection/` changes map onto that).
  - The import-pinning cascade checklist: before bumping, `grep -rl
    "owl:imports.*<layer-namespace>" ontology/` (or the literal pattern each
    layer's README already uses) to enumerate every importer, and update all
    of them, plus their README `turtle-spec` sources, in the same change.
  - Where the number physically lives for the seven literate-spec layers
    (the README's `turtle-spec` block; `tools/literate_extract.py` propagates
    it to `spec/*.ttl`/`vocab/*.ttl` — never hand-edit the generated file's
    `owl:versionIRI` independently of its README source) versus the
    directly-authored layers (Persistence, Surface, MORK, SPC, applied
    ontologies), where the generated file *is* the source.
  - The one flagged judgement-call case (silent semantic redefinition with no
    axiom change) stated as requiring a documented rationale in the PR, not a
    mechanical diff.
- `CONTRIBUTING.md` "Where new content belongs" gains a short cross-reference
  to the new policy document, next to the existing `vocab/` boundary note.
- `docs/architecture/ontology-architecture.md` §2 ("Namespace convention")
  gains a one-paragraph cross-reference to the new policy document; no other
  content in that file changes as part of this unit.

### 3. Baseline reset

A single mechanical pass across every document the sketch's inventory table
names:

- Assign `Mork.ttl` and `spc.ttl` their first `owl:versionIRI`.
- Reconcile `applied/insurance/contract.ttl`'s `owl:versionIRI 0.1.1` and
  `owl:versionInfo "3.5.1"` into one signal (the ADR's recommendation:
  `owl:versionIRI` is authoritative; `owl:versionInfo`, if kept at all, states
  the same value as a human-readable label, never a second number).
  Confirm at ratification whether `owl:versionInfo` is dropped or kept.
- Normalise the `owl:versionIRI` base URI for every core layer currently
  missing the `lattice/` segment (Foundation, Vocabulary, Quantification,
  Party, Eligibility, Instrument, Behaviour, Surface — both `spec` and
  `vocab` artefacts) to `https://www.nebularis.org/neuro-semantic/lattice/<layer>/<version>`
  (and the equivalent `<layer>-vocab` pattern, base corrected the same way).
  Leave `applied/insurance/contract.ttl`'s distinct namespace family alone
  pending the open question in the sketch.
- Reset every in-scope document's version segment to `0.2.0` (pending
  ratification of that number).
- For the seven literate-spec layers, make this edit in the README's own
  `turtle-spec` block and regenerate via `tools/literate_extract.py`, not by
  hand-editing `spec/*.ttl`/`vocab/*.ttl` directly — the existing README⇄spec
  drift check depends on that discipline holding.
- Update every `owl:imports` statement (README source and generated file
  alike) that names one of the bumped IRIs by its old version, in the same
  change — enumerate with the checklist from deliverable 2 before starting,
  not after.
- Add one line to each affected layer's own "Open items" (or equivalent)
  section recording the reset as an administrative normalisation under
  ADR-A86, not a claim of seven-plus MINOR releases.

### 4. Narrow enforcement tooling

- A small check (Python, in the spirit of `tools/repository_topology_check.py`)
  that, given a base ref and the working tree, flags any in-scope `.ttl` file
  whose triples differ from the base ref but whose `owl:versionIRI` literal
  is unchanged. Wired as `mise run check:ontology-versioning` (or folded into
  `topology:links`/`topology:preflight` if that proves the better home —
  confirm at Slice 4 planning, not before).
- Explicitly does not attempt MAJOR/MINOR/PATCH classification — only
  "something changed, nothing was bumped."

## Slice plan

| Slice | Scope | Test level | Gate |
|---|---|---|---|
| 1 | ADR-A86, sketch, plan, status record, ADR-index and INDEX.md entries | L0 | Human review of the mapping table, versioning unit, and `0.2.0` baseline number |
| 2 | `ontology-versioning-policy.md`, `CONTRIBUTING.md` and `ontology-architecture.md` §2 cross-references | L0 | `mise run topology:links` finds no broken cross-reference; a second reader can classify a change using only the new document |
| 3 | Baseline reset (version numbers, base-URI normalisation, `owl:imports` cascade, per-layer changelog notes) | L0, L3 | Every affected README's `turtle-spec` block still extracts cleanly (`tools/literate_extract.py --check`); every `owl:imports` target IRI resolves to a document that exists in the tree; `reuse lint` still passes |
| 4 | The "changed but not bumped" check, wired into `mise` | L0 | The check fires against a fixture with content changed and version literal held constant, and stays silent against a fixture with both changed together (mutation probe) |

Slice 3 touches many files but each file's edit is the same three mechanical
operations (version segment, base URI, importer cascade); it is not split
further because splitting by layer would multiply cross-file import-cascade
coordination rather than reduce it. Slice 4 is independent, small, and does
not block Slices 1–3 landing first.

## Acceptance and validation

The single command, once Slice 4 lands:

```text
mise run check:ontology-versioning
```

Until then, Slices 1–3 validate via `mise run topology:links`, `tools/literate_extract.py --check`
(run per affected layer), and `reuse lint`, all of which already exist.

## Deliberate non-coverage

- Automatic MAJOR/MINOR/PATCH classification of a change.
- A dependency-range import mechanism replacing exact-IRI `owl:imports`
  pinning (flagged in the ADR as a live open question, not decided here).
- Independent `owl:Ontology`/`owl:versionIRI` identity for `shapes/*.ttl` or
  `projection/*.ttl`.
- Any change to what a layer's ontology says, beyond the version/namespace
  metadata this unit's baseline reset touches.
- MORK's and SPC's own governance conventions beyond first-assigning them a
  version identity.
- `applied/insurance/contract.ttl`'s namespace family — resetting its version
  number and reconciling its two version signals, yes; moving it into the
  `lattice/` namespace tree, not decided here.

## Checked documents with no planned change

`docs/architecture/solution-design-specification.md`, `docs/GOVERNANCE.md`,
the root `README.md`, and `GENAI_CONTRIBUTION.md` were checked and contain no
ontology-version-specific mechanism this unit must synchronise. This remains
an explicit assumption for human review, not a claim the files are
permanently out of scope.
