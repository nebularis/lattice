<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: word-authoring-poc WA3, detection, templates and conformance

**Plan:** [word-authoring-poc](../plans/word-authoring-poc.md) §5 WA3
**Status record:** [word-authoring-poc](../status/word-authoring-poc.md) (holds the commit hash)

## Invariant

An author marking up a contract in Word gets structural feedback without waiting for the worker, and
that feedback never edits the document behind their back. Two invariants carry it. First, detection
reads **only literal parts**: text already marked as a variable or a reference is settled, and a
suggestion is never raised against it. This is what keeps marking up idempotent, so running the
add-in twice over the same clause offers nothing the second time. It is the add-in's half of the
sketch's §4.1 text-part model (CCS §4.1: a part is a literal, a variable reference or an object
reference), and the reason offsets are defined over the **element** text rather than the part
(plan §2.5): a suggestion has to be applied to a range the author can see.

Second, every match reported is a single, non-overlapping claim on a range of that text. Overlapping
suggestions would let the add-in mark `5 days` inside the placeholder `[5 days]`, producing a
variable nested in a variable, which the Wording graph (WS2, WS4) cannot represent. The longest
match wins, so the author is offered the construct a lawyer would recognise.

Template findings and conformance are advisory throughout: every finding is a `warning` or an
`info`, never a `violation`. A document that departs from its template is still a document, and
ADR-A118's POC boundary means none of this is a platform contract. Conformance says nothing about
sections the template does not name, because `TemplateFindings` has already said the section is
unknown and repeating it would make the same defect produce two findings.

## Test cases

| ID | Given / When / Then | Level | +/− | Result |
|---|---|---|---|---|
| S3-01 | facility element 13 / detected / placeholder `[Agent]` at the UTF-16 offsets of its position in the element text, suggestion `mark-variable`, `text`, `agent` | L1 | + | pass |
| S3-02 | facility elements 11 and 13 / detected / money `GBP 250` (`gbp-250`) and duration `120 days` (`duration-120-days`). Every case of `contracts/authoring/fixtures/suggested-keys.json` gives its value type and key | L1, L3 | + | pass |
| S3-03 | literal `within [5 days] and 5 days` / detected / the placeholder `[5 days]` and the later `5 days`, and no duration inside the placeholder | L1 | − | pass |
| S3-04 | facility elements 14 and 15 / detected / `Loans` in 14 and `Loan` in 15 as defined-term with the Loan definition as target. In `Loaner` nothing. In definition 03 its own `Loan` is not reported | L1 | +/− | pass |
| S3-05 | facility element 08 / detected / nothing from the variable part `2.5 per cent` | L1 | − | pass |
| S3-06 | a literal `𝑥 costs GBP 5` / detected / money starts at offset 9 (the astral character counts 2) | L1 | + | pass |
| S3-07 | literal `subject to clause 4.1(a)` / detected / cross-reference with action `none` | L1 | + | pass |
| S3-08 | the catalog / loaded / three templates. A template resource missing `sections` / loading throws naming the file | L1 | +/− | pass |
| S3-09 | a licence snapshot without Restrictions, with Fees empty, a section `misc`, and a definition inside Grant / checked / one finding each: `required-section-empty` ×2, `unknown-section`, `element-kind-not-allowed` | L1 | − | pass |
| S3-10 | a snapshot with zero sections / checked / one `required-section-empty` per required template section (zero case) | L1 | − | pass |
| S3-11 | an analysis with a Prohibition in licence `grant` and a Permission in `grant` / conformance / one `term-kind-not-allowed` only | L1 | +/− | pass |
| S3-12 | an analysis with `relationClass` null in `interest`, and one element in an unknown section / conformance / one `no-term-kind`, nothing for the unknown section | L1 | +/− | pass |
| S3-13 | the licence sample / template findings / exactly one `unmarked-text` for `Fees are exclusive of VAT.` | L1 | + | pass |

The thirteen cases are carried by four test classes: `ConstructDetectorTest` (S3-01 to S3-07),
`CatalogTest` (S3-08, and the sample catalog beside it), `TemplateFindingsTest` (S3-09, S3-10,
S3-13) and `ConformanceCheckerTest` (S3-11, S3-12). The module runs 63 tests in total, WA2's 48
among them.

## One command

From the repository root:

```
mise run check:authoring-service
```

A pass prints `Tests run: 63, Failures: 0, Errors: 0, Skipped: 0` followed by `BUILD SUCCESS`. The
shade plugin's overlapping-resource warnings are expected and unchanged from WA2.

Re-run `mise run check:java` and `mise run check:authoring-contracts` to confirm nothing else moved.

## Artefacts to inspect

