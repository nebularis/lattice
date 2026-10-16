<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

## 13. Where next
{: #next}

You have followed one facility agreement from its keys to its storage. This chapter covers the parts
of LATTICE the facility did not need, helps you decide which parts your own project would take, and
points to where each is explained in depth.

### The parts beside the stack

**MORK** maps source material onto a target ontology: database schemas, records, spreadsheets and
free text. A mapping is itself data, so it can be reviewed, versioned and reused. MORK's compilers
turn mappings, and Eligibility conditions as in chapter 8, into SPARQL, SHACL and other forms. For a
data architect bringing existing data into LATTICE, this is the part to read next. Its
[README](https://github.com/nebularis/lattice/blob/main/ontology/mork/README.md) is a plain-English
guide that starts from the integration problem.

**Governance** is the planned home for checks run across all layers at once, such as whether every
bound code list meets its contract. Its folder holds no content yet.

**SPC**, a subject-oriented process calculus, is a formal model of the exchanges between agents,
human or software, that drive the state changes of chapter 9. It is developed separately and not yet
connected to the layers.

**Formal methods.** Several layers state their rules as numbered laws, such as Instrument's I8 in
chapter 6 and Eligibility's L9 in chapter 8. A formal-methods programme checks some of them with
model checkers and proof assistants, beyond what tests can show.
[Formal Methods in the Development Lifecycle](https://github.com/nebularis/lattice/blob/main/docs/developer/formal-methods-lifecycle.md)
explains how.

### Which parts would your project take?

LATTICE is a framework, so the answer depends on the problem. A starting point:

| If your project needs to | Start with |
|---|---|
| version records and keep durable identity separate from natural keys | Foundation (chapter 4) |
| govern reference data that differs by context or changes over time | Vocabulary (chapter 7) |
| handle amounts with units, conversion and additivity rules | Quantification (chapter 7) |
| model who holds which role, from when, alone or in groups | Party (chapter 6) |
| state eligibility rules and get explainable three-valued answers | Eligibility (chapter 8) |
| track status as a state machine with full, caused history | Behaviour (chapter 9) |
| hold contract text and its legal meaning side by side | Wording and Instrument (chapters 5 and 6) |
| manage limits, quotas or budgets drawn down by demands | Capacity (chapter 10) |
| write graph data safely under concurrency, with unique keys | Persistence (chapter 11) |
| serve fast answers to long-path questions | Surface (chapter 11) |
| bring existing data in | MORK (above) |

Each layer can be taken with the layers below it and nothing above. A project that needs only
versioned reference data, for example, takes Foundation and Vocabulary.

### Further reading

| Read | For |
|---|---|
| [The LATTICE Field Guide](./book.html) | a thorough tour of every layer, Surface and MORK |
| [Theoretical Foundations](./theory.html) | the mathematics behind the design, in plain terms |
| [Architecture diagrams](https://github.com/nebularis/lattice/blob/main/docs/diagrams/README.md) | five views of the whole system |
| [Glossary](./glossary.html) | the project's terms, defined |
| [Ontology architecture](https://github.com/nebularis/lattice/blob/main/docs/architecture/ontology-architecture.md) | the layers in depth, with their dependency rules |
| [Architecture decision records](https://github.com/nebularis/lattice/blob/main/docs/architecture/decisions/README.md) | why each design choice was made |
| [Ontology Releases](./architecture/ontology-releases.html) | every released version of every document |
| [Getting started](https://github.com/nebularis/lattice/blob/main/docs/developer/getting-started.md) | installing the toolchain, when you want to run things |

Each layer's README under
[`ontology/`](https://github.com/nebularis/lattice/tree/main/ontology) is its full specification,
written to be read, and every example this tutorial quoted sits in that layer's `examples/` folder
with a header saying what it shows.

A hands-on companion to this tutorial is planned. It will have you install the toolchain, validate
these examples, break a shape and read the report, and compile a condition to SPARQL.
