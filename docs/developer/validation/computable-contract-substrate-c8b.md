<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: CCS C8b, references by identity

**Unit:** [`computable-contract-substrate`](../status/computable-contract-substrate.md)
**Machine:** R (Claude Code). **Branch:** `ccs/c8b-references-by-identity`. Commits are the human's,
and the change is merged into `main` before its release tags are created
**Plan and test cases:** [CCS plan](../plans/computable-contract-substrate.md) (C8b in detail)
**Decisions:** ADR-A104 and its 2026-10-06 addenda, ADR-A51, the Wording ADRs behind laws W1 to W7.
C8b-Q1 to C8b-Q4. Takes over insurml-alignment IMA-3.3

## Invariant

A clause's text names what it refers to the way its stated meaning does. A reference to another part of the wording, or to a variable, names a persistent identity, resolved within the wording that holds the clause, so a clause reused under another schedule or beside a revised definition needs no new version. Nothing here changes what a wording means.

## Test cases

The table in the plan section above. Each row's result is recorded under Results at
verification.

## One command

Run from the repository root on machine R.

```bash
mise run build:ontology-catalog && mise run check:ontology-versioning && mise run check:ontology-catalog && mise run check:import-guard
```

## Artefacts to inspect

- `ontology/wording/examples/`: the reworked examples and `reused-clause.ttl`, written before the
  model.
- `ontology/instrument/examples/`: the three C8 examples, their text references by identity.
- `ontology/wording/README.md`: references by identity, resolution at each tier, display text, W8.
- `ontology/wording/shapes/`: W8 and the reference ranges.

## Deliberate non-coverage

A renderer (insurml-alignment IMA-4.1). Resolution records for policies that cannot be derived from the graph (assembly interface sketch H5). Transclusion and inline parts (IMA-3.1, IMA-3.2).

## Handoff

Written by the building machine when the work is ready for the human to commit.

Phase 1, examples first (ADR-A-C2), 2026-10-06:

- **Built:**
  - `ontology/wording/examples/reused-clause.ttl` (new): an equipment lease form in two editions.
    Clause 5.1 is one element version in both, though the definition it mentions is revised, the
    schedule variable it shows is redeclared, and a regulation it cites is relied on at a newer
    edition. An inflected display text ("Lessee's"). One regulation relied on statically, one as
    amended, and a scanned attachment at one edition. A lease assembled from edition 2, with each
    reference's resolution tabulated in the header
  - `facility-agreement.ttl`, `facility-form.ttl` and `trial-protocol.ttl` (Wording), and
    `facility-parameters.ttl`, `framework-lots.ttl` and `services-schedule.ttl` (Instrument),
    reworked: every reference names an identity. The attachment and the regulation they cite gain
    identities, and their wordings a static and an ambulatory reliance
  - the ADR-A112 addendum "references by identity" (Proposed)
- **Run by the agent:** every Wording example and the three Instrument examples against the current
  model and every layer's shapes, without inference. The only new failures are the ones the model
  phase changes: Wording's shapes require a reference's value to be a `wrd:Variable` or a
  `wrd:ReferenceTarget`, a version, where each now names an identity. `facility-amendment.ttl`'s
  results, read alone, are unchanged from before, since its tests read it with the form it amends.
  The Instrument examples' warnings are C8's.
- **Not run:** the tool tests, which fail on those shapes until the model phase.
- **Check first:** the deviations.
- **Deviations from the plan:**
  - **One clause in two editions of one form, not in two forms.** Wording's law W1 places an element
    version in versions of one wording only, so one version in two different forms needs
    transclusion (insurml-alignment IMA-3.1). The example shows the problem C8b solves, revisions
    rippling through every clause that mentions what changed, which needs no transclusion. A
    form's sections that contain a revised definition still take new versions, since containment
    names versions: references by identity remove the ripple through references, not through
    containment
  - **Two properties for reliance, and no reliance node.** `wrd:reliesOnEdition` names an edition,
    and `wrd:reliesAsAmended` names an identity. A node per reliance would carry the mode as data,
    at the cost of a node per citation in every wording, with nothing else to say about it today.
    If a reliance later needs more (a date, a jurisdiction), a node can replace the two
  - **An outside document's editions** carry `fnd:hasIdentity`, `fnd:hasTemporalScope` (in force
    from) and `fnd:supersededBy`. External documents and document objects are `prov:Entity` today,
    not `fnd:Version`: the model phase makes them versions
  - **A reliance is stated on the form**, and an assembled wording inherits it through
    `wrd:assembledFrom`. An assembled wording may state its own, which W8 reads first

