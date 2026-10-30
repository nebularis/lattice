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

## Register gaps

The index answered the rules side weakly because Instrument §4.4 and §4.6, the proposer tools, the trials and the doctrine's new invariants are not register entries.
