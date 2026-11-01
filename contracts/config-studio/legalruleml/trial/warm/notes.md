# Warm trial notes

Check rounds: 3 attempts, 7 `check` invocations (attempt-1 failed on `.RDF`, positional `sh:declare`, an undeclared `rdfs` path prefix and an unused-template iterator error, attempt-2 failed once on rebinding `rdf` then passed, attempt-3 passed). Final file: `proposal.mcn` (= attempt-3), 0 errors, 0 findings, 320 triples, 35 queries. No sample, so not run.

## Easy
- The earlier ODRL scheme gave the whole shape: root Datum per rule kind with `mappingFor`, a Term then Relation chain, parties by `templateMapping` of a Role template with `inverseRBoxMatch` to holder/obligor/obligee/counterparty.
- The lessons showed which mistakes recur (proposing a specific subclass where the scheme writes `Term`+`Template`, omitting the Role template, mapping sub-structure with no root).

## Hard or missing
- The metamodel has no property from a statement to its deontic specification, nor from a specification to its activity, scope or conditions (these sit in the RuleML XML in `hasTemplate`). So no activity, scope or condition mapping was possible, unlike ODRL.
- MCN has no code for `sh:declare` or `mork:appliesWhen`, and a positional inline node is refused under `sh:declare`. Used `!T` raw triples for the declarations and shapes.
- Temporal characteristics, penalties and jurisdictions attach to statements through Context/Association/`toTarget`, which a tree of composite mappings cannot follow, so these are roots with no link to the term.
- LATTICE has no jurisdiction or authority term. Guessed `skos:Concept` and `pty:Actor`.
- Deontic role values are `rulemm:Term` (variables or data), so the party label path is a guess.

## Taken from the ODRL mapping
Term/Relation split with `ins:Term`+`ins:Template` and relation `arisesUnder` (Obligation, Prohibition, Permission, Right, Reparation roots), Role_T and its label child, holder/obligor/obligee/counterparty wiring, obligation for a remedy/consequence as `arisesOnBreachOf` (Reparation), `appliesWhen` shapes as guards (Temporal_From/To), `dataRef` paths with `|` alternatives. Not taken: implied prohibition (LegalRuleML permissions are not stated to imply one), conditions and ranges (no source equivalent), the lessons' `numericValue` and `requiredConcept` rows (no source).

| ## Mappings: source term | target terms | confidence | why |
|---|---|---|---|
| lrmlmm:Obligation | ins:Term, ins:Template | 85 | as ODRL obligation root |
| lrmlmm:Obligation (relation) | ins:Obligation, ins:Template, ins:arisesUnder | 85 | as ODRL Obligation_Relation |
| lrmlmm:Bearer (of Obligation) | pty:Role, ins:obligor | 85 | ODRL assignee as obligor |
| lrmlmm:AuxiliaryParty (of Obligation) | pty:Role, ins:obligee | 55 | related party, not stated to be the one owed |
| lrmlmm:Prohibition | ins:Term, ins:Template | 85 | as ODRL prohibition root |
| lrmlmm:Prohibition (relation) | ins:Prohibition, ins:Template, ins:arisesUnder | 85 | as ODRL |
| lrmlmm:Bearer (of Prohibition) | pty:Role, ins:obligor | 85 | as ODRL |
| lrmlmm:AuxiliaryParty (of Prohibition) | pty:Role, ins:obligee | 55 | as for obligation |
| lrmlmm:Permission | ins:Term, ins:Template | 85 | as ODRL permission root |
| lrmlmm:Permission (relation) | ins:Permission, ins:Template, ins:arisesUnder | 85 | as ODRL |
| lrmlmm:Bearer (of Permission) | pty:Role, ins:holder | 85 | as ODRL |
| lrmlmm:AuxiliaryParty (of Permission) | pty:Role, ins:counterparty | 60 | counterparty is who the permission holds against, weaker than ODRL assigner |
| lrmlmm:Right | ins:Term, ins:Template | 70 | permission by definition, but implies duties on others |
| lrmlmm:Right (relation) | ins:Permission, ins:Template, ins:arisesUnder | 60 | implied obligations on auxiliary parties not stated |
| lrmlmm:Bearer (of Right) | pty:Role, ins:holder | 80 | Bearer is the permitted party |
| lrmlmm:AuxiliaryParty (of Right) | pty:Role, ins:counterparty | 65 | the parties bearing the implied duties |
| lrmlmm:Reparation | ins:Term, ins:Template | 55 | sanction linked to a statement |
| lrmlmm:Reparation (relation) | ins:Obligation, ins:Template, ins:arisesUnder | 45 | penalty as an obligation, as ODRL consequence, but its content is XML |
| lrmlmm:toPrescriptiveStatement | ins:arisesOnBreachOf | 30 | points at a statement, not an obligation |
| lrmlmm:appliesPenalty | ins:expressedIn | 30 | the penalty statement's text is the nearest term |
| lrmlmm:TemporalCharacteristic | fnd:TemporalScope | 35 | start/end only, status and time kind lost, no link to a term |
| lrmlmm:atTime (Starts) | fnd:validFrom | 35 | guarded on the Starts development, time value shape unknown |
| lrmlmm:atTime (Ends) | fnd:validTo | 35 | guarded on Ends |
| lrmlmm:LegalReference | fnd:Key | 40 | a reference ID within an ID system |
| lrmlmm:refID | fnd:keyValue | 55 | direct |
| lrmlmm:Authority | pty:Actor | 40 | a person or organisation with power, no link to a term |
| lrmlmm:Jurisdiction | skos:Concept | 20 | LATTICE has no jurisdiction term, ins:classification is the nearest |
| lrmlmm:Role / rulemm:symbolForData | pty:Role, rdfs:label | 60 | label path guessed |
Not mapped: lrmlmm:Violation, Compliance, SuborderList, Override, Strength, LegalSource (collections and other kinds with no LATTICE equivalent in scope).
