<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# LegalRuleML proposal trial

Whether an earlier, reviewed mapping helps a language model propose a new one, as MORK expects (MORK README §5.18). Two Sonnet agents proposed a MORK scheme from the LegalRuleML metamodel to LATTICE with the same proposal tools, goal and rules, on 2026-10-29. Only the warm run was given the ODRL history: the approved ODRL pack and the lessons drawn from the ODRL trial's review ([`odrl-lessons.txt`](odrl-lessons.txt)). LegalRuleML has no reference pack, so each correspondence was reviewed by hand against Instrument's model, and the maintainer signed the reviews off as recorded on 2026-10-29. They are in [`history.ttl`](history.ttl).

| | Cold | Warm |
|---|---|---|
| check rounds to a clean check | 6 | 3 |
| correspondences reviewed | 17 | 28 |
| accepted | 4 (24%) | 19 (68%) |
| corrected | 9 | 0 |
| rejected | 2 | 3 |
| deferred | 2 | 6 |

The warm run took the ODRL pack's shape, a term and a template with a relation under it and roles for its parties, which is where the cold run went most wrong: it named role occupancies, which stated meaning never names, and terms without the template they are. Both runs made a LegalRuleML right a permission, which is half of it: its definition gives the bearer a permission and implies obligations or prohibitions on the auxiliary party, so in Instrument it is two relations under one term, and neither run stated the relation owed to the bearer. The first review called the permission wrong, from Instrument's sense of a right as a claim, and was amended on reading LegalRuleML's definition. The history keeps both reviews, the later one deciding. The warm run proposed more and deferred more, mapping temporal characteristics, authorities and jurisdictions that LATTICE has no settled term for.

The result is consistent with MORK's expectation, and does not yet show it. There is one run of each, the review was not blind to which run was which, and the approved pack as a worked example likely did more than the lessons, which the warm agent said transferred little beyond what not to do. A test of the lessons alone, and several runs of each, would separate them.

| Folder or file | What it is |
|---|---|
| [`legalruleml-metamodel.ttl`](legalruleml-metamodel.ttl) | the metamodel's twelve files merged as one Turtle file for the tools |
| [`cold/`](cold), [`warm/`](warm), [`cold-2/`](cold-2) | each run's attempts with their findings, `proposal.mcn`, `notes.md` and `score.json` |
| [`sample-supply-terms.ttl`](sample-supply-terms.ttl) | a sample source, a made-up supply agreement in the metamodel, which the check runs a proposal over |
| [`history.ttl`](history.ttl) | both runs, their mappings, and each review |

Found in passing: the check counted an uncertain mapping, which a proposal uses for a question to its reviewer, as an error, so both agents avoided them. It now reports one for review.

## Cold run 2, 2026-10-30

A third Sonnet agent, with no history, given the improved proposal tools (cards with each term's utility, `describe`, a check that holds the output on [`sample-supply-terms.ttl`](sample-supply-terms.ttl) to the layers' shapes, the translation table and five target-side cassettes), and the same brief. The review is by hand against Instrument's model, as before.

| | Cold | Warm | Cold 2 |
|---|---|---|---|
| check rounds to no error | 6 | 3 | 5 |
| correspondences reviewed | 17 | 28 | 32 |
| accepted | 4 (24%) | 19 (68%) | 20 (63%) |
| corrected | 9 | 0 | 2 |
| rejected | 2 | 3 | 0 |
| deferred | 2 | 6 | 10 |
| tokens | 135,094 | 157,814 | 116,986 |
| time | 164 s | 207 s | 159 s |

Without any history, cold run 2 came close to the warm run. It named roles, never occupancies, stated every term as a template, and stated the prohibition a permission excepts (law I8), each of which the first cold run got wrong. It was the first run to map a right's claim end, an obligation the auxiliary party owes the bearer, though not its permission half. Its two corrections: a guard dropped any prohibition without an auxiliary party instead of leaving the obligee to the reviewer, and the right's term lacks its permission. Its ten deferrals are the five acts and their labels, which it minted from each specification's label, since the act lies in the rule's formula and the sample gives none. It did not map reparations or penalty statements, judging that the source gives them no parties.

What the agent found missing, not yet changed: the pack does not say an activity is a `skos:Concept` (which `describe` does), nor how to declare several prefixes, which two rounds were spent on.

