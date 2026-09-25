<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: AOR-14 to AOR-16, Quantification extensions

**Unit:** [`applied-ontology-readiness`](../status/applied-ontology-readiness.md)
**Decisions:** [ADR-A93](../../architecture/decisions/ADR-A93-quantification-derived-rate-spaces.md), [ADR-A94](../../architecture/decisions/ADR-A94-quantification-calendar-binding.md), [ADR-A95](../../architecture/decisions/ADR-A95-quantification-alternative-bounds.md), all Accepted. One Quantification change, by decision (2026-09-25).

## Invariant

Rates are typed by the spaces they divide. A calendar-unit conversion is
always contextual. A limit stated in several units is compared only in the
candidate's own unit, by every compiler backend, never through a conversion.

## Test cases

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| AOR14-01 | a derived space with numerator and denominator / shapes / conforms | L1 | + |
| AOR14-02 | a derived space missing its denominator / shapes / violation | L1 | - |
| AOR15-01 | a Contextual conversion from a calendar unit / shapes / conforms | L1 | + |
| AOR15-02 | a Defined conversion from a calendar unit / shapes / violation | L1 | - |
| AOR16-01 | two alternative bounds, same sense, different units / shapes / conforms | L1 | + |
| AOR16-02 | alternatives with different senses / shapes / violation | L1 | - |
| AOR16-03 | alternatives in one unit / shapes / violation | L1 | - |
| AOR16-04 | a USD 10m or EUR 9m ceiling / compiled / one interval per unit | L1 | + |
| AOR16-05 | candidates in USD, EUR, GBP and no unit / SPARQL / Permitted and Denied by own unit, GBP and unitless `Undetermined` with `exe:NoBoundInUnit` | L1 | + and - |
| AOR16-06 | same / SHACL / agrees with SPARQL | L2 | + |
| AOR16-07 | same / SWRL applied / only the two within-limit candidates permitted | L2 | + |
| AOR16-08 | two statements in one unit / compiled / refused | L1 | - |
| AOR16-09 | bound subjects drawing EUR and GBP amounts / SPARQL / by own unit, GBP `Undetermined` | L1 | + and - |

## One command

```bash
mise run check:ontology-catalog && mise run check:mork-compilers
```

Pass: tool tests (including `tools/test_substrate_extensions.py`), a
consistent catalog, and `80 passed`.

## Artefacts to inspect

- `ontology/quantification/README.md`: `qnt:DerivedValueSpace`,
  `qnt:CalendarUnit`, `qnt:Calendar ⊑ voc:ConceptScheme`, five properties,
  `qnt:Scale`, `qnt:NoBoundInUnit`, three shapes, §9.2, §9.6, §13 (questions 2
  and 4 closed). Mirrored in `spec/`, `vocab/` and `shapes/constraints.ttl`.
- Compiler: `RequiredInterval.unit`, `_statements` in the IR, `applicable` in
  `sparql_backend.py` (the SHACL backend now reuses the SPARQL interval
  helpers instead of its own copy), `inUnit` atoms in SWRL.
- `exe:NoBoundInUnit` in Executable.
- Versions (MINOR, against `3e7d911`): Quantification 0.4.0 → 0.5.0,
  Executable 0.4.0 → 0.5.0, and the cascade to Party, Surface, Eligibility,
  Instrument, Behaviour and the applied capacity spec.

## Adversarial probe (run by the agent)

| Mutation | Tests failed |
|---|---|
| every interval treated as applicable | AOR16-05, AOR16-06, AOR16-09 |
| unit condition dropped from interval clauses | AOR16-05, AOR16-06, AOR16-09 |

## Deliberate non-coverage

- Evaluating `qnt:Scale` and calendar conversions. Quantification declares
  them. Supplying a calendar context to the compilers is later work (ADR-A94).
