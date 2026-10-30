# Review of the mapping proposer's inputs, after the ODRL and LegalRuleML trials

Reviewed 2026-10-30. What the proposing agents were given, where it stopped helping, and six changes in order of value against cost. Held here to refine the proposer once the MORK studio module is built.

## What the agents were given

| Input | Size | What it carries |
|---|---|---|
| teaching pack (L0, doctrine, two cassettes, codebook) | about 18 KB | notation and the decision ladder. Two generic cassettes, neither from an RDF source |
| target cards, four layers | about 43 KB, 11k tokens | one line per term, the first sentence of `rdfs:comment`, placement |
| source cards | about 28 KB | the same for ODRL |
| read outside the tools | about 50 KB | the MORK and `mork_rdf` READMEs, the MCN specification |

The reviews' most frequent corrections each break a semantic rule the target layer states, and none of those rules reaches the cards. For example a permission excepts a prohibition whose obligor is its holder (I8), stated meaning names roles and never occupancies (I13), a term is also a template, and a condition's kind is chosen by `elg:matchStrategy` as an individual, never by a subclass.

## Recommendations

| # | Change | Why |
|---|---|---|
| R1 | a `describe_term(curie)` tool returning a term's full comment, its `fnd:utility`, its properties by domain and range, its individuals and every shape message naming it | Instrument's comments total 5.7 KB and its utility 22 KB, and the cards drop utility, which states each rule the agents broke. An agent reads twenty terms deeply instead of a hundred shallowly, and the cost grows with the source |
| R2 | `check_mapping` validates what a proposal writes on a sample with the target layers' shapes (Instrument's 37, Eligibility's, Party's) | it reported no error for a scheme the pack rejected or corrected in 27 of 35 mappings, since it checks MCN and the MORK compile, never the meaning written. Needs a sample for every trial, which LegalRuleML lacked |
| R3 | a generated translation card for legal vocabulary from Instrument §4.4 and §4.6 (right, duty, claim, liability, rule, norm, condition, deadline), and `skos:altLabel` and `skos:hiddenLabel` synonyms in the literate READMEs, indexed by `cards.py` and `rank.py` | about 700 tokens. BM25 over labels cannot reach `ins:ClaimHolder`, `ins:Permission` or `ins:Power` from "Right". Regime's altLabel "Dispensation" shows the mechanism exists |
| R4 | six to eight target-side cassettes of ten to fifteen lines each: a relation under a stated term, a party role, a concept condition, an interval condition with sense and closure, a trigger on breach, the implied prohibition of a permission. `mork:DAGTemplate` may carry the same shapes | the warm run beat the cold one because the ODRL pack showed how terms compose, which per-term cards cannot. About 1.5k tokens each |
| R5 | lessons generated as rules from `mork:reviewNote`, grouped by target term, with recurring ones promoted to MTP's minimal pairs | the 35-row ledger carried little beyond what not to do. One generalised note, such as "a subclass proposed where the layer chooses by an individual", covers six corrected rows |
| R6 | cards fall back to `fnd:utility` when a term has no comment, and stop cutting at 160 characters | Behaviour has 45 cards with no definition, Quantification 27, Eligibility 11, nearly all individuals such as states and kinds |

An `ask_target(question)` tool over the knowledge index's term search is a further option. The index ranked `ins:Power` at 0.82 for "a legal relation whose holder can change a counterparty's position by an act", which BM25 over labels cannot do.

## What was done, 2026-10-30

| # | Done | Where |
|---|---|---|
| R6 | a card gives a term's `rdfs:comment` or its `fnd:utility`, whichever is longer, uncut, as the maintainer chose. The 83 empty cards stay empty: those terms of Behaviour, Quantification and Eligibility carry neither annotation, so the review's fallback could not fill them | `tools/mork/src/mork_propose/cards.py` |
| R1 | `describe_term` gives a term's comment and utility, place, properties, individuals and the messages of the shapes that name it | `tools/mork/src/mork_propose/describe.py` |
| R2 | the check runs a proposal over its sample and validates the output against every layer's shapes with OWL RL entailment, each result on the mapping that wrote it. What the context supplies, a persisted identity or a term's clause, is information. On the ODRL trial's proposal it reports 20 errors where it reported none, and the pack is clean. LegalRuleML gained a sample source. A proposal run records its start and tokens | `tools/mork/src/mork_propose/check.py`, `contracts/config-studio/legalruleml/trial/sample-supply-terms.ttl` |
| R3 | a translation table in MTP's data, as the maintainer chose over labels in the layers, carried as a card in the teaching pack and indexed by the ranking | `ontology/mork/mtp/data/translations.yaml` |
| R4 | five target-side cassettes, each run over a shared sample in a test and held to the layers' shapes | `ontology/mork/mtp/data/cassettes/C-*.yaml`, `ontology/mork/examples/Patterns/` |
| R5 | rules from a history, grouped by what was corrected or by the reviewer's note, with recurring ones marked as candidate minimal pairs for a person to promote | `History.rules`, `mork:propose -- lessons` |
| `ask_target` | waits until R1 to R3 are measured, as the maintainer decided | |

## Trying the rest of MORK on the trials, 2026-10-30

| Part | What it gave | Where |
|---|---|---|
| the re-runs | ODRL accepted 58% where it accepted 23%, in 107k tokens where it spent 191k. LegalRuleML cold accepted 63% where it accepted 24%, near the warm run's 68% | the trial READMEs |
| recognition (`mork_communities.recognition`) | nothing as a ranking signal between two vocabularies: 2% of ODRL's confirmed targets in its first ten and 40% of LegalRuleML's, against 18% and 90% for BM25 with the translation table, and fusing it in lowers the ranking. It compares surface forms, which suits a data dictionary's field names against concepts, the ACORD case, and that is where it belongs | `benchmark/mork-candidate-ranking` |
| communities, projections and DAG templates | `mork_communities` reads a source as `mork:Representation` sections, which an RDF source mapped by concepts and paths does not have. Observing the mapping DAGs instead, a root mapping and everything beneath it as a section, gives three sensible communities: LegalRuleML's deontic specifications with their bearer and auxiliary party, ODRL's rules with their parties and action, and ODRL's constraints with their operators. Each projects to the target shape the cassettes teach. No community spans the two standards, since their vocabularies share no term. What carries over between standards is the target side, which projections and DAG templates record | `tools/mork/src/mork_propose/baseline.py`, `contracts/config-studio/communities-baseline.ttl` |
| persistence | a Turtle baseline beside the trials, written by `mise run mork:communities-baseline` from the reviewed mappings, the same for the same reviews: sorted observations, communities numbered by their first member, a version digested from the observations. A deployment would keep the same graph in its store, and the confirmed corpus from real use stays private | |

Not changed in `mork_communities`: its scheme version and observation times read the clock, and its materialisers nest their own folder under the base given. The baseline works around both.

## Register gaps

The index answered the rules side weakly because Instrument §4.4 and §4.6, the proposer tools, the trials and the doctrine's new invariants are not register entries.
