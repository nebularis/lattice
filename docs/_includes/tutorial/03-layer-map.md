<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

## 3. The layer map
{: #layers}

LATTICE is a stack of small ontologies, each with one job. A layer may build on layers below it and
never on layers above. If you know dimensional modelling, think of conformed dimensions that every
mart shares, then marts that add their own facts on top, with the difference that the rule is
written down and checked.

### The substrate and what sits on it

**Substrate layers** hold mechanisms that make sense in any domain: identity, reference data,
amounts, parties, conditions, text structure and state. They name no industry. **Instrument** is
the first ontology built on them, the general shape of an agreement and the legal relations it
creates. **Applied modules** under `ontology/applied/` add domain content, such as the insurance
peril vocabulary, or cross-domain content not yet general enough for the substrate, such as
capacity that can be drawn down.

In the diagram an arrow points from a layer to a layer that builds on it.

<div class="mermaid">
graph BT
  fnd["Foundation<br/>identity, versions, keys"] --> voc["Vocabulary<br/>reference data bound per contract"]
  voc --> qnt["Quantification<br/>amounts, units, ranges"]
  qnt --> pty["Party<br/>actors and roles"]
  pty --> elg["Eligibility<br/>conditions and decisions"]
  elg --> wrd["Wording<br/>what the text says"]
  elg --> bhv["Behaviour<br/>states and transitions"]
  wrd --> ins["Instrument<br/>what the agreement binds parties to"]
  bhv --> ins
  voc --> cls["applied: Classification"]
  cls --> icm["applied: Insurance common"]
  pty --> icm
  qnt --> prl["applied: Insurance peril"]
  bhv --> cap["applied: Capacity"]
  classDef applied fill:#14223a,stroke:#f3cf8e,color:#f4f7ff;
  class cls,icm,prl,cap applied;
</div>

The substrate order is strict. A layer may import any layer below it in the chain, so Party can use
Foundation directly as well as through Vocabulary. Wording and Behaviour are siblings, and neither may
name the other. `mise run check:import-guard` fails the build if any substrate layer imports, or even
names, a layer above it or beside it. The applied modules follow their own one-way rule. A
cross-domain module never imports a domain module, and a domain module never imports another
domain's.

Only the main imports are drawn. The full lists are in each document's `owl:imports`, as you saw for
the classification module in chapter 1.

### Beside the stack

Some parts of LATTICE are not layers that your data lives in. They work on the layers from outside.

| Part | What it does | Chapter |
|---|---|---|
| **Persistence** | declares which storage pattern each class uses, such as how concurrent writes and uniqueness are handled, and compiles that choice to SPARQL. It imports no layer and no layer imports it. It refers to classes by IRI | 11 |
| **Surface** | restates values reachable along a path as direct statements, so common questions need no long traversal | 11 |
| **MORK** | maps source material, such as schemas, records and free text, onto a target ontology, and compiles mappings and conditions to SPARQL, SHACL and other forms | 13 |
| **Governance** | the planned home for checks across all layers together, such as whether reference data meets its declared contracts. Its folder holds no content yet | 13 |
| **SPC** | a formal model of the exchanges between agents. Developed separately and not yet joined to the layers | 13 |

### Inside a layer

Every layer has the same folder layout, present in whole or in the parts that layer needs.

| Folder | Holds | Relational counterpart |
|---|---|---|
| `README.md` | the layer's specification, written as prose with the Turtle inside it | the design document |
| `spec/` | the ontology, generated from the README | the DDL |
| `shapes/` | SHACL constraints | constraints and check rules |
| `vocab/` | the layer's own fixed code lists | seed reference data |
| `examples/` | worked instances, the files this tutorial quotes | test fixtures |
| `projection/` | declared contracts connecting this layer to another, for example Eligibility's to Party | published interfaces |

The README is the source of truth. The `spec/`, `vocab/` and `shapes/` files are extracted from it,
and the extractor has a check mode that reports any drift between them. When a layer's behaviour surprises you, its README says why it was designed that way,
usually with a pointer to the decision record (ADR) behind it.

### Versions

Each document carries a semantic version in its version IRI, and the documents that import it pin
that exact version. A change that could break an importer raises the major number. Every release is
listed on the site's [Ontology Releases](./architecture/ontology-releases.html) page.

### Where the chapters go from here

Chapters 4 to 9 climb the substrate with the facility agreement, from its keys to its covenant
default. Chapter 10 adds the applied capacity module for drawdowns. Chapter 11 steps beside the stack
to store and serve the result. Chapter 12 shows how the insurance domain is built on the same
substrate, as a model for a domain of your own.
