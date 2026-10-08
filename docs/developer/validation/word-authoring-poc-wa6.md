<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: word-authoring-poc WA6, Logical English reading

**Plan:** [word-authoring-poc](../plans/word-authoring-poc.md) §5 WA6
**Status record:** [word-authoring-poc](../status/word-authoring-poc.md) (holds the commit hash)

## Invariant

LE-Q2 of [logical-english-alignment.md](../sketches/logical-english-alignment.md) asks where a
condition atom's sentence form lives, and answers "a rendering profile, so the T-Box gains
nothing for presentation". This slice is that profile, made real: a clause's text parts (CCS
sketch §4.1) are matched against a small table of sentence forms with no parser and no language
model, exactly as route D of the LE alignment sketch describes. Two invariants carry it.

First, **matching is total and deterministic over the sample texts**: every element of the three
samples reads as a form, a keyword class, or is honestly reported as unmatched, with the same
answer on every run (`best_match`'s tie-break — most fixed words, then earliest in the profile —
never leaves two equally good readings unresolved). Second, **the proposal graph never invents
meaning the tokens do not support**: a party is only asserted when a constant token actually names
a defined term, a variable binding only when a declared variable's value type matches what the
form's slot requires, and `wap:activityText` is only the literal substring a slot actually
consumed, not a paraphrase.

## Test cases

| ID | Given / When / Then | Level | +/− | Result |
|---|---|---|---|---|
| S6-01 | `utf16_len` and `utf16_index` / `"abc"`, `"𝑥a"` / 3, and index 1 → 2 | L1 | + | pass |
| S6-02 | facility element 06 / tokenised / constant, words, variable tokens with element-text offsets. Quotes and the final full stop give no token. A comma gives a punct token | L1 | + | pass |
| S6-03 | the profile / loaded / form ids unique, classes in TermKind, each template's slots match its items. Every form matches at least one element of the three samples | L1 | + | pass |
| S6-04 | `Borrower shall not create …` / `best_match` / `prohibition`, not `obligation` | L1 | + | pass |
| S6-05 | a party slot over a literal, a text slot with zero tokens, a rate slot over a duration variable / matched / no match each | L1 | − | pass |
| S6-06 | keyword rules / a table of nine sentences, one per rule and two with competing words (`shall be deemed`, `shall not`) / the table's classes | L1 | +/− | pass |
| S6-07 | every element of the three samples / analysed / spans sorted, non-overlapping, each word token inside exactly one span | L2 | + | pass |
| S6-08 | each sample / analysed / equals its committed `.analysis.json` | L2 | + | pass |
| S6-09 | the facility sample / LE program / equals `facility-agreement.le` | L2 | + | pass |
| S6-10 | the facility proposal / built / isomorphic (`rdflib.compare.isomorphic`) to the golden. Each relation has one `ins:expressedIn`. Each `ins:fromVariable` names a declared variable | L2 | + | pass |
| S6-11 | each sample's analysis / validated against `common` `#/$defs/Analysis` / passes | L3 | + | pass |
| S6-12 | every IRI constant in `namespaces.py` / looked up in `platform/authoring-service/src/main/resources/vocab/wording-provisional.ttl` / declared there | L3 | + | pass |
| S6-13 | a wording graph where one text has zero parts / analysed / that element has basis `none` and no spans, the rest are unaffected (zero case) | L1 | − | pass |

Carried by one test file, `test_wording_le.py`, 33 test functions (some parametrised; S6-06 alone
is three functions, S6-02 two). 67 tests run under `check:authoring-worker` in total: WA6's own
plus WA1's `test_authoring_contracts.py` (35), both named by the plan's own task.

## One command

From the repository root:

```
mise run check:authoring-worker
```

prints `67 passed` with no failures.

Re-run `mise run check:authoring-contracts` (35, a subset already included above),
`mise run check:authoring-service` (85, confirms the shared vocabulary file still loads and
nothing in the Java module regressed) and `mise run check:java` (9 modules) to confirm nothing
else moved.

## Artefacts to inspect

| What | Where | Look for |
|---|---|---|
| the twelve sentence forms | [forms/sentence-forms.json](../../../workers/src/lattice_workers/wording_le/forms/sentence-forms.json) | matches plan WA6's table exactly: formId, relationClass, template, items in the same order |
| the facility reading, element by element | [facility-agreement.analysis.json](../../../workers/tests/fixtures/wording_le/facility-agreement.analysis.json) | each `objectId`'s `relationClass`/`basis`/`formId` against plan WA6's "Expected facility readings" |
| the LE program a reviewer would read | [facility-agreement.le](../../../workers/tests/fixtures/wording_le/facility-agreement.le) | one `%` comment and one sentence per matched clause, `% ... unmatched: ...` for any that are not |
| the proposed meaning graph | [facility-agreement.proposal.ttl](../../../workers/tests/fixtures/wording_le/facility-agreement.proposal.ttl) | `ins:obligor`/`ins:holder` naming the right party for each relation (e.g. element 6's obligor is Lender, element 7's holder is Borrower) |
| the extended provisional vocabulary | [wording-provisional.ttl](../../../platform/authoring-service/src/main/resources/vocab/wording-provisional.ttl) | the new `ins:` relation classes and the `wap:` proposal-graph terms, each with a comment |
| the tie-break probe | `test_wording_le.py`'s `test_best_match_tiebreak_prefers_most_fixed_words_not_earliest_form` | a synthetic two-form profile, independent of the real table's incidental ordering |

