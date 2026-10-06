<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Assurance records

**Unit:** [formal-methods](../plans/formal-methods.md), track A. **Status:** sketch, 2026-10-06,
revised after review ([response](../notes/formal-methods-review-response.md)). Nothing here is
ratified. The profile's home is FM-D3.
**Parent:** [formal methods](formal-methods.md) §7.4 and §11, which this details.

---

## 1. The problem

A claim of correctness is only as useful as the reader's knowledge of what exactly was established,
how, over what, and on what assumptions. LATTICE needs one record for that, for its own laws and for
adopters' instruments, that a report, a release gate, a regulator and a recipient of an exchanged
contract can all read, and that a recipient can check rather than merely believe.

## 2. A profile, not a new vocabulary

| Need | Existing standard | Used as |
|---|---|---|
| a claim, its subject, its result, who asserted it | W3C EARL (a Working Group Note, no longer maintained, which a profile tolerates) | `earl:Assertion`, `earl:subject`, `earl:test`, `earl:result`, `earl:assertedBy`, `earl:mode` |
| outcomes | EARL | `earl:passed` (Holds), `earl:failed` (Fails), `earl:cantTell` (not decided), `earl:untested` |
| the check as an activity, its tool and inputs, its time | PROV-O | `prov:Activity` with `prov:used` for tool and specification, `prov:wasAssociatedWith`, `prov:endedAtTime` |
| a shape check's evidence | SHACL | `sh:ValidationReport`, linked as evidence |
| tool identity and an attestation a recipient can verify | in-toto and SLSA | an attestation per evidence activity, signed through ADR-A40's adapters |

The profile adds only what those lack, in Executable's vocabulary (prefix `exe:` illustrated as
`asr:` below until FM-D3 places it):

| Term | Meaning |
|---|---|
| `asr:statedAs` | the statement's name in the theory, or the property's source text. A label only |
| `asr:statementDigest` | the digest of the normalised statement and of every definition it depends on. **This, not the name, is the claim's identity** |
| `asr:method` | Proof, ModelCheck, SolverCheck, PropertyTest, ShapeCheck, Review |
| `asr:scope` | what the claim quantifies over: every instrument, every binding of a template, this instrument over all runs, this instrument to a bound, this corpus |
| `asr:bound`, `asr:complete` | for bounded methods: the bound, and whether the space was exhausted |
| `asr:assumes` | each assumption the claim rests on: fairness, a template's rely conditions, an encoding's faithfulness, an abstraction |
| `asr:dischargedBy` | for an assumption, the claim that discharges it |
| `asr:model`, `asr:abstraction` | for a model check: the model's digest, and the abstraction with its own evidence |
| `asr:assumptionAudit` | for a proof: the prover's assumption listing (Rocq's `Print Assumptions`, Isabelle's check over `sorry`, oracles and `axiomatization`) |
| `asr:resourceEnvelope` | the machine, memory and time a bounded or timed-out result depended on |
| `asr:staleSince` | set when a tool identity changes, until the claim is re-verified |
| `asr:advisory` | the witness, counterexample trace and timings, recorded but not part of the claim's identity |

Tool and specification identities are digests. A name and version ("rocq 9.0") is a label beside
the digest, never the identity.

## 3. The claim

```turtle
# Hypothetical. asr: stands for the profile's terms, whose home is FM-D3.
[] a earl:Assertion ;
    earl:subject elg:L15 ;
    earl:assertedBy <https://deployment.example/agent/ci> ;
    earl:result [ a earl:TestResult ; earl:outcome earl:passed ] ;
    asr:statedAs "Eligibility.SetReadings.l15" ;
    asr:statementDigest "sha256:7c1e..." ;
    asr:method asr:Proof ;
    asr:scope asr:EveryCandidate ;
    asr:assumptionAudit "Closed under the global context" ;
    prov:wasGeneratedBy [ a prov:Activity ;
        prov:used <urn:sha256:...prover-image> , <urn:sha256:...specification> ] .

[] a earl:Assertion ;
    earl:subject <https://insurer.example/id/contract/property-pro-0412/2026-03-01> ;
    earl:result [ a earl:TestResult ; earl:outcome earl:passed ] ;
    asr:statedAs "always balance(paid) <= balance(aggregate)" ;
    asr:statementDigest "sha256:51d0..." ;
    asr:method asr:ModelCheck ;
    asr:scope asr:ThisInstrumentAllRuns ;
    asr:complete true ;
    asr:model "sha256:9ab2..." ;
    asr:abstraction <https://deployment.example/abstraction/ledger-thresholds> .
```

