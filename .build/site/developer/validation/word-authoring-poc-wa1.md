<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: word-authoring-poc WA1, Contracts, templates and samples

**Plan:** [word-authoring-poc](../plans/word-authoring-poc.md) §5 WA1
**Status record:** [word-authoring-poc](../status/word-authoring-poc.md) (holds the commit hash)

## Invariant

The three runtimes (Java, Python, the add-in) agree on one wire format before any of them is
built. Every message schema closes its object shape (ADR-A118 decision 1: the POC's own
contracts, not a platform contract) and marks every optional field `null` rather than omitting it,
so a producer in one language and a consumer in another cannot silently drift. The three sample
documents exercise the Wording text-part model the sketch describes (§3.1): a literal, a variable
reference and an object reference are the only three part kinds, matching CCS §4.1's three-part
reading that the Logical English alignment (route D) depends on.

## Test cases

| ID | Given / When / Then | Level | +/- | Result |
|---|---|---|---|---|
| AC-01 | every schema file / loaded / has the 2020-12 `$schema` and an `$id` of rule 2 | L1 | + | pass |
| AC-02 | every object subschema, found recursively / inspected / has `additionalProperties: false` and `required` equal to its property names | L1 | + | pass |
| AC-03 | every schema / scanned / contains no `format` keyword | L1 | + | pass |
| AC-04 | every `$ref` in the schemas and the OpenAPI file / resolved in the registry / resolves, including its JSON pointer | L3 | + | pass |
| AC-05 | each valid fixture / validated against the schema named by its prefix / passes | L3 | + | pass |
| AC-06 | each invalid fixture / validated / fails | L3 | - | pass |
| AC-07 | a snapshot whose element has zero parts, and a definition whose term is null / validated / both fail (zero cases) | L3 | - | pass |
| AC-08 | each template / validated / passes, section keys and variable keys unique within it | L3 | + | pass |
| AC-09 | each sample / validated and cross-checked / passes the schema, names an existing template, uses only that template's section keys, every reference targets a definition in the same sample, every definition's term occurs in one of its literal parts, documentIds follow §2.4 | L3 | + | pass |
| AC-10 | the OpenAPI file / parsed / version `3.1.0` and exactly the routes and methods of WA4's table | L3 | + | pass |
| AC-11 | the three samples / scanned / together contain each demo feature: a bracket placeholder, an unmarked money amount, an unmarked duration, an unreferenced variable, an unmarked entry, a clause with `shall not` in a section admitting only Permission | L1 | + | pass |

35 test functions in total (`test_each_fixture_validates_as_expected` parametrises over 13 valid
and 12 invalid fixtures, one case per AC-05/AC-06; `test_zero_case_fixtures_fail_for_the_right_reason`
is an explicit AC-07 check beyond the generic loop).

## One command

```
mise run check:authoring-contracts
```

Run from the repository root. A pass prints `N passed in …s` with no `FAILED` lines (35 passed,
0.94s on machine S). `mise run bootstrap:workers` must be run once first to install `jsonschema`
and `rdflib` (the `test` and `authoring` extras).

## Artefacts to inspect

- `contracts/authoring/common.schema.json` and the eleven other `*.schema.json` files under
  `contracts/authoring`, plus `contracts/events/wording-analysis-{request,result}.schema.json`.
- `contracts/authoring/templates/{facility-agreement,software-licence,property-policy}.json` and
  the matching `contracts/authoring/samples/*.json`. The facility sample's exact text was fixed by
  the plan, the licence and policy samples were written to the plan's content rules (§5 WA1,
  "Samples 2 and 3").
- `contracts/authoring/fixtures/suggested-keys.json`: shared by this slice and WA3/WA9a. Its seven
  cases were computed by hand against WA3's key-suggestion algorithm, not copied from the plan
  verbatim beyond the two it already gives.
- `contracts/openapi/authoring-service.openapi.json`.

## Self-probe

Removed `"additionalProperties": false` from `document-snapshot.schema.json`'s `LiteralPart`
definition. `test_every_object_schema_closes_additional_properties_and_requires_every_property`
failed, naming `document-snapshot.schema.json $defs/LiteralPart: not closed`. Restored the line and
re-ran: 35 passed.

## Implementer choices

- **AC-02's scope.** The plan's rule 3 ("every object has `additionalProperties: false`...") is
  enforced only on the top-level schema (when `type: object`) and on `$defs` entries that are
  themselves `type: object`. It deliberately does not scan `allOf`/`if`/`then` conditional
  fragments (used for `Element`'s definedTerm rule and `wording-analysis-result`'s status rule),
  since those fragments test only a subset of an instance's keys by design and must not declare
  `additionalProperties: false` or they would stop matching the real instance.
- **`message` and `error`-shaped string fields** without an explicit length in the plan's table
  (e.g. `ValidationResult.message`, `Finding.message`) were given `minLength: 1, maxLength: 1000`,
  matching the `error` schema's explicit `1..1000`.
- **Template `domain` values**: `finance` (facility agreement), `technology` (software licence),
  `insurance` (property policy). Not specified by the plan.
- **Sample 2 and 3 content** beyond the plan's literal quotations (the `Licensor`/`Licensee`/
  `Software`/`Documentation` and `Insurer`/`Insured`/`Premises`/`Damage` definition texts, and
  variable display values such as `"GBP 5,000"`) was written to satisfy the plan's content rules;
  it is not dictated word for word.
- **`wording-analysis-result--failed-minimal.json`**: a second valid fixture for that schema
  (the plan only required at least one valid fixture per schema), to exercise the `failed` branch
  of the `allOf`/`if`/`then` conditional as well as the `completed` branch.

## Deliberate non-coverage

The schemas and samples are not yet consumed by any runtime (that is WA2 onward). No Java,
Python or TypeScript code reads these files yet; `ContractSchemas` (WA2) and the add-in's
`domain/schemas.ts` (WA8) will load them next. Whole-unit non-coverage (CCS assembly, amendments,
tables, versioned elements, LE2 parsing, concurrent editing, authentication, poison-message retry
limits, real Word) is listed once in the plan §7 and not repeated per slice.