## Self-probe

The plan's prescribed break — in `best_match`, prefer the earliest form instead of the most fixed
words — **does not fail S6-04, or S6-08, or anything else in the suite.** Checked directly: the
only two forms that structurally match "Borrower shall not create any security over its assets."
are `prohibition` (2 fixed words, profile index 4) and `obligation` (1 fixed word, profile index
5). Since `prohibition` already sits earlier in the profile's own table — independently of its
fixed-word count — "most fixed words, then earliest" and "earliest only" pick the same form. The
same holds across all 30 elements of the three samples: nowhere does a later-indexed, more-specific
form have to be preferred over an earlier-indexed, less-specific one, so S6-08's golden comparison
cannot distinguish the two implementations either. This is the third slice in this unit (after WA3
and WA5) where the plan's own prescribed probe turns out not to bite.

**A probe that does bite was added**: `test_best_match_tiebreak_prefers_most_fixed_words_not_earliest_form`
builds two synthetic forms, deliberately ordered so the one with fewer fixed words is listed
first, and asserts the one with more fixed words still wins. With the break applied:

```
test_best_match_tiebreak_prefers_most_fixed_words_not_earliest_form FAILED
AssertionError: assert 'few' == 'many'
```

while every other test, including S6-04 and S6-08, still passes. The break was reverted and
`mise run check:authoring-worker` re-run green at 67 tests.

## Implementer choices

| Left open | Chosen | Why |
|---|---|---|
| the JSON shape of `forms/sentence-forms.json` | `{"kind": "fixed", "words": [...]}` or `{"kind": "slot", "name": ..., "type": ..., "valueTypes": [...]}`, forms as `{formId, relationClass, template, items}` | the plan gives the twelve forms as a table of English descriptions, not a JSON encoding. This is the most direct structural translation of "Fixed(words)" and "Slot(name, type, value_types)" |
| `proposal_graph`'s access to slot detail | re-tokenises the element and re-runs `matcher.match` against the one form `formId` names (form basis), or re-scans tokens directly for the first non-ignorable constant (keyword basis) | the plan's own signature, `proposal_graph(wording, element_analyses, proposal_graph_iri, profile)`, takes the public `Analysis.elements` shape, which carries no slot names — only `formId` and `relationClass`. Matching is a pure function of tokens, form and declared variable types, so re-running it is deterministic and gives back the same match |
| where `wording-provisional.ttl` gets its `ins:`/`wap:` additions | extended in this slice, `platform/authoring-service/**` added to the path list | the WA4 status record's own note: "When WA6 builds the worker that writes the proposed meaning graph ... add that file to WA6's own path list and extend it there" |
| S6-02's comma case | a second test with a small ad-hoc literal, since facility element 06 (object id 2.1) has no bare comma — the one in "GBP 10,000,000" sits inside a variable's display text, which is tokenised as one whole token, not split | the same pattern WA3 used for cases its own samples did not happen to contain |
| S6-12's "every IRI constant in `namespaces.py`" | the five `Namespace` strings (`WRD`, `INS`, `WAP`, `PROV`, `DCTERMS`), each checked for a `@prefix` declaration in the vocab file | `namespaces.py` defines no bare term constants, only namespace objects and IRI-minting functions, so these five are the whole of what the module calls a constant |
| the tie-break rule's own test | added as a named test alongside S6-04, not a replacement for it | S6-04 is still correct and still run; the new test additionally isolates the one behaviour the plan's self-probe meant to protect |

## Deliberate non-coverage

- **LE2 parsing of the generated program.** The program text says so itself: "Not checked by an LE
  parser." Route B/C of the LE alignment sketch (import, differential test) are not part of this
  unit.
- **`software-licence` and `property-policy`'s LE program and proposal graph text.** Only
  `facility-agreement` gets `.le`/`.ttl` goldens, matching plan WA6's own "Goldens" section. The
  other two samples are covered by their `.analysis.json` goldens (S6-08) and the schema
  validation (S6-11), not by a line-for-line program or graph comparison.
- **Two defined terms that overlap as substrings** (e.g. "Loan" inside "Loaner"), beyond what the
  `term` slot's exact-token-sequence match already prevents by construction. Not a scenario any
  sample exercises.
- **Malformed or partially-written wording graphs** beyond the one documented error
  (`load_wording` raises `ValueError` when the wording node is absent) and the zero-parts case
  (S6-13). The worker's handling of a missing or unreadable graph is WA7.
- **The worker's RabbitMQ and Fuseki runtime.** WA7.

Unit-wide non-coverage, cited by every pack: CCS assembly, amendments, tables and versioned
elements. Concurrent editing. Authentication. Poison-message retry limits. Real Word, except
through WA11's manual checklist.