The second claim is an inductive invariant, checked as one, so it holds for every run rather than to
a bound.

## 4. Rules

| # | Rule |
|---|---|
| AR1 | every evidence activity names its tool and specification by digest |
| AR2 | a bounded result names its bound and completeness, and is never reported as a proof |
| AR3 | not decided is an outcome in its own right. A timeout or a reached bound is never Holds |
| AR4 | a claim's level is the pair of its scope and its method, ordered by scope first, then method. A complete model check of a small abstraction does not outrank an exhaustive test of a larger domain merely by method. SolverCheck is not ranked above a bounded ModelCheck, since both are often bounded and the solver's encoding is itself an assumption |
| AR5 | a Proof claim records its assumption audit. A claim whose audit shows an unproved assumption is recorded as such, never as Proof |
| AR6 | a claim stated against an interface records that some instantiation discharges the interface's assumptions. A claim over an interface no instantiation realises is marked vacuous |
| AR7 | a temporal claim that passes records a witness that its antecedent is reachable, or is marked vacuity-unchecked |
| AR8 | every claim names its assertor, not only reviews |
| AR9 | a claim's identity is its subject and statement digest. Its advisory part (witness, trace, timing) is outside its identity |
| AR10 | an instrument claim is a derived artefact (ADR-A92) whose semantic read set is the instrument version, the statement and the specification. A tool change marks it stale and schedules re-verification, without invalidating it. A tool release that fixes a known soundness bug marks the claims it produced suspect, which fails the gate until they are re-verified. A re-verification with a different verdict is a finding (FM-D15) |
| AR11 | the profile has its own shapes and positive and negative fixtures, like every LATTICE vocabulary |

## 5. The law report and the release gate

The report lists every law of every layer with its claims, levels, coverage (positive and negative
fixtures) and the columns of track A's consistency checks (joint satisfiability, independence,
non-vacuity). It joins the release's provenance ledger (ADR-A39).

| Gate | Rule |
|---|---|
| no unreviewed restatement | a claim whose statement digest changed fails the gate unless a reviewed change record accompanies it |
| no unexplained regression | a level may fall only with a reviewed change record, so that restating a law more precisely is never punished |
| no failure | any claim with outcome failed fails the gate |
| no stale gate | a stale claim does not fail the gate, but a release report lists it |
| no repeated not-decided | a not-decided claim cannot satisfy a declared target twice without an attempt at a higher bound |
| coverage | each law may declare a target level and a coverage target (at least one negative fixture). Shortfalls are reported, and fail only where declared as required |

## 6. Statements about assurance

The record is the only source of any assurance statement, in a report, a user interface, a
certificate or a document. Every rendering shows method, scope, bound and assumptions in the same
visual unit as the verdict. "Verified" is not used. "Proved", "checked for every run of this
abstraction", "checked to depth 40", "tested on 12,000 cases" and "shape-checked on this corpus"
are. A statement not generated from a record is a release-blocking defect.

## 7. Exchange

An exchanged claim carries its statement digest, specification digest, tool digests, assumption set,
abstraction where there is one, and a signed attestation, so a recipient can check it and re-run it
with the named tools and inputs. Proof scripts travel with templates a market body publishes, and not
by default with instrument claims. Counterexample traces are tenant data, classified and retained as
such, and leave the tenant only on the owner's decision.

A crosswalk from claim levels to the evidence categories insurance supervisors and model-risk
functions use is worth building once the first adopter asks, since it is what makes the record
readable to them.

## 8. Open questions

| # | Question | Leaning |
|---|---|---|
| AS-R1 | Executable's vocabulary, Foundation, or a new small vocabulary? | Executable's, as a profile (FM-D3) |
| AS-R2 | Should laws declare target levels in the ontology, or in the plan? | in the ontology, beside the law, with a coverage target |
| AS-R3 | Are human reviews evidence? | evidence of the lowest level, with a scope and an expiry. A review of one statement digest is no evidence about the next |
