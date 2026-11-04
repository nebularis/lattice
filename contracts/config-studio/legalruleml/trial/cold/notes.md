# Cold trial notes (LegalRuleML to LATTICE)

Check rounds: 6 (attempt-1 to attempt-6, attempt-5 kept as a failed probe). Final `proposal.mcn` equals attempt-6, 0 errors, 0 warnings, 294 triples. 17 mappings.

## Rounds
1. Positional inline `[sh:prefix ...]` refused under `sh:declare`.
2. Typed inline (`[sh:PrefixDeclaration ...]`) decodes, but 6 `BadPath` errors: prefix not found.
3. Declaring the prefix on the mapping scheme as well as the representation scheme fixes it. 0 errors.
4. Added Compliance, Violation, guarded temporal mapping, and three `MU` mappings (Jurisdiction, Authority, LegalSource): 3 `Uncertain` errors.
5. Tried `hy` hypothesis on an `MU`: same error. An `MU` always errors at compile.
6. Dropped the three `MU` mappings (recorded below as unmapped). 0 errors.

## Easy
Teaching pack decision ladder, the glue direction rule (exact vs inverse R-Box) and the cassettes gave the structure. `candidates` and the target cards found the legal relations quickly.

## Hard or missing
- No MCN example for an RDF source: how to write `sh:declare`, `mork:appliesWhen` and `mork:format mork:RDF` had to be found by trial. The codebook has no code for `sh:declare` or `mork:appliesWhen`, and a CURIE escape needs a typed (not positional) inline node, which the error message does not say.
- The prefix must be declared on the mapping scheme for a path to resolve, not only on the representation scheme (the task text said so, the pack does not).
- The pack teaches `MU` as the way to record doubt, yet any `MU` is a compile error, so the check cannot be clean while an unmappable term is recorded. I dropped them and recorded them here.
- The check does not run the mapping, so the path semantics (e.g. `lrmlmm:Bearer` is a property named like a class) and the R-Box glue direction are unverified.
- LATTICE has no jurisdiction, authority or legal-source term in the layers read. No place for Override (instrument `excepts` is close), Context/Association, SuborderList, Strength.
- Bearer/AuxiliaryParty targets are role occupancies in LATTICE, while LegalRuleML points at a Term (often a variable or role). Resolving it needs more than the metamodel.

## Mappings
| source term | target terms | confidence | why |
|---|---|---|---|
| lrmlmm:PrescriptiveStatement | ins:Term | 60 | a provision that prescribes behaviour, the nearest container of relations. Could also be an ins:Template (stated meaning). |
| lrmlmm:Obligation | ins:Obligation | 90 | same meaning. |
| lrmlmm:Prohibition | ins:Prohibition | 90 | same meaning. |
| lrmlmm:Permission | ins:Permission | 85 | same meaning, ins:Permission is "despite a prohibition". |
| lrmlmm:Right | ins:Permission | 50 | a right also implies duties on others, only the permission half is mapped. |
| lrmlmm:Role | pty:RoleOccupancy | 55 | a role filled by an actor behaves as an occupancy, not as pty:Role. |
| lrmlmm:Bearer (of Obligation) | ins:obligor, pty:RoleOccupancy | 85 | bearer is who must perform. |
| lrmlmm:Bearer (of Prohibition) | ins:obligor, pty:RoleOccupancy | 85 | prohibition is an obligation. |
| lrmlmm:Bearer (of Permission) | ins:holder, pty:RoleOccupancy | 85 | bearer holds the permission. |
| lrmlmm:AuxiliaryParty (of Obligation) | ins:obligee, pty:RoleOccupancy | 70 | the related party is usually who it is owed to, but not defined so. |
| lrmlmm:AuxiliaryParty (of Permission) | ins:counterparty, pty:RoleOccupancy | 70 | the party against whom it holds. |
| lrmlmm:filledBy | pty:occupiedBy, pty:Actor | 65 | actor filling a role. |
| lrmlmm:Reparation | ins:OnBreach | 55 | links a penalty to a rule whose violation triggers it. |
| lrmlmm:PenaltyStatement (via appliesPenalty) | ins:Term, ins:arisesOn | 55 | the penalty arises on the breach trigger. Mapped as a term, not a relation, since its deontic content is in a nested statement. |
| lrmlmm:Violation | bhv:Breached | 55 | exact A-Box match to a state, but Violation is a specification, not a state. |
| lrmlmm:Compliance | bhv:Performed | 55 | same reasoning. |
| lrmlmm:TemporalCharacteristic (forStatus InForce, guarded) | fnd:TemporalScope | 35 | only the in-force characteristic gives a validity period. Start and end times (rulemm:Time) are not mapped, since the metamodel gives no value path. |

Unmapped, no LATTICE term found: lrmlmm:Jurisdiction, lrmlmm:Authority, lrmlmm:LegalSource (ins:expressedIn is the nearest, 25), lrmlmm:Override, lrmlmm:Context, lrmlmm:Association, lrmlmm:SuborderList, lrmlmm:Strength, lrmlmm:toPrescriptiveStatement (breached rule link: ins:ofObligation expects an obligation, not a statement).
