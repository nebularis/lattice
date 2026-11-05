# Trial run 1 notes

Check rounds: 9 attempts. Attempt 1 and 2 (decode error on an inline `sh:declare` node, fixed by a separate node line). Attempt 3 crashed the compiler (see below, no JSON kept). Attempts 4 to 8 fixed an IRI-vs-string code, then guard problems. Attempt 9 is the final, copied to `proposal.mcn`. Final check: 0 errors, 4 info findings (`Evidence`, the hypotheses), 85 triples written over the sample (492 triples in the decoded mapping, 379 queries).

I could only see counts, not the written triples. I verified the 85 by hand-counting what each part should write (56 for the plain rules, 3 for the duty trigger, 9 for the `eq` constraint, 17 for the `lt` constraint) and it matched.

## What the mapping does
- Policy (any ODRL policy class) becomes `ins:Instrument`.
- Each rule becomes one `ins:Term` + `ins:Template` (shared node `Map_Term`, glued with `ins:arisesUnder`) and one relation: permission to `ins:Permission` (holder = assignee role, counterparty = assigner role), prohibition to `ins:Prohibition`, obligation, duty, remedy and consequence to `ins:Obligation` (obligor = assignee role, obligee = assigner role). Parties are looked up through the rule or its enclosing rule and policy.
- Action becomes `ins:activity`, the ODRL action IRI kept as is.
- Remedy and consequence relations get `ins:arisesOnBreachOf` the relation they hang on. A duty of a permission gets an `ins:OnAct` trigger (`ins:arisesOn`) whose activity is the permission's action.
- Scope: `ins:scope` an `elg:AdmissionProfile` with `elg:hasCondition` for the target (an `elg:ExactCondition`, requiredConcept = the asset) and each constraint. Guards (`mork:appliesWhen`, SHACL shapes) pick by operator: eq an ExactCondition (requiredConcept), neq an ExactCondition (excludedConcept), isAnyOf/isA and isNoneOf a SetMembershipCondition, lt/lteq/gt/gteq an IntervalCondition with RangeSet, Range, upper or lower Bound, and a `qnt:Quantity` carrying the right operand. Each condition has an `elg:EvidenceBinding` with one step whose property is the left operand.

## What was easy
- The teaching pack's two cassettes plus the codebook gave the line shapes (`M`/`MD`, `f`, `xt`, `xr`, `cn`, `r`, `p`, `v`) almost at once. The codebook is compact and was enough for most lines.
- `candidates` ranked the right class first for Permission, Prohibition and Duty. The target cards were sufficient for choosing the relation classes and the condition classes.
- `check` messages for decode errors name the line and the code.

## What was hard or missing
- The teaching pack has no example of an RDF source, of a contextual datum, of the glue direction (`xr` versus `xi`), of templates, or of guards. I learned these from `tools/mork_rdf/README.md` and the MORK README, not from the pack. `xr` = child to parent, `xi` = parent to child for a contextual datum is stated only through the loan example's `xi :principal` and I confirmed it only by counting triples.
- No MCN code for `sh:declare`, `sh:prefix`, `sh:namespace`, `mork:appliesWhen`, `sh:property`, `sh:path`, `sh:hasValue`, `sh:in`, `sh:minCount`, `sh:nodeKind`, `rdf:first`/`rest`. I used CURIE codes, `!T` raw triples for the `sh:in` lists, and `rdfs:Resource` as a type for the prefix node. An inline `[#id sh:prefix ...]` is refused ("does not accept a positional inline node"), which the spec's text on `#id` form does not warn about.
- The `SH` payload sub-notation requires a target (`c`/`o`/`s`/`n`), and the guard compiler then refuses any `sh:targetClass`, and refuses `skos:inScheme`, which a `%K` block adds. So the payload cannot make a guard shape. I had to write shapes by hand with CURIE codes in `%X`. The spec says `%K` is for SHACL and says nothing about this.
- `ii` (`mork:individualIRI`) takes a string, not an IRI, and a bare local id crashes the compiler with a Python `PathError` traceback instead of a finding (attempt 3).
- The tool prints no output triples, so I could not see the direction of glue, the type of `stepIndex`, or whether `odrl:target?` returned the asset. Counts only.
- Prefix namespaces of `ins`, `pty`, `qnt` are not on the cards. I guessed `https://www.nebularis.org/neuro-semantic/lattice/<layer>#` from `elg` and `qnt` in the README and cassette. `check` did not validate this (a wrong namespace would pass).
- No individuals on the cards, so I could not name a bound closure (Closed/Open), a bound sense, an evidence step direction, a match strategy, a composition operation or a value space.
- `target-cards` is ~43 KB for four layers, with no filter by name.
- Teaching pack says "Record uncertainty as a note, not weighting", while the cassettes use `w` heavily and the README says weight drives confidence. I used both.

## Unsure mappings
- Roles (`Map_Holder` etc., w 75). In a stated Template a party may be a role, so assigner and assignee become two constant roles (`#Assignee`, `#Assigner`, minted in the mapping base) and the concrete party IRI is dropped. Whether that loses what the import needs, or should reuse workspace roles, is unknown. Permission holder = assignee and counterparty = assigner is my reading, not stated on the cards.
- Duty of a permission to `ins:Obligation` with an `ins:OnAct` trigger (w 70). The cards have no relation from an obligation to a permission it follows. `ins:arisesOnExerciseOf` takes a power only.
- Remedy and consequence with `ins:arisesOnBreachOf`. Faithful for a prohibition (a subclass of Obligation), but a consequence of a duty and a remedy are the same relation here.
- Interval conditions (w 60). Closure of lt versus lteq is lost, the value space is not given, and the literal goes into `qnt:numericValue` whatever its datatype (a date).
- Target as `elg:ExactCondition` with `requiredConcept` the asset IRI, though an asset is not obviously a `skos:Concept`. Its path `odrl:target?` is a hack to read the focus node itself, since a path cannot be empty. It also means a rule and its parent policy share the target condition node.
- Constraints lacking a binding subject class: an evidence binding has no `elg:subjectClass`.
- Not mapped (hypotheses `Hyp_*`): logical constraints (and, or, xone), isAllOf/hasPart/isPartOf, a literal under eq, action refinement, policy kind and profile, conflict and undefined strategies, odrl:output, party functions beyond assignee and assigner (attributedParty etc.), the Instrument-to-Term link (the cards show none for a stated term).
- Term and relation are two nodes per rule, joined by `ins:arisesUnder`. I did not find a card saying whether a stated Term should also carry the clause text (`ins:expressedIn`).

## Tool output read
About 120 KB of tool output in total, roughly 30,000 tokens: teaching pack (18 KB), ODRL source cards (28 KB), target cards (43 KB, instrument, eligibility, party, quantification, all read in part), about 20 candidate lists (~12 KB), check JSON (small). Plus docs read outside the tools, allowed: about 50 KB from `tools/mork_rdf/README.md` sections 4 to 15, `ontology/mork/README.md` sections 4 and 5.4 to 5.13, and `docs/architecture/mork-compact-notation.md` sections 3 to 12 and 16, 17 (roughly 15,000 tokens). The teaching pack alone was not enough to write a valid RDF-to-RDF scheme.
