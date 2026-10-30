# Cold trial 2, LegalRuleML deontic specifications

Check rounds: 5. Attempt 1 failed on undeclared rdfs prefix in paths and on activities, attempt 2 fixed the prefix but activities were literals, attempt 3 minted activity concepts but left the prohibition without an obligee, attempt 4 had no error, attempt 5 added weightings and notes and is the proposal.

## What the mapping does

- An lrmlmm:Obligation becomes a stated term with an ins:Obligation under it. The Bearer is the obligor and the AuxiliaryParty the obligee.
- An lrmlmm:Permission becomes a stated term with an ins:Permission. The Bearer is the holder and the AuxiliaryParty the counterparty. It also states the ins:Prohibition it excepts (law I8), named by the act, its obligor the holder.
- An lrmlmm:Prohibition becomes an ins:Prohibition, only where an AuxiliaryParty is given, which becomes the obligee.
- An lrmlmm:Right becomes the claim end only, an ins:Obligation owed by the auxiliary party to the bearer.
- Parties are pty:Role, labelled from the source label. The act is a minted skos:Concept named from the deontic's label.
- Weightings (out of 100) and notes are on the mappings that are doubtful.

## Not mapped

- Reparation and PenaltyStatement. A remedy needs the obligation it arises on breach of, as obligor and obligee, and the sample's reparation links only to a prescriptive statement and a penalty statement that carry a label. Nothing in the source says who owes the penalty, so any output would invent parties.
- Violation, Compliance, SuborderList, Strength, Override, contexts, temporal characteristics. Out of the scope of the request.
- The permission end of a Right, because it needs a stated prohibition to except.
- lrmlmm:Role and filledBy. LATTICE states roles and not occupancies, and the sample's roles are not linked to the deontic specifications, so they are not used.

## Result

320 output triples from 32 mappings. No error or warning remains. Four info findings (ContextShape) remain.

## What helped

- The cassettes, especially C-STATED-OBLIGATION and C-PERMISSION, were nearly the whole structure.
- The translation table settled right, claim, bearer and auxiliary party.
- The check's messages named the failing shape in words (an obligation is owed to at least one obligee, an activity is a concept).
- describe ins:activity showed the activity must be a skos:Concept.

## What was hard or missing

- The cassettes' src:act is not shown to be an IRI, so the first attempt used a literal and failed. A cassette or note that says an activity is a concept, and how to mint one from a label, would have saved two rounds.
- The syntax for several prefixes in sdl (repeat sdl, no comma) is not in the pack.
- Which skos terms the target declares is not stated. skos:prefLabel was refused, rdfs:label accepted.
- The guard syntax came from docs/architecture/mork-compact-notation.md.
- A prohibition with no counterparty cannot be expressed, and the guard hides it silently. The sample prohibition is not mapped, and no finding reports it.
