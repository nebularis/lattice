<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# LegalRuleML proposal trial

Whether an earlier, reviewed mapping helps a language model propose a new one, as MORK expects (MORK README §5.18). Two Sonnet agents proposed a MORK scheme from the LegalRuleML metamodel to LATTICE with the same proposal tools, goal and rules, on 2026-10-29. Only the warm run was given the ODRL history: the approved ODRL pack and the lessons drawn from the ODRL trial's review ([`odrl-lessons.txt`](odrl-lessons.txt)). LegalRuleML has no reference pack, so each correspondence was reviewed by hand against Instrument's model, and the maintainer signed the reviews off as recorded on 2026-10-29. They are in [`history.ttl`](history.ttl).

| | Cold | Warm |
|---|---|---|
| check rounds to a clean check | 6 | 3 |
| correspondences reviewed | 17 | 28 |
| accepted | 4 (24%) | 16 (57%) |
| corrected | 9 | 3 |
| rejected | 2 | 3 |
| deferred | 2 | 6 |

The warm run took the ODRL pack's shape, a term and a template with a relation under it and roles for its parties, which is where the cold run went most wrong: it named role occupancies, which stated meaning never names, and terms without the template they are. Both runs made a LegalRuleML right a permission, where Instrument makes it the claim end of an obligation, so neither transferred that. The warm run proposed more and deferred more, mapping temporal characteristics, authorities and jurisdictions that LATTICE has no settled term for.

The result is consistent with MORK's expectation, and does not yet show it. There is one run of each, the review was not blind to which run was which, and the approved pack as a worked example likely did more than the lessons, which the warm agent said transferred little beyond what not to do. A test of the lessons alone, and several runs of each, would separate them.

| Folder or file | What it is |
|---|---|
| [`legalruleml-metamodel.ttl`](legalruleml-metamodel.ttl) | the metamodel's twelve files merged as one Turtle file for the tools |
| [`cold/`](cold), [`warm/`](warm) | each run's attempts with their findings, `proposal.mcn`, `notes.md` and `score.json` |
| [`history.ttl`](history.ttl) | both runs, their mappings, and each review |

Found in passing: the check counted an uncertain mapping, which a proposal uses for a question to its reviewer, as an error, so both agents avoided them. It now reports one for review.
