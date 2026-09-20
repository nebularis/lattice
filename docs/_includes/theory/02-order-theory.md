## 2. Order theory, and why it's called LATTICE
{: #order}

A **lattice**, in the mathematical sense the project takes its name from, is a partially ordered set in which every pair of elements has both a unique greatest lower bound (a *meet*) and a unique least upper bound (a *join*). That's a more specific claim than "things are ordered" — it's a claim about *structure*: given any two elements, there's always a well-defined "most specific thing both fit under" and "least specific thing that covers both." Concept hierarchies have exactly this shape, which is why lattice theory turns up wherever ontologies, taxonomies, or type systems are involved.

LATTICE leans on order theory at three distinct scales, and it's worth seeing them side by side, because they're the same mathematics doing three different jobs.

### The layer dependency order is a strict partial order

The rule "a lower layer never names a term belonging to a higher one" defines a strict partial order over the layers — some pairs are directly comparable (Foundation precedes Vocabulary), some are only comparable through a chain (Foundation precedes Behaviour, via several intermediate steps), and a few are simply incomparable (Eligibility and Instrument's shared dependency on Party doesn't make Eligibility and Instrument comparable to each other). Drawing that order as a diagram is exactly a **Hasse diagram** — the standard way order theory visualises a partial order, where an edge means direct precedence and nothing implied by transitivity is drawn twice.

<div class="mermaid">
graph TD
  fnd["Foundation"] --> voc["Vocabulary"]
  voc --> qnt["Quantification"]
  qnt --> pty["Party"]
  qnt --> srf["Surface<br/><span style='font-size:11px'>(imports Foundation, Vocabulary,<br/>Quantification only — nothing<br/>above imports it back)</span>"]
  pty --> elg["Eligibility"]
  pty --> bhv["Behaviour"]
  elg --> ins["Instrument"]
  ins --> bhv
  elg --> bhv
  classDef surf fill:#14223a,stroke:#d4a8ff,color:#f4f7ff;
  class srf surf;
</div>

This order is exactly what makes an automated import-closure check meaningful in CI: with an unambiguous partial order, "did anything import upward" becomes a single well-formed question instead of a matter of convention.

### Closure operators, appearing three times under three names

A **closure operator** takes a relation and extends it to include everything reachable by following that relation any number of times (its reflexive-transitive closure), and a relation only supports a *well-defined* closure if it's acyclic — otherwise "everything reachable" is either infinite or ill-defined. LATTICE needs exactly this operation in three unrelated-looking places, and it's worth naming them together because the repository itself never quite says "these are the same mathematical operation" in one place — but they are:

| Where | The relation being closed over | What "well-founded" buys |
|---|---|---|
| Eligibility's `HierarchicalMatch` | A concept scheme's `skos:broader` ordering | A candidate satisfies a condition exactly when it's in the reflexive-transitive closure of the bound scheme's ordering, restricted to that scheme's members — and a scheme with a cycle simply isn't evaluable under this strategy at all. |
| Surface's `ClosureRelation` index form | A declared closure basis (often also `skos:broader`, but stated explicitly, never assumed) | Every carrier instance gets a generated relation to every in-scope ancestor of its value, so a query never walks the taxonomy live — but only after the generator itself has traversed the basis and confirmed it's acyclic, since no fixed SHACL shape can check that for an arbitrary declared relation. |
| Quantification's ordering machinery | An `OrderingBasis`'s priority-ordered components | A deterministic tie-break, so two events sharing a timestamp resolve the same way everywhere, rather than however a database's insertion order happens to land. |

<div class="mermaid">
graph BT
  leaf["industrial-fire"] -->|broader| mid["fire"] -->|broader| top["peril"]
  leaf -.->|"closure: matches self"| leaf
  leaf -.->|"closure: matches ancestor"| mid
  leaf -.->|"closure: matches ancestor"| top
  classDef base fill:#101a2d,stroke:#2a3a56,color:#f4f7ff;
  classDef closure fill:transparent,stroke:#9df7d7,color:#9df7d7,stroke-dasharray: 4 3;
  class leaf,mid,top base;
</div>

Well-foundedness (no cycles) is stated in LATTICE as a **runtime claim, not a static one** — SPARQL cannot express a property path over a *variable* predicate, so no fixed SHACL shape can verify acyclicity for a relation that's only known at declaration time. The generator has to actually walk the graph and check, and it records the result as evidence (a discharged law) rather than a proof anyone could have derived by inspection alone.

### Ordered value spaces

Quantification generalises the same theme one level further down, into raw values: every `ValueSpace` states, explicitly, which order theory shape it has — a **total order** (every pair comparable, like a number line), a **cyclic order** (like clock positions, where "which is lower" has no consistent answer without picking an arbitrary cut point), or **no order** (equality-only, comparable but not rankable). Getting this declaration right is what makes a bounded region — a `Range` for a total order, a `CyclicRange` for a cyclic one — a well-defined concept in the first place, rather than a guess about what "between" ought to mean for a particular kind of value.
