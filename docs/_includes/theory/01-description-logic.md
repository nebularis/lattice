## 1. Description logic and the open-world graph
{: #dl}

Everything in LATTICE sits on top of a **description logic** — the family of decidable logics that OWL (the Web Ontology Language) is built from. A description logic is, deliberately, a *restricted* fragment of first-order predicate logic: it gives up some expressive power in exchange for a guarantee that a machine can always finish checking what follows from what you've asserted, in finite time. Full first-order logic doesn't promise that. Description logics are engineered specifically so a reasoner never has to say "I don't know if this terminates."

<div class="mermaid">
graph TD
  RDFS["RDFS<br/><span style='font-size:11px'>subclass, subproperty,<br/>domain, range</span>"] --> EL["OWL 2 EL<br/><span style='font-size:11px'>existential restrictions,<br/>owl:hasValue — polynomial-time</span>"] --> DL["OWL 2 DL<br/><span style='font-size:11px'>full class expressions,<br/>cardinality, disjointness</span>"]
  EL --- usedByA["Surface's nominal index form<br/>σ(v) ≡ Carrier ⊓ ∃R.{v}<br/>deliberately stays inside EL"]
  DL --- usedByB["SPC's structural layer:<br/>sorts, behaviours, session types"]
  RDFS --- usedByC["SPC's domain-refinement predicates<br/>target EL++, a further-restricted fragment"]
  classDef base fill:#101a2d,stroke:#2a3a56,color:#f4f7ff;
  classDef usage fill:transparent,stroke:#9df7d7,color:#9df7d7,stroke-dasharray: 3 3;
  class RDFS,EL,DL base;
  class usedByA,usedByB,usedByC usage;
</div>

Two consequences of choosing a description logic show up constantly once you start reading LATTICE's specifications:

#### The open-world assumption

A description-logic reasoner never treats the absence of a statement as evidence that the statement is false. If nothing in the graph says who occupies a `RoleOccupancy`, the reasoner concludes nothing about who occupies it — not "nobody," just "unstated." This is the right default for a graph assembled incrementally from many sources, but it has a sharp consequence: a genuinely *closed* question ("is this `GovernanceState` one of exactly four values, and no others") cannot be answered by OWL classes alone, because OWL can never conclude a class extent is exhaustive. LATTICE's answer, used throughout, is to keep the OWL class open and push the closed question into a SHACL shape (`sh:in` over named individuals) — SHACL validates a graph as it stands, right now, closed-world, which is precisely the complementary tool OWL's semantics deliberately withholds.

#### Picking the right fragment, on purpose

Not every part of LATTICE needs the same amount of logical horsepower, and asking for more than you need has a real cost: OWL 2 DL is decidable but can be expensive to reason over; OWL 2 EL is deliberately restricted so that classification stays polynomial-time even over very large ontologies. Surface's nominal-class index form is a direct, stated example of choosing EL on purpose — a generated class is defined as `Carrier ⊓ ∃R.{v}`, using `owl:hasValue`, specifically because that construct is inside OWL 2 EL. A form requiring more expressive power than EL would need its own index kind; the design note is explicit that this was a deliberate tractability trade, not an oversight. SPC makes the identical trade at a larger scale: its structural layer (sorts, behaviours, session types) is written in full OWL 2 DL, because the structural questions genuinely need that expressiveness, while its domain-refinement predicates — the part that reaches into an imported ontology to constrain a message payload — are recommended to stay inside the tractable **EL++** fragment specifically so a reasoner checking those constraints doesn't inherit DL's worst-case cost.
