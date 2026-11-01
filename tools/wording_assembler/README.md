<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Wording assembler

The reference implementation of Wording's baseline assembly model ([ADR-A139](../../docs/architecture/decisions/ADR-A139-wording-baseline-assembly-model.md)), as [ADR-A140](../../docs/architecture/decisions/ADR-A140-wording-assembler-topology.md) places it. It draws an assembled wording from a form, the settings of the instance and the drafter's choices, and renders the result in the [document markup](../../contracts/document/README.md).

Install the editable package from the repository root with:

```bash
mise exec -- python -m pip install -e "./tools/wording_assembler[test]"
```

Run its tests with `mise run check:wording-assembler`. A pass is the whole suite green, including the document schema check where `xmllint` is installed and a skip of that one check where it is not.

## The functions

Every function takes graphs and returns graphs. The assembly time and the minter of each new identifier are arguments, so the same inputs give the same record (law WA5). The one read from disk is the layer's specification and shapes, found through the repository catalogue and cached. Pass a `Layer` to read nothing.

| Function | Gives |
|---|---|
| `check(form, form_iri)` | an `sh:ValidationReport` of the form against laws W1 to W6 and W8, with the stage `validate` |
| `plan(form, form_iri)` | a `Plan`, the checked form with each `wrd:includedWhen` profile compiled by `tools/mork_compilers`, the questions they pose (`Plan.questions`) and a digest. It is reusable for every assembly of that form |
| `assemble(plan, settings, choices, at=, mint=)` | a `Result`, either the record and the value records it writes, or findings and no record (law WA6) |
| `reassemble(record_graph, record_iri, plan, settings, choices, at=, mint=)` | a `Result` for a new version with the same identity, which shares every value record the new settings leave alone |
| `render(record_graph, record_iri, form)` | the assembled wording as a document in the markup of ADR-A137 |

`settings` holds `wrd:VariableValue` records. `choices` names the optional elements, and the variants with no inclusion condition, that the drafter chose. `mint(kind)` gives an IRI for the kinds `record`, `identity`, `value`, `assembly` and `settings`.

## Findings

A refused assembly returns an `sh:ValidationReport` whose `sh:ValidationResult`s carry a code naming the stage, `load`, `validate`, `decide`, `assemble` or `record`, the focus element, and for an Undetermined condition the governing variable it lacks as `sh:value`. `wording_assembler.findings(report)` reads them as a list.

## What it does not do

- Digests of the plan, the settings and the choices are on `Result.digests`, not in the graph, since Foundation has no digest term to state them with.
- A definition is written as a clause, and a level below a section is flattened into it. The markup has no number attribute, so each clause opens with its derived number as text.
- Amendments, transclusion and inherited attributes are not assembled (ADR-A139, deferred).