Phase 2, the model, 2026-10-06:

- **Built:**
  - Wording 0.7.0 and `wording-vocab` 0.7.0 (breaking), shapes 0.4.0. `wrd:refersToObject`,
    `wrd:refersToVariable` and `wrd:linksTo` range over `fnd:PersistentIdentity`.
    `wrd:displayText` is new. `wrd:DocumentObject` and `wrd:ExternalDocument` are `fnd:Version`s
    (editions), relied on through `wrd:reliesOnEdition` (static) or `wrd:reliesAsAmended`
    (ambulatory). §5.7 and §5.8 rewritten, with a resolution diagram in §5.8
  - law W8 in the constraints shapes: in a form, an identity a reference names has exactly one
    comprised version. In an assembled wording, one included or declared through an included
    element. An outside document is relied on exactly once, by the wording or the form it is
    assembled from
  - Instrument 0.14.0 and `instrument-vocab` 0.14.0 (breaking, a re-pin). Shapes unchanged (0.6.0)
  - C8b tests in `tools/test_wording.py`, already in `check:ontology-catalog`. Version pins moved in
    five other test modules. The release register, the catalog and the ontology architecture
    updated
- **Run by the agent:** every check listed under Results.
- **Check first:** the deviations, then the W8 messages in `ontology/wording/README.md`.
- **Deviations from the plan:**
  - **The binder is unchanged.** It reads placeholders, not text references, and W8 covers forms,
    so the lookup the plan expected (C8b-Q4) had nothing to change. C8's regeneration tests pass
    unchanged (C8b-07)
  - **No hash.** Wording has no content hash, so C8b-05 reads "its hash unchanged" as the clause
    being one node in both editions
  - **Messages on the referring shapes.** pySHACL does not carry a node shape's message through
    `sh:node`, so each property shape that uses `wrd:VariableIdentityShape`,
    `wrd:TargetIdentityShape` or the ambulatory reliance check carries its own message
  - **Existing tests corrected.** C3-04 expects identities, and C4-02 counts five examples

## Results

| Row | Result | Evidence |
|---|---|---|
| C8b-01 | pass | `test_c8b_01_spec_version_ranges_and_display_text`, `test_c8b_01_display_text_only_on_a_reference_part` |
| C8b-02 | pass | `test_c8b_02_examples_conform` (eight Wording and Instrument examples) |
| C8b-03 | pass | `test_c8b_03_a_reference_naming_a_version_is_reported` |
| C8b-04 | pass | `test_c8b_04_an_identity_finding_no_version_or_two_is_reported` |
| C8b-05 | pass | `test_c8b_05_one_clause_version_in_both_editions_resolving_differently`, see the hash deviation |
| C8b-06 | pass | the three `test_c8b_06_` tests, including reliance inherited by an assembled wording |
| C8b-06a | pass | `test_c8b_06a_a_revised_definition_leaves_the_clause_mentioning_it_alone` |
| C8b-07 | pass | `tools/test_parameter_bindings.py` C8-10 to C8-13, unchanged |
| C8b-08 | pass | `test_c8b_08_instrument_imports_wording_0_7_0_and_nothing_names_0_6_0` |
| C8b-09 | pass | `test_c8b_09_readme_release_notes`, both literate checks |
| C8b-10 | pass | `check:ontology-catalog` (587 passed), `check:ontology-versioning`, `check:import-guard`, `check:python-root`, `check:mork-compilers` (114), `check:vocabulary` (16), `check:persistence` (778), `build:mtp`, `check:mtp` |

The §5.8 diagram renders in a browser.
