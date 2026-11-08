<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: v-rig VR-3, the mapping scheme and the extension seam

**Unit:** `v-rig` ([plan](../plans/v-rig.md), [status](../status/v-rig.md)).
**Branch:** `docs/placement-vehicles-structure`. Commits by the agent under the maintainer's authorisation of 2026-11-07, one per slice.
**Plan and test cases:** [the plan](../plans/v-rig.md), VR-3 in detail, principles 4, 6 and 8.
**Decisions:** [ADR-A153](../../architecture/decisions/ADR-A153-verification-rig-module.md) decision 2, VR-Q8, [ADR-A147](../../architecture/decisions/ADR-A147-skolem-rule-for-mapped-sources.md) for the runner.

## Invariant

The format's keys reach the layers through one tracked MORK scheme that enumerates no token of any rig, a rig's tokens reach concepts through an extension named at run time, every key no scheme reads is a finding, and the projection of one rig revision is byte for byte the same.

## Test cases

| Case | Expectation |
|---|---|
| VR3-01 | The tracked scheme compiles with no error finding |
| VR3-02 | The scheme declares the reading keys and the tool types their facts `vrig:Reading` |
| VR3-03 | The mapping source is the representation plus one derived edge per fact, with a list in order and an unknown fact's edge at the fact itself |
| VR3-04 | Each document is an `ins:Instrument` expressed in a `wrd:Wording` with its title as label |
| VR3-05 | Every body node is a `wrd:Element` under its parent by `wrd:directlyComprises`, one with text a `wrd:Text` with one part, and the kinds with a row in the reference data carry an element type |
| VR3-06 | Each layer is a `pty:ParticipationGroup` each for its own share, party to the instruments it places, with memberships carrying the shares, occupancies the roles of the extension and actors the invented names |
| VR3-07 | The line tokens reach concepts of the extension through the class-of-business lookup |
| VR3-08 | A numeric limit is an `ldg:AccountDefinition` with its stated amount, a formula limit is neither an account nor a quantity, and an attachment stated as not known is a `qnt:UnresolvedValue` |
| VR3-09 | A programme's period is a `fnd:TemporalScope` with its dates in the order written |
| VR3-10 | The extension's own scheme runs after the tracked one and gives each loss event its date as a scope |
| VR3-11 | Every key no scheme reads is a finding, a reading key is not, and every unresolved lookup is a finding at its node |
| VR3-12 | The projection and its findings are byte for byte the same over two runs |

## One command

Run from the repository root.

```bash
mise run check:v-rig
```

## Artefacts to inspect

`ontology/v-rig/projection/layers.mork.ttl`, `projection/reference.ttl`, `projection/.version`, `tools/v_rig/tests/mini-rig.extension.ttl`, `tools/v_rig/src/v_rig/p1.py`, `lift.py` (`mapping_source`, `mark_readings`, `rdf_list`), `tools/v_rig/tests/test_p1.py`, the `v-rig` task in `mise.toml`, and a run's `p1/source.ttl`, `p1/layers.ttl` and `p1/compiled.sparql`.

## Deliberate non-coverage

Validation of the layer graph by the layers' shapes, the reasoner and the competency queries (VR-4). The report (VR-6). A mapping of programmes, layers and placements onto a programme module, which does not exist yet (AIR-7.1), so they stay `vrig:` terms in the projection.

## Handoff

**Delivered 2026-11-08.** The tracked scheme maps the format's keys to Instrument, Wording, Party, Quantification, Ledger, Foundation and the insurance common module, and declares `exhaustion` and `drop_down` as reading keys with the vocabulary's new `vrig:readingKey`. Its reference data gives the body's kind tokens the Wording layer's element types by notation. The mini-rig's extension, tracked beside the mini-rig, carries the mini-rig's tokens as concepts and one scheme of its own for the keys of its events. `tools/v_rig/p1.py` compiles and runs every scheme with `tools/mork_rdf` on Oxigraph over the mapping source, collects the layer graph, and turns the runs' check rows and the keys no scheme reads into findings. `mise run v-rig -- --rig <path> [--extension <ttl>]` runs the whole, with the catalogue reader on the path.

**Two things learned about MORK while building, recorded in the scheme's header.** A plain assertion or a lookup reads from its parent's focus and cannot be guarded on a fact's key, so the mapping source carries one derived edge per fact, `<carrier> key:<name> <value>`, which the representation never holds, and a scheme reads a value by that edge and a node by a fact datum guarded on `vrig:key`. A contextual datum's exact R-Box match writes its own target as the subject and its parent's target as the value, and the inverse match the other way, which the first draft had backwards for every gluing property until the tests said so.

**What the scheme leaves out on purpose, for VR-4's competency queries to find.** No layer term links an instrument to the account definition of its limit or to the quantity of its attachment, so both stand alone, identified by the fact's locator. No term carries a reading of a legal concept, so a reading stays a `vrig:Reading` fact. A formula limit becomes neither an account nor a quantity until its inputs are bound. A declarations row, a list item, a paragraph, a title and a label have no element type in Wording's baseline, and each is an uncertain-mapping finding from the lookup.

**Vocabulary changes within the unreleased 0.1.0.** A list of scalars is one `vrig:value`, an RDF list with IRI cells in the source's order, so a period's two dates keep their order. `vrig:readingKey` is stated on a scheme. The module gained the `projection` role, versioned by `projection/.version` at 0.1.0, and the release register a row for it, so four tags wait for the maintainer, `v-rig-v0.1.0`, `v-rig-projection-v0.1.0`, `v-rig-shapes-v0.1.0` and `v-rig-vocab-v0.1.0`.

**Checks run, with their results.**
- `mise run check:v-rig`, `python -m pytest tools/v_rig -q`: 41 passed.
- `mise run check:catalogue`: `21 module(s) and 17 tool package(s) agree with the tree`.
- `mise run check:ontology-versioning -- --base-ref main`: `52 in-scope ontology document(s) checked against main: no unbumped changes`, and the release register check passes after `build:ontology-releases` added the projection's row.
- `python -m pytest tools/test_v_rig.py tools/test_lattice_repo_catalogue.py -q`: 144 passed.
- `literate_extract.py ... --check`: `4 extracted artefact(s) consistent`.
- `mise run v-rig -- --rig tools/v_rig/tests/mini-rig --extension tools/v_rig/tests/mini-rig.extension.ttl`: ran, 686 layer triples, 4 instruments, 4 wordings, 75 elements, 49 texts and parts, 3 groups, 4 memberships, 4 occupancies, 4 actors, 6 account definitions, 13 quantities, 3 temporal scopes, 3 definitions, 2 loss events, and 111 findings, 60 unmapped keys over 27 distinct keys, 40 uncertain mappings all `LookupUnresolved`, 8 prose-only and 3 unresolved references.

## Results

| Case | Result |
|---|---|
| VR3-01 | pass |
| VR3-02 | pass, five reading facts |
| VR3-03 | pass |
| VR3-04 | pass |
| VR3-05 | pass, once the match directions were flipped. Section, Clause, Definition and Endorsement carry a type |
| VR3-06 | pass, shares 0.4, 0.6, 1 and 1 compared as decimals, since Oxigraph writes 1.0 back as 1 |
| VR3-07 | pass |
| VR3-08 | pass, three tests, the unknown attachment on a hand-built source since the mini-rig's documents state none as not known |
| VR3-09 | pass |
| VR3-10 | pass |
| VR3-11 | pass, two tests |
| VR3-12 | pass |
