<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: word-authoring-poc WA2, Service model, mapping and shapes

**Plan:** [word-authoring-poc](../plans/word-authoring-poc.md) §5 WA2
**Status record:** [word-authoring-poc](../status/word-authoring-poc.md) (holds the commit hash)

## Invariant

A `document-snapshot` maps deterministically to the Wording-layer graph the CCS sketch §4
describes, with no loss and no leakage: every IRI is built only from the base, fixed path words and
checked identifiers (never from drafter-supplied text), no blank node is ever created, and an
element's identity (its IRI) never depends on its position, while its displayed object id (CCS law
W7) does. The SHACL shapes enforce laws W1 and W2 (`wording-poc-shapes.ttl`) over the mapped graph,
and compute `conforms` as "no violation", distinct from a warning.

## Test cases

| ID | Given / When / Then | Level | +/- | Result |
|---|---|---|---|---|
| S2-01 | each sample / mapped at revision 1 / its sorted N-Triples equal `fixtures/wording/<sample>.nt` | L2 | + | pass |
| S2-02 | a mapped sample / its triples added to a new model in reverse order / the canonical hash is unchanged | L2 | + | pass |
| S2-03 | a sample with one literal character changed / mapped / the hash differs | L2 | + | pass |
| S2-04 | an element inserted before element 2 of a section / mapped / its siblings' object ids shift and their IRIs do not (W7) | L1 | + | pass |
| S2-05 | the facility sample / mapped / literal parts carry `wrd:partText` only, variable and reference parts carry their reference and `wap:displayText` and no `wrd:partText` | L1 | + | pass |
| S2-06 | a snapshot whose title and texts contain `>`, `"`, `\n`, `{`, `#` / mapped / every IRI in the model starts with the base followed by `doc/<uuid>/` or with a vocabulary namespace, and the model has no blank node | L1 | - | pass |
| S2-07 | `ContractSchemas` / each valid and invalid snapshot fixture, every WA1 fixture | L3 | +/- | pass |
| S2-08 | each sample's graph / validated / facility and licence give no result, the policy exactly one WS10 warning on `period-start`, all three `conforms` | L1 | + | pass |
| S2-09 | a part with both `wrd:partText` and `wrd:refersToVariable` / validated / one WS2 violation | L1 | - | pass |
| S2-10 | a text with part indices {0, 0} and another with {0, 2} / validated / one WS3 violation each | L1 | - | pass |
| S2-11 | a text with zero parts / validated / one WS4 violation, and no WS3 result (zero case) | L1 | - | pass |
| S2-12 | an element with zero parents, and one with two / validated / one WS5 violation each (zero case) | L1 | - | pass |
| S2-13 | a reference part to a clause, and one to an absent element / validated / one WS7 violation each | L1 | - | pass |
| S2-14 | two definitions of `Loan` / validated / WS9 violations. A variable with zero references / WS10 at warning severity, `conforms` true (zero case) | L1 | - | pass |
| S2-15 | `FixtureWriter` / run into a temporary directory / its files equal the committed fixtures | L2 | + | pass |

48 JUnit tests in total across `WordingMapperTest`, `CanonicalHashTest`, `ContractSchemasTest`,
`WordingValidatorTest` and `FixtureWriterTest` (several plan rows are covered by more than one
`@Test`/`@ParameterizedTest` method, e.g. S2-08's two sample cases and the warning case).

## One command

```
mise run check:authoring-service
```

Run from the repository root. A pass prints `BUILD SUCCESS` for both `lattice-platform` and
`authoring-service` in the reactor summary (6.3s on machine S, including the shaded jar build).
`mise run build:authoring-fixtures` regenerates the committed `.nt` fixtures; it was run once to
create them and they are committed as goldens, read (not regenerated) by `check:authoring-service`.

## Artefacts to inspect

- `contracts/authoring/fixtures/wording/{facility-agreement,software-licence,property-policy}.nt`:
  the golden graphs. `facility-agreement.nt`'s first lines show a definition's single literal part,
  with `wrd:partText` carrying the curly-quoted term and an explicit `xsd:integer` datatype on
  `wrd:partIndex`.
- `platform/authoring-service/src/main/resources/vocab/wording-provisional.ttl`: every IRI the
  mapper writes, each commented with its CCS sketch citation or marked `POC gap (plan §2.6)`.
- `platform/authoring-service/src/main/resources/shapes/wording-poc-shapes.ttl`: the eleven shapes.

## Self-probe

In `wording-poc-shapes.ttl`'s WS10 shape, replaced `OPTIONAL { ?part wrd:refersToVariable $this }`
with the bare (non-optional) pattern. Two tests failed as expected:
`the_property_policy_sample_has_exactly_one_ws10_warning_on_period_start` (expected 1, got 0) and
`an_unreferenced_variable_is_a_ws10_warning_and_conforms_stays_true` (expected a WS10 result, got
none) — the zero-count case (a variable with no referencing part) produced no row to filter at all,
so the warning never fired. Restored the `OPTIONAL` and re-ran: all 48 tests passed.

## Implementer choices

- **Jena SHACL's `sh:sourceShape` for nested property shapes.** A first attempt nested every plain
  cardinality/datatype constraint under `sh:property [ ... ]` blank nodes beneath a named
  `sh:NodeShape`, as the SHACL examples elsewhere in the repository do. Jena reports
  `ReportEntry.source()` as the shape that directly carries the failing constraint, which for a
  nested `sh:property [...]` is the **blank node itself**, not the enclosing named shape, so the
  plan's `shapeId` regex (matching `shape-WSn` in the source's string form) found nothing and fell
  back to `WS0` for every plain property shape (WS1, WS4, WS5, WS6, WS7, WS8, WS11 — found by
  running the tests, not predicted in advance). Fixed by declaring each of those seven shapes
  directly as a named, top-level `sh:PropertyShape` carrying its own `sh:targetClass`/
  `sh:targetSubjectsOf` and `sh:path`, with no nesting. The four SPARQL-based shapes (WS2, WS3, WS9,
  WS10), whose constraint is declared directly on the named `sh:NodeShape`, needed no change.
- **`wrd:Text`'s relationship to `wrd:Element`.** The CCS sketch declares `wrd:Text ⊑ wrd:Element`.
  The provisional vocabulary does not assert this `rdfs:subClassOf` axiom, since nothing in this POC
  runs an RDFS or OWL reasoner (ADR-A83) and WS5's target is the explicit union
  `wrd:Element, wrd:Text, wrd:EmbeddedVariable`, which already matches every type this slice
  actually asserts.
- **The provisional vocabulary's scope.** Declares only the `wrd:`/`wap:` terms this slice's own
  code mints (`WordingMapper`, `Vocab`). The sketch's "proposed graph" terms (`ins:` classes,
  `wap:proposalBasis`, `wap:activityText`, etc., sketch §4.4) are not yet declared, since nothing
  produces them until WA6. WA6's plan entry does not list this vocabulary file among its own paths;
  when WA6 runs, extending `wording-provisional.ttl` should be added to its path list. Flagged here
  and in the status record rather than pre-declaring terms a later slice's code might not end up
  needing exactly as sketched.
- **`message` string lengths** on `ValidationResult` are unconstrained Java `String`s from Jena's
  own `ReportEntry.message()`; the JSON Schema bound (1..1000, WA1) applies at the HTTP boundary
  (WA4), not here.

## Deliberate non-coverage

No HTTP, no store, no detection, no templates: those are WA3 to WA5. The provisional vocabulary and
shapes are read from the classpath but never served or exposed; WA4 adds the routes that do. Whole-
unit non-coverage is listed once in the plan §7, not repeated per slice.