| What | Where | Look for |
|---|---|---|
| the detection rules | [ConstructDetector.java](../../../platform/authoring-service/src/main/java/org/nebularis/lattice/authoring/detection/ConstructDetector.java) | the `RULES` table reads as plan WA3's pattern table, in the same order |
| the suggested-key cases | [suggested-keys.json](../../../contracts/authoring/fixtures/suggested-keys.json) | all seven cases are asserted by S3-02, including the two that need the value-type prefix |
| the finding wording | [TemplateFindings.java](../../../platform/authoring-service/src/main/java/org/nebularis/lattice/authoring/template/TemplateFindings.java) | each message is one plain sentence naming the section heading, and the object id where it has one |
| the detection table for authors | [README.md](../../../platform/authoring-service/README.md) | kinds and actions only, as the plan asks |

## Self-probe

**The probe the plan names does not bite, and that is worth recording.** Plan WA3 says: "change the
overlap sort to start-first instead of length-first. S3-03 fails." It was made
(`comparingInt(Candidate::start).thenComparingInt(Candidate::order)`) and `ConstructDetectorTest`
still ran 7 tests with 0 failures.

The reason is a property of the rule set, not a weakness in S3-03. With these seven patterns, two
matches can overlap only by **containment**: every shorter match that overlaps a longer one lies
wholly inside it, because the only rule with author-supplied content is `defined-term`, and a
defined term that began before a money, date, duration or placeholder match and ended inside it
would have to be a term such as `A 5`. A contained match never starts earlier than its container,
so sorting by start and sorting by length descending accept the same candidates. The length-first
sort and the kind-order tiebreak are kept because the plan specifies them, but only their
containment behaviour is observable today.

A probe that does bite was run instead, against the invariant S3-03 actually protects. The overlap
rejection was removed, so every candidate is accepted:

```java
for (Candidate candidate : candidates) {
    if (true) {                       // was: no accepted candidate overlaps this one
        accepted.add(candidate);
    }
}
```

`mvn -f platform/pom.xml -pl authoring-service test -Dtest=ConstructDetectorTest` then failed:

```
ConstructDetectorTest.resolvesOverlapsByLength:66 ... expected: <2> but was: <3>
```

with the third detection being `5 days` at 8..14, inside the placeholder at 7..15 — exactly the
nested variable the invariant forbids. The rejection was restored and the full command re-run green
at 63 tests.

## Implementer choices

| Left open | Chosen | Why |
|---|---|---|
| where the plan's `Detection`, `Suggestion` and `Finding` records live | new `detection` and `template` packages | they are read by WA4's API and WA5's service, so they are not internal to one class |
| `kind` of a detection and of a finding, and `action` of a suggestion | `String`, holding the common-schema enum value | the plan lists these as records and names no Java enum for them, and WA4 serialises the value as it stands. `severity` is the existing `model.Severity`, which plan §5 WA2 does name |
| `TemplateCatalog.raw` | `Optional<JsonNode>`, not the plan's bare `JsonNode` | the plan gives `SampleCatalog.raw` as `Optional`. Matching them means WA4's two endpoints answer a missing id the same way |
| `AuthoringTemplate` fields | `templateId`, `version`, `title`, `domain`, `sections` only | nothing in WA3 or WA4 reads the template's variable declarations as Java: the add-in gets them from `raw(id)` |
| `TemplateFindings` and `ConformanceChecker` | static `check` methods on final classes | neither holds state |
| finding order, "template section order, then snapshot order" | template sections in order (each one's `required-section-empty` then its elements' `element-kind-not-allowed` in snapshot order), then `unknown-section` in snapshot order, then `unmarked-text` in snapshot order | unknown sections have no place in template order, so they follow it |
| S3-08's "template resource missing `sections`" | `contracts/authoring/amqp-topology.json`, read as a template | `contracts/authoring/fixtures/**` is excluded from the service jar by the module pom, so `fixtures/invalid/authoring-template--no-sections.json` is not on the classpath. Using a shipped resource that genuinely has no `sections` avoids adding a test resource tree for one assertion. A missing resource is asserted beside it |
| reading a shipped JSON resource and validating it | one new method, `ContractSchemas.readValidated` | both catalogs need it, and `ContractSchemas` already owned both halves |

## Deliberate non-coverage

- **Partial overlaps between detection rules**, and therefore the kind-order tiebreak, for the
  reason set out under Self-probe. If a later slice adds a rule with author-supplied content that
  can start mid-match, a case must be added here.
- **`property-policy` detections and findings.** Both catalogs load all three templates and samples
  (S3-08), but the finding and detection rules are exercised on the facility and licence documents.
  The third sample is covered end to end by WA10's stack tests.
- **The `term-kind-not-allowed` path for `Deeming` and `Exclusion`.** The rule is a set membership
  test, exercised once; the term kinds themselves are covered by WA1's schema tests.
- **Whether a clause really reads as the term kind the analysis claims.** That is WA6's work, and
  WA3 takes `relationClass` as given.
- **Detection and findings over the HTTP boundary**, including their JSON shape against
  `snapshot-accepted` and `analysis-view`: WA4.

Unit-wide non-coverage, cited by every pack: CCS assembly, amendments, tables and versioned
elements. LE2 parsing of the generated program. Concurrent editing. Authentication. Poison-message
retry limits. Real Word, except through WA11's manual checklist.
