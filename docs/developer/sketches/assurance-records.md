<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Assurance records

**Unit:** [formal-methods](../plans/formal-methods.md), phase 2. **Status:** sketch, 2026-10-06.
Nothing here is ratified. The vocabulary's home is FM-D3.
**Parent:** [formal methods](formal-methods.md) §7.4 and §11.3, which this details.

---

## 1. The problem

A claim of correctness is only as useful as the reader's knowledge of how it was established. A law
may be proved, model-checked to a bound, solver-checked, property-tested or only shape-checked, and
an instrument's property may hold for every run or only for runs of length twelve. LATTICE needs
one way to record which, for its own laws and for adopters' instruments, so that a report, a
release gate and a regulator can all read it.

## 2. Two subjects, one record

| Subject | Example | Who writes the record |
|---|---|---|
| a law of a layer | `elg:L15`, `wrd:W3`, `ins:I7` | LATTICE's CI, per release |
| a property of an instrument version | "payments never exceed the aggregate" for one policy | the toolchain, per instrument version |

Both are the same structure: a statement, and evidence for it.

## 3. The vocabulary

Hypothetical, prefix `asr:`. FM-D3 decides whether it is a part of Executable's vocabulary, beside
derived artefacts and diagnostics, which is the leaning.

| Term | Meaning |
|---|---|
| `asr:Claim` | a statement that something holds: a law, or an instrument property |
| `asr:about` | what the claim is about: a law individual, or an instrument version |
| `asr:statedAs` | the formal statement's name in the theory, or the property's text in the property language |
| `asr:evidence` | an evidence node |
| `asr:Proof` | checked by a proof assistant's kernel |
| `asr:ModelCheck` | checked by a model checker, with `asr:bound` (a depth or a number of positions) and `asr:complete` when the state space was exhausted |
| `asr:SolverCheck` | decided by an SMT solver, with the encoding's version |
| `asr:PropertyTest` | property-based tests, with `asr:cases` and `asr:seed` |
| `asr:ShapeCheck` | a shape's verdict over a corpus, with `asr:shape` |
| `asr:Review` | a human review, with its agent and date |
| `asr:result` | `asr:Holds`, `asr:Fails`, or `asr:NotDecided` (a bound was reached) |
| `asr:counterexample` | a trace or a witness, where the result is Fails |
| `asr:tool`, `asr:specification` | the tool and its version, the specification and its digest |

```turtle
# Hypothetical.
[] a asr:Claim ;
    asr:about elg:L15 ;
    asr:statedAs "Eligibility.SetReadings.l15" ;
    asr:evidence [ a asr:Proof ; asr:result asr:Holds ;
                   asr:tool "isabelle-2025" ; asr:specification "sha256:..." ] ,
                 [ a asr:ShapeCheck ; asr:result asr:Holds ; asr:shape elg:L15Shape ] .

[] a asr:Claim ;
    asr:about <https://insurer.example/id/contract/property-pro-0412/2026-03-01> ;
    asr:statedAs "always paid(insurer) <= aggregate" ;
    asr:evidence [ a asr:ModelCheck ; asr:bound 40 ; asr:complete false ;
                   asr:result asr:NotDecided ; asr:tool "apalache-0.47" ] .
```

## 4. Rules

| # | Rule |
|---|---|
| AR1 | Every evidence node names its tool and version, and the digest of the specification it checked against |
| AR2 | A model check names its bound and whether it was complete. A bounded result is never reported as a proof |
| AR3 | `NotDecided` is a result in its own right. A timeout or a reached bound is never `Holds` |
| AR4 | A claim's strongest evidence is its assurance level, ordered Proof, complete ModelCheck, SolverCheck, bounded ModelCheck, PropertyTest, ShapeCheck, Review |
| AR5 | An instrument claim is a derived artefact (ADR-A92) whose read set is the instrument version, the specification and the tool. It is regenerated when any of them changes |

## 5. The law report and the release gate

The report lists every law of every layer with its assurance level and evidence. It is generated
per release and joins the release's provenance ledger (ADR-A39).

| Gate | Rule |
|---|---|
| no regression | a release fails if any law's assurance level is lower than in the previous release |
| no failure | a release fails if any claim's result is Fails |
| declared targets | each law may declare a target level. A release reports, without failing, the laws below target |

## 6. Instrument assurance in exchange

An instrument's claims travel with it. In the InsurML toolchain they sit in the contract package
beside the assembled contract and its graph, so a recipient can see what was checked, how and to
what bound, and can re-run the check with the named tool and specification.

## 7. Open questions

| # | Question | Leaning |
|---|---|---|
| AS-R1 | Executable's vocabulary, Foundation, or a new small vocabulary? | Executable's (FM-D3) |
| AS-R2 | Should laws declare target levels in the ontology, or in the plan? | in the ontology, beside the law, so the README states the intended assurance |
| AS-R3 | Are human reviews evidence, or only context? | evidence of the lowest level, since some laws are judgements that no tool checks |
