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

## Results

Recorded at verification.
