# Run 2 notes

## Rounds
Three check rounds. Attempt 1 was a minimal permission with its implied prohibition and had no errors. Attempt 2 added the prohibition, its remedy, the policy-level obligation and the permission's duty. Attempt 3 added the permission's constraints as a scope. All three reported zero errors, so the rounds added coverage, not fixes. The final check (attempt-3.json) has 0 errors, 4 findings at severity info (ContextShape), 71 output triples.

## What the mapping does
- The agreement is a stated term (ins:Term, ins:Template). Parties become one pty:Role template.
- odrl:permission becomes an ins:Permission under the term, holder the assignee, counterparty the assigner, with the ins:Prohibition it excepts (law I8) minted from the action, as the permission cassette does.
- odrl:prohibition becomes an ins:Prohibition, obligor the assignee and obligee the assigner. Its odrl:remedy becomes an ins:Obligation with ins:arisesOnBreachOf the prohibition, under a term of its own.
- The policy-level odrl:obligation and the permission's odrl:duty become ins:Obligation, obligor the assignee and obligee the assigner.
- The permission's constraints become an elg:AdmissionProfile scope. A spatial eq constraint is an elg:ExactCondition with the place as required concept. A dateTime lt constraint is an interval condition with an open upper bound. Each is picked by a guard on odrl:leftOperand.

## Confidence and doubts (mork:weighting out of 100, doubt in notes)
Permission 80, prohibition 85, remedy 75, obligation 70, duty 55, scope 70, place 75, date bound 50. The weakest are the duty, which is not tied to the permission it conditions (ins:fulfilledWhen unused), and the date, which is a literal xsd:date read through qnt:numericValue where the value space expects a number. The operator is not mapped, so lt and eq are fixed by the guards' assumption, not read. The obligee of the policy-level obligation and the remedy is assumed to be the assigner.

## What helped
The cassettes were close to a template, especially permission, remedy-on-breach and interval-condition. The translation table settled right, duty and remedy. The check's error-free first round and info-only findings made it easy to extend. The guard payload syntax in the notation document was needed for the constraints.

## Hard or missing
- The sample's rules are untyped blank nodes, so concepts had to be paths from the agreement, with inverse paths to reach the parties. This is verbose, one concept per rule kind and party.
- Party role labels are not mapped. Role_T has no per-party name, since the shared role has no single path.
- No tool showed whether a rule or party in the sample was left unmapped. The check gives no coverage view, only errors.
- Dates have no obvious target. A temporal quantity needs a numeric or a typed literal, and I found no card telling which.
- Odrl:Set and odrl:Offer policies are not covered, only odrl:Agreement.
- Only the sample was checked, so the guards and paths are unproven on other policies.
