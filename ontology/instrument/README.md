<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Instrument Ontology — Terms and Legal Relations

Literate specification for the Lattice Instrument Ontology layer.

---

## 1. Purpose and Scope

This ontological substrate allows a user to state what legally binding outcomes an agreement binds its parties to. An instrument is expressed in an assembled wording (linking back to the `wording` ontology). Its clauses give rise to terms, and its terms to the five legal relations: what a party must do, must not do, may do despite a prohibition, need not do, and can do to change another's position. Each can be written and checked as structured data.

### 1.1 Dependencies 

Instrument imports Foundation, Vocabulary, Quantification, Party, Eligibility, Wording and Behaviour's configuration document. Instrument's runtime document is upstream of it. Nothing outside Instrument imports it ([ADR-A104](../../docs/architecture/decisions/ADR-A104-instrument-terms-and-legal-relations.md), [ADR-A106](../../docs/architecture/decisions/ADR-A106-behaviour-configuration-runtime-occasions-and-records.md)).

This version (0.10.0, CCS slice C7a) holds the instrument, its terms in two tiers, the five relations, their parties and their content (C6), and the legal triggers, the regimes they move, and the gating of relations by a regime's state (C7a). Later slices add, in order:

| Slice | Adds |
|---|---|
| C7b | due ranges, recurrence and ending, survival, definitions and deemings, sections, classification of terms, resolution of parties that depend on the case |
| C8 | parameter bindings from variables, encoding status, law I17's shapes |
| C9 | amendments, consent rules, incorporation, instruments made under a power |

Nothing in this version evaluates.

## 2. Namespace and Prefixes

```turtle-spec
@prefix ins:  <https://www.nebularis.org/neuro-semantic/lattice/instrument#> .
@prefix fnd:  <https://www.nebularis.org/neuro-semantic/lattice/foundation#> .
@prefix pty:  <https://www.nebularis.org/neuro-semantic/lattice/party#> .
@prefix elg:  <https://www.nebularis.org/neuro-semantic/lattice/eligibility#> .
@prefix wrd:  <https://www.nebularis.org/neuro-semantic/lattice/wording#> .
@prefix bhv:  <https://www.nebularis.org/neuro-semantic/lattice/behaviour#> .
@prefix qnt:  <https://www.nebularis.org/neuro-semantic/lattice/quantification#> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .
@prefix rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
```

```turtle-spec
<https://www.nebularis.org/neuro-semantic/instrument>
	rdf:type owl:Ontology ;
	owl:versionIRI <https://www.nebularis.org/neuro-semantic/lattice/instrument/0.10.0> ;
	owl:imports <https://www.nebularis.org/neuro-semantic/lattice/foundation/0.4.0> ,
				<https://www.nebularis.org/neuro-semantic/lattice/vocabulary/0.4.0> ,
				<https://www.nebularis.org/neuro-semantic/lattice/quantification/0.6.0> ,
				<https://www.nebularis.org/neuro-semantic/lattice/party/0.6.0> ,
				<https://www.nebularis.org/neuro-semantic/lattice/eligibility/0.8.0> ,
				<https://www.nebularis.org/neuro-semantic/lattice/wording/0.4.0> ,
				<https://www.nebularis.org/neuro-semantic/lattice/behaviour/0.11.0> .
```

The vocabulary (`ins-voc:`) is `vocab/instrument-vocab.ttl`, in the namespace `https://www.nebularis.org/neuro-semantic/lattice/instrument/vocab#` (§13).

## 3. Extraction Contract

This README is the source of three kinds of file. `tools/literate_extract.py` concatenates every ` ```turtle-spec ` block into `spec/instrument.ttl` and every ` ```turtle-vocab ` block into `vocab/instrument-vocab.ttl`, and writes the three ` ```turtle-shapes ` blocks, in order, to
`shapes/structural.ttl`, `shapes/constraints.ttl` and `shapes/single-expression.ttl`. A ` ```turtle-example ` block is illustration only.

```bash
python tools/literate_extract.py ontology/instrument/README.md --layer instrument --root . \
    --shapes shapes/structural.ttl shapes/constraints.ttl shapes/single-expression.ttl
```

## 4. Terminology

A lawyer reads words such as "term", "obligation", "exclusion" and "power" as terms of the art developed over millennia of law making, with centuries of meaning behind them. By contrast, a software engineer reads terms like "relation", "template" and "variable", in the context of computing. The naming convention for this layer attempts to adopt the terms a contract lawyer would recognise. This section defines, for every class and property, where its name comes from and why it was chosen over the alternatives. Historical naming conventions and adjustment decisions are recorded in the [CCS sketch](../../docs/developer/sketches/computable-contract-substrate.md) §1.1 and §2, CC-D1 and ADR-A104.

### 4.1 Contract

The word "contract" can refer to any one of three things: words on a page, the rights and duties those words create, and a whole agreement resulting from the other two meanings:

| Word | Its meaning in law and financial markets | In LATTICE |
|---|---|---|
| **wording** | the text and form of a contract: "policy wording", "loan agreement wordings", "the wording of clause 5". A market's own text model, for example, would be something like the LMA **Wording Information Model** | the Wording layer (`wrd:`): text and its structure, with no claim to legal effect |
| **instrument** | a formal legal document that creates, defines or transfers rights and duties: a deed, a contract, a policy, a licence. From the Latin *instrumentum*, a means or tool, and in Roman and later law a written document of record | this layer (`ins:`): the rights and duties a wording creates |
| **contract** | the legally binding agreement itself, and colloquially its document | the **computable contract**: a wording and an instrument together. No layer or class is called Contract, since a layer holding only part of the whole would claim all of it |

```mermaid
flowchart LR
    W["Wording<br/>what the contract says<br/>wrd:Wording, wrd:Element"]
    I["Instrument<br/>what it binds the parties to<br/>ins:Instrument, ins:Term, relations"]
    C["computable contract<br/>the two together"]
    W -- "expresses" --> I
    W --> C
    I --> C
```

### 4.2 Classes

#### 4.2.1 **`ins:Instrument`.** 

Has the same meaning as the legal sense above: one version of the legal instrument, expressed in one assembled wording. Distinct from *contract* (which would name the whole), *agreement* (one kind of instrument, and a deed or a licence is not always considered one), or *document*.

A document codifies an *instrument* when it is **operative**: executing it changes the parties' legal positions. For example, a lease grants a tenancy, a guarantee makes the guarantor answerable for another's debt, a licence permits what would otherwise be forbidden, or a facility agreement commits lenders to lend.

An instrument changes over time, by amendment, variation, or restatement, and remains the same instrument. LATTICE models this longevity with Foundation's versioning capability: each `ins:Instrument` is one **version**, and every version of one instrument shares one `fnd:PersistentIdentity`. The persistent identity carries the instrument's keys, such as an agreement number (Foundation §8), and any runtime state, such as which regime it is in (ADR-A106). A version represents what was agreed at a point in time: it is expressed in exactly one assembled wording (law I1), and its bound terms belong to it.

`ins:Instrument` acts as an aggregate for the purposes of versioning. Terms and relations are treated as part of their owning clause or instrument version, and change only when it does (law I18). That constaint ensures there is only one answer to "what did the parties agree on 1 March": the instrument version in force on 1 March, its wording, and its bound terms.

```mermaid
flowchart LR
    ID["persistent identity<br/>the agreement itself<br/>keys, runtime state"]
    V1["instrument version 1<br/>signed 1 January"]
    V2["instrument version 2<br/>after an amendment, 1 July"]
    W1["assembled wording 1"]
    W2["assembled wording 2"]
    V1 -- "hasIdentity" --> ID
    V2 -- "hasIdentity" --> ID
    V1 -- "supersededBy" --> V2
    V1 -- "expressedIn" --> W1
    V2 -- "expressedIn" --> W2
```

#### 4.2.2 **`ins:Term`.**

In contract law, a "term" is a provision the parties are bound by: "the terms of the agreement", "an implied term", "terms and conditions". A term may be *express*, stated in the words, or *implied*, by statute, custom or the course of dealing between the parties. "Term" has a second sense, of duration ("the term of the lease", "a five-year term"), which LATTICE handles with Foundation's `TemporalScope`. Note that `ins:Term` means only the provision and not the duration.

The following similar, but distinct terminology, is provided for reference here.

- **A Provision**, which means both a clause and what a clause provides, and was retired from the ontology for that duplication 
- **A Clause**, which is a piece of text, wording's element type
- **A Condition**, which in contracts has three senses: a heading ("General Conditions"), a class of term
  whose breach lets the other side terminate (a condition, as against a warranty), and a contingency
  ("subject to the following condition"). Contingencies are `elg:Condition`, and the class of a term
  is its classification (C7b). No `ins:` class is named Condition
- **A Norm** or **A Statement**, which are words of legal theory that a contract lawyer would not use for a
  provision
  
**Express and implied terms.** Most terms are *express*: the parties wrote them, and a clause states
each one. Some terms bind the parties although no clause states them. They are *implied*:

- **by statute**: many legal systems imply into a sale of goods a term that the goods are of
  satisfactory quality and fit for their purpose, whatever the contract says
- **by custom**: a usage so settled in a trade that the parties are taken to have agreed it
- **by the course of dealing**: terms the same parties have always used in their past contracts
- **in fact**: a term so obvious, or so necessary to make the contract work, that it goes without saying

An express term is a stated term, expressed in a clause. An implied term has no clause to express it, so it has no stated meaning. Its bound term names its source instead (`ins:impliedBy`). 

**A term is not a clause.** A clause is a piece of text. A term is what the parties are bound by.
They usually line up one to one, but not always:

- one clause may state several terms: "The Supplier shall deliver the goods by 1 March, and shall
  pack them for sea transport" is two provisions in one sentence
- one term may need several clauses to state it, when a definition, the main clause and a schedule
  together make one provision. Its stated term is then expressed in the element that contains
  them, such as their section (law I2 requires it to map to exactly one wording element version)

Since a term gives rise to relations, and in a well-modelled contract it is common for one term to give rise to more than one (§16.1, clause 8.1), it has been modelled as an independent node. The law treats a term as a unit, and several things attach to the whole provision rather than to any one relation under it:

| Attaches to the term | Meaning | Slice |
|---|---|---|
| its relations, definitions, deemings, and qualifiers | these determine what the provision creates | C6, C7b, C8 |
| classification | a *condition* (any breach lets the other side terminate), a *warranty* (breach gives damages only), or an *innominate* term (it depends on how serious the breach is) | C7b |
| survival | whether the provision outlives the termination of the instrument, as confidentiality clauses often do | C7b |
| sections it applies within | for an instrument divided into sections, which ones the provision governs | C7b |
| precedence | which provision prevails when two conflict | NRS N10 |

```mermaid
flowchart TB
    T["ins:Term<br/>a provision the parties are bound by"]
    R1["a relation"] -- "arisesUnder" --> T
    R2["another relation"] -- "arisesUnder" --> T
    Q["a qualifier, such as a limit"] -- "arisesUnder" --> T
    D["a definition or deeming (C7b)"] -. "arisesUnder" .-> T
    T -. "classification, survival, sections (C7b)" .-> P["properties of the whole provision"]
    T -- "expressedIn (express term)" --> C["a clause version"]
    T -- "impliedBy (implied term)" --> S["a statute, custom or course of dealing"]
```

#### 4.2.3 **`ins:Template`.**

Drafters reuse text, and the word *template* comes from that practice. Two kinds of clause matter here:

- a **standard clause** (also *model clause* or clause *template*) is drafted once, in general words,
  and included in many contracts. For example the form clause "The Borrower shall repay each loan to the
  Lenders", might appear in every facility that a lender signs
- a **bespoke clause** is drafted for one contract only: a clause negotiated for Acme's facility and
  no other, such as "The Borrower shall keep its head office in Leeds"

Both kinds have a meaning in their own words, and those words name roles and variables, rather than the parties of a particular contract: "the Borrower", "the Lenders", "{margin}". LATTICE calls this the clause's **stated meaning**, and each node of it a **template**: meaning fixed by the words, waiting for the parties and values of a particular contract. When a contract includes the clause, its template is instantiated with that contract's parties and values, which gives the contract's **bound meaning** (§5.2).

A standard clause's template is instantiated for every contract that includes the clause. A bespoke clause's template is instantiated for one contract only. It is still a template, so every clause works the same way, whether it is used once or a thousand times: its meaning is stated once and instantiated per contract.

```mermaid
flowchart LR
    subgraph STANDARD["A standard clause: drafted once, used in many contracts"]
        SC["clause 6.1<br/>The Borrower shall repay<br/>each loan to the Lenders"] -- "states" --> ST["template<br/>Borrower must repay Lenders"]
    end
    subgraph BESPOKE["A bespoke clause: drafted for one contract"]
        BC["clause 12.4, Acme only<br/>The Borrower shall keep<br/>its head office in Leeds"] -- "states" --> BT["template<br/>Borrower must keep its head office"]
    end
    ST -- "instantiated for" --> A["Acme's facility<br/>Acme must repay its lenders<br/>Acme must keep its head office"]
    ST -- "instantiated for" --> B["Brightline's facility<br/>Brightline must repay its lenders"]
    ST -- "instantiated for" --> C["Corvid's facility<br/>Corvid must repay its lenders"]
    BT -- "instantiated for" --> A
    style STANDARD fill:#BBDEFB
    style BESPOKE fill:#BBDEFB
```

`ins:Template` is a mixin rather than a class of its own, because terms, relations and qualifiers each have a stated form: a stated term is both an `ins:Term` and an `ins:Template`. A regime is always a template: it is stated once by its clause and never instantiated (§11.1).

#### 4.2.4 **`ins:LegalRelation`.**

In jurisprudence a *legal relation* (or *jural relation*) is a bond the law recognises between two persons concerning some conduct: one owes, the other can claim. The phrase is Hohfeld's (§4.4), and every relation in this layer has his shape: two ends and an act. The name is not to be confused with a "relation" in RDF and OWL terminology, which names a property axiom. Similar but distinct terms include:

- **A Right**, which Hohfeld showed covers four different things (a claim, a liberty, a power, and an
  immunity).
- **A Duty**, which names only one end of an obligation
- **A Rule** or **A Norm**, which suggest a general law rather than a bond between named parties

Whatever its kind, a legal relation in this layer will have the same parts:

- **two ends**: the party bound or exposed, and the party who benefits or acts. An obligation has an
  obligor and obligees, the other kinds, a holder and counterparties
- **an act**: what the relation is about, its `ins:activity`, such as repaying, enrolling or
  terminating
- **a scope**: the cases it applies to, as an Eligibility condition (`ins:scope`)
- **a term**: the provision it arises under, and belongs to (`ins:arisesUnder`)
- **when it exists**: what makes it arise, and what ends it, where its words say so
  (`ins:arisesOn`, `ins:endsOn`, below)
- **when it applies**: the situations it is confined to, where its words say so
  (`ins:appliesInState`, §4.2.13)

A relation is always between parties. "The goods must be delivered" becomes an obligation of the supplier, owed to the buyer, to deliver.

**Choosing a kind:** Contract wording signals the kind of a relation by its verbs, but the test is what the provision does to the parties' positions:

```mermaid
flowchart TB
    Q1{"Does it require a party<br/>to act, or not to act?"}
    Q2{"to act, or<br/>to keep a state holding?"}
    Q3{"Does it free a party<br/>from such a requirement?"}
    Q4{"from a duty not to act,<br/>or from a duty to act<br/>or a power?"}
    Q5{"Can a party, by an act,<br/>change another's position?"}
    OB["ins:Obligation"]
    CO["ins:ContinuingObligation"]
    PR["ins:Prohibition"]
    PE["ins:Permission"]
    EX["ins:Exclusion"]
    PO["ins:Power"]
    Q1 -- "to act" --> Q2
    Q1 -- "not to act" --> PR
    Q1 -- "neither" --> Q3
    Q2 -- "perform an act" --> OB
    Q2 -- "keep a state" --> CO
    Q3 -- "yes" --> Q4
    Q3 -- "no" --> Q5
    Q4 -- "a duty not to act" --> PE
    Q4 -- "a duty to act, or a power" --> EX
    Q5 -- "yes" --> PO
```

The four kinds are disjoint: nothing is both an obligation and a power. A clause that seems to be
both, such as "the Tenant may terminate by giving notice, and shall give notice in writing", is two
relations under one term: a power to terminate, and an obligation about the form of notice.

##### 4.2.4.1 **Arising: when a relation comes into existence.** 

In law a right or a duty *arises* when the facts its source attaches it to come about. Hohfeld called these *operative facts*: the facts that, under a rule or a contract, create, change, or end a legal relation, as against the *evidential facts* that prove them. Giving notice, failing to pay, issuing an invoice, and leverage passing a threshold are all operative facts in some contract. Contract English uses "arise" in two senses, which this layer keeps apart:

```mermaid
flowchart LR
    subgraph SOURCE["Its source: which provision?"]
        T["term 16.1<br/>If the Provider fails to meet<br/>clause 4.1, the Customer<br/>may end this agreement"]
    end
    subgraph MOMENT["Its moment: from when?"]
        F["an operative fact<br/>the Provider fails to meet<br/>clause 4.1 in March"]
    end
    R["the Customer's power<br/>to end the agreement"]
    R -- "arisesUnder" --> T
    R -- "arisesOnBreachOf<br/>the service obligation" --> F
    style SOURCE fill:#BBDEFB
    style MOMENT fill:#bcdee1
```

| Sense | Contract English | Answers | In this layer |
|---|---|---|---|
| its **source** | "any obligation arising under this agreement", "liabilities arising under clause 9" | which provision creates it? | `ins:arisesUnder` exactly one term, fixed by the words |
| its **moment** | "a right to terminate arises if the Supplier fails to deliver", "the duty to pay arises on the issue of each invoice" | from when does it exist? | `ins:arisesOn` a legal trigger (§4.2.15), or its short forms `ins:arisesOnBreachOf` and `ins:arisesOnExerciseOf`: optional |

A relation whose words name no operative fact exists from the moment its instrument takes effect. "The Borrower shall repay each loan on its maturity date" binds the borrower from signing, although nothing is payable until maturity. Arising is not falling due: a duty may arise long before it must be performed, as a debt *accrues* before it is *payable*, and its due range (C7b) says when performance is owed. The duty to repay arises at signing and is due only at maturity:

```mermaid
gantt
    dateFormat YYYY-MM-DD
    axisFormat %Y
    section The facility
    signed, takes effect          :milestone, m1, 2027-01-04, 0d
    the duty to repay exists      :active, a1, 2027-01-04, 2031-12-31
    section Repayment
    not yet payable               :n1, 2027-01-04, 2031-12-01
    due on the maturity date      :crit, d1, 2031-12-01, 2031-12-31
```
 A relation whose words do name an operative fact does not exist until the fact
happens, and then exists for the case it happened in:

- **on a breach**: what follows a failure. "If the Supplier fails to deliver, the Buyer may
  terminate" is a power arising on breach of the duty to deliver, and "the Borrower shall pay default
  interest on any overdue sum" an obligation arising on breach of the duty to pay. A primary duty and
  the relations that arise on its breach form a *breach chain*, which may fan out: one failure can
  give a remedy, a fee and a power to terminate together
- **on an exercise**: what a power creates. "On acceleration, the Borrower shall repay all loans at
  once" is an obligation arising on exercise of the power to accelerate
- **on an act**: "on the issue of each invoice, the Customer shall pay it", where issuing an invoice
  exercises no power and breaches nothing
- **on a condition**: "if leverage exceeds 3.5 to 1, the Borrower shall deliver a remediation plan"

A breach chain from a supply agreement, where one failure to deliver gives rise to three relations:

```mermaid
flowchart LR
    D["deliver<br/>ins:Obligation<br/>the primary duty"]
    C["pay a price reduction<br/>ins:Obligation"]
    E["source elsewhere<br/>at the Supplier's cost<br/>ins:Power"]
    T["terminate<br/>ins:Power"]
    C -- "arisesOnBreachOf" --> D
    E -- "arisesOnBreachOf" --> D
    T -- "arisesOnBreachOf" --> D
```

**Ending.** `ins:endsOn` names the operative facts on which a relation ends: "the Supplier's duty
of exclusivity ends if the Buyer fails to meet its minimum order", "the Lender's power to
accelerate ends once the Event of Default is waived". A relation with none ends with its instrument (C7b adds termination of whole terms and
survival after termination). Ending is final for the case it ends for. A relation that recurs, a
monthly service or an invoice a month, does so as a new occasion, and an ended occasion stays ended.

**What happens at runtime.** For each case a relation applies to, Behaviour keeps an *occasion*:
the relation applied to that case, with its own state. Arising and ending move it through the core
occasion states, which the runtime evaluator derives from records (C12):

```mermaid
stateDiagram-v2
    state "Live" as Live {
        state "Pending" as Pending
        state "Arisen" as Arisen
        [*] --> Pending
        Pending --> Arisen : an arising trigger fires, or at once if there is none
    }
    state "Performed" as Performed
    state "Breached" as Breached
    state "Ended" as Ended
    [*] --> Live
    Live --> Ended : an ending trigger fires
    Arisen --> Performed : performance
    Arisen --> Breached : no performance when due, or a forbidden act done
```

*Pending* means the relation applies to the case and has not yet arisen, *Arisen* that it exists and
is live. A breach of one occasion is itself an operative fact: an `ins:OnBreach` of it may make
another relation arise, which is how a breach chain runs. Each relation has an occasion for each
case, so a monthly duty has twelve occasions a year, each moving on its own:

```mermaid
flowchart TB
    R["provide the service<br/>ins:Obligation, one relation"]
    R --> J["January's occasion<br/>Performed"]
    R --> F["February's occasion<br/>Performed"]
    R --> M["March's occasion<br/>Breached"]
    R --> A["April's occasion<br/>Arisen, not yet due"]
    M -- "an OnBreach of it" --> P["the Customer's power to end<br/>arises for March's breach"]
```

Arising and ending say *whether* a relation exists. Whether an existing relation applies *now*, in
the situation the instrument is in, is a second question, answered by regimes (§4.2.13).

#### 4.2.5 **`ins:Obligation`.**

From Roman law's *obligatio*, which Justinian's Institutes define as a bond of law (*vinculum iuris*) binding a person to perform something: the bond between the *obligor*, who owes, and the *obligee*, who is owed. It is what "shall" and "must" create in a contract. Once again we can contrast this with *Duty* (one end of the bond), and *Covenant* (a promise in a deed, and in finance a particular kind of undertaking).

An obligation is one bond with two ends. The *duty* is the obligor's end, and the *claim* is the
obligee's: the right to have the act performed, and to a remedy if it is not. They are not two
facts to keep in step, but one fact seen from two sides (§4.4).

**What an obligation states:**

- **who owes**: exactly one obligor. Where several parties owe together, the obligor is a
  participation group, and the group's composition rule says how they owe: each for its own share
  (several), or each for the whole (joint and several) (§4.2, `ins:RelationParty`)
- **to whom**: one or more obligees, who need not be parties to the instrument. A beneficiary named
  in a contract is an obligee who signed nothing (§6.1)
- **what**: the act owed, `ins:activity`: repay, deliver, report, repair
- **in which cases**: its scope, where it applies only to some
- **by when**: its due range, such as "within 30 days of each invoice" (C7b)
- **what counts as performance**: `ins:fulfilledWhen`, where performance is more than the act being
  done. Without it, performance is an act of the activity, for the case, by the obligor or someone
  the obligor delegated to (Party's `pty:Delegation`)

**Examples across domains:** the borrower shall repay each loan, the tenant shall pay rent
quarterly, the investigator shall report each serious adverse event within 24 hours, the
manufacturer shall repair a product that fails, the employer shall pay salary monthly.

An obligation of this kind is an *achievement* obligation in deontic logic: it is met by doing
something. Its counterpart, an obligation met by keeping something true, is the continuing
obligation below.

#### 4.2.6 **`ins:ContinuingObligation`.**

English contract law speaks of a *continuing* obligation: one that must be kept for a period rather than performed once. "The Borrower shall ensure that leverage does not exceed 3.0 to 1", holds on every day the facility is in force.

Deontic logic, the logic of obligation and permission, draws the same line more sharply. It distinguishes two ways an obligation can be met.

- **An achievement obligation** requires that something be *brought about* at least once, usually by a deadline: "the Borrower shall repay the loan by 31 December". This is fulfilled the moment the act is done and asks nothing more thereafter. It is breached only when the deadline passes and the act has not happened.
- **A maintenance obligation** requires that something *hold throughout* a period: "the Borrower shall ensure that leverage does not exceed 3.0 to 1". It is never discharged by a single act. It is fulfilled only if the state holds at every moment of the period, and it is breached at any moment it does not. This is a common type of obligation in insurance contracts that define subjectivities, which are requirements set by an insurer that a policyholder must meet in order to activate or maintain coverage. 

The difference matters for a computable model, because the two are checked in opposite ways:

- **Breach of a maintenance obligation is a positive fact.** It is found by looking at the state at a point in time. If leverage was 3.4 on 30 June, the covenant was breached on 30 June. That is evidence a rule can read directly.
- **Breach of an achievement obligation is an absence.** It is found only by establishing that the act did *not* happen before the deadline. That needs a record of what happened and a closed view of it, which an open-world reasoner cannot assume. This is why later slices handle the two differently when deriving breach (C12, C13).
- **Their content differs.** An achievement obligation names an act and a time to do it by: `ins:activity`, and a due range from C7b. A maintenance obligation names a state to keep: `ins:maintains`, an Eligibility condition such as "leverage ≤ 3.0", tested against the case at each point.

The literature refines achievement obligations further:

- **Preemptive or not.** Can the act be done early, before the obligation arises, and still count? Paying an invoice before it is issued is the usual example.
- **Perdurant or not.** Does the obligation survive its own breach? A late payment is still owed after the due date has passed.

These distinctions belong to arising and due (C7b), and C6 does not model them yet.

So LATTICE maps the two kinds onto two classes:

- `ins:Obligation` is the achievement case: an act, owed, and later due.
- `ins:ContinuingObligation` is the maintenance case, with the state it keeps in `ins:maintains`.

Other continuing obligations across domains: the tenant shall keep the premises in good repair,
the licensee shall keep the source code confidential while it holds a copy, the supplier shall
maintain the certifications listed in the schedule, the employer shall maintain a safe place of
work.

#### 4.2.7 **`ins:Prohibition`.**

What "shall not" and "must not" create: an obligation not to do something. In deontic logic F p, "p is forbidden", is defined as O ¬p, "not-p is obligatory", which is why `ins:Prohibition` is a kind of `ins:Obligation`. A market's *negative covenant* and *negative pledge* are examples of prohibitions.

In deontic logic a prohibition is a maintenance obligation, in negative form. "The Borrower shall not create any security" creates an obligation to keep *not creating security* true throughout the period the instrument remains in force. Unlike a covenant on a state, though, its breach is an act. Creating security on March 3rd breaches it on March 3rd, again a positive fact.

That is why `ins:Prohibition` is not an `ins:ContinuingObligation`, and the T-Box declares the two
disjoint. Both hold throughout a period, but they say different things:

| | `ins:ContinuingObligation` | `ins:Prohibition` |
|---|---|---|
| what it names | a **state** to keep: leverage at most 3.0 | an **act** not to do: create security |
| its content | `ins:maintains`, a condition | `ins:activity`, a concept, and usually a scope |
| what breaches it | the state failing to hold at a moment | the act being done |
| how it is excepted | an exclusion for some period or case | a permission for some cases |

**Scope makes a prohibition precise.** Few prohibitions forbid an act everywhere. "The Employee
shall not work for a competitor within 50 miles for six months after leaving" forbids working for a
competitor only within that scope: the act is `Work for competitor`, and the place and period are
its scope. Keeping the act plain and the circumstances in the scope lets a permission except part
of the same act (below).

**Examples across domains:** a negative pledge (shall not create security), a non-compete (shall not
work for a competitor), a confidentiality clause (shall not disclose confidential information), a
restriction on assignment (shall not assign this licence), a trial's eligibility rule (shall not
enrol a participant who fails the criteria).

#### 4.2.8 **`ins:Permission`.**

A *permission* in the strong sense of deontic logic: a positive licence to do what a prohibition would otherwise forbid. Contracts write it as an exception: "Clause 8.1 does not apply to any lien arising by operation of law", "Permitted Security", "the Sponsor may waive". A permission always excepts a prohibition. Weak permission, the mere absence of a prohibition, needs no node and has none. *Liberty* and *Privilege*, Hohfeld's words, are not suitable here, since "privilege" has other legal senses (legal professional privilege).

The name is shared with the Eligibility decision value `elg:Permitted`, which is a different thing entirely, with both carrying a comment saying as much.

**Strong and weak permission.** deontic logic distinguishes two senses of "permitted":

- **weak permission**: an act is permitted because nothing forbids it. Nothing in a lease forbids
  the tenant from painting the walls, so painting them is permitted in the weak sense
- **strong permission**: an act is permitted because a provision says so, usually as an exception
  to something that would otherwise forbid it. "The Tenant shall not alter the premises, except
  that the Tenant may decorate the interior" gives a strong permission to decorate

Only strong permission is a node in this layer. Weak permission is the absence of a prohibition,
and an absence is not a fact an open-world model can record: there may be a prohibition the graph
does not hold. A strong permission is written in the wording, so it is a fact like any other.

**How a permission works.** A permission always excepts exactly one prohibition (`ins:excepts`),
and takes effect within its own scope. The act is forbidden where the prohibition's scope holds,
unless the permission's scope holds too:

```mermaid
flowchart LR
    PR["prohibition<br/>shall not create security<br/>scope: any asset"]
    PE["permission<br/>may create security<br/>scope: a lien arising by law"]
    RES["effect: security is forbidden,<br/>except a lien arising by law"]
    PE -- "excepts" --> PR
    PR --> RES
    PE --> RES
```

Law I8 ties a permission to the prohibition it excepts:

- its **holder** is the prohibition's **obligor**: only the party who is forbidden can be freed
- its **activity** is the prohibition's activity: it permits the same act, in fewer cases

A permission that broke either rule would free someone who was never bound, or permit an act that
was never forbidden. The shapes report both.

**Examples across domains:** permitted security under a negative pledge, a sponsor's written waiver
of an eligibility criterion, consent to assign a licence, a landlord's permission to sublet part of
the premises.

#### 4.2.9 **`ins:Exclusion`.**

An *exclusion clause* or *exemption clause*: "the Manufacturer shall not be liable for", "Clause 2.1 does not apply to damage caused by misuse", "is not obliged to". It frees its holder from an obligation within its scope, or protects its holder from a power: "the Licensor may not end the licence once the perpetual fee is paid", which is an *immunity*. Distinct from *Exemption* (also a tax and regulatory word), *Immunity* (only the second kind), *Waiver* (an act of giving up a right, not a term).

An exclusion has two forms, according to what it excepts:

```mermaid
---
config:
  layout: elk
---
flowchart TB
    subgraph OBL["Excepting an obligation: a liberty not to act"]
        RE["obligation<br/>Manufacturer shall repair"]
        EX1["exclusion<br/>need not repair<br/>scope: misuse"]
        EX1 -- "excepts" --> RE
        H1["holder: the Manufacturer,<br/>the obligation's obligor"] --- EX1
    end
    subgraph POW["Excepting a power: an immunity"]
        PO["power<br/>Licensor may terminate<br/>for convenience"]
        EX2["exclusion<br/>cannot be terminated<br/>scope: perpetual fee paid"]
        EX2 -- "excepts" --> PO
        H2["holder: the Licensee,<br/>the power's counterparty"] --- EX2
    end
```

- **Excepting an obligation**, the exclusion is a *liberty not to act*: within its scope the obligor
  need not perform. Its holder is the obligation's obligor, the party who would otherwise be bound
  (law I8). A product warranty that does not cover misuse, a supplier who need not deliver on public
  holidays, an employee who need not work on rest days.
- **Excepting a power**, the exclusion is an *immunity*: within its scope the power cannot be
  exercised against its holder. Its holder is the power's counterparty, the party who would
  otherwise be exposed (law I8). A perpetual licence that cannot be ended for convenience, a lease
  that the landlord cannot end early while the rent is paid.

**Why Exclusion and Permission are separate classes.** Both are Hohfeldian privileges, and both are
exceptions. They differ in the direction of the duty they free from: a permission frees from a duty
*not* to act, so its holder *may* act. An exclusion frees from a duty *to* act, so its holder *need
not* act, or from exposure to a power, so its holder *cannot be made* subject to it. Contract
English uses different words for them ("may", "need not", "shall not be liable"), and a reader of
the data should see the same distinction.

**Carve-backs.** Exclusions are often narrowed by a carve-back: "Clause 2.1 does not apply to damage
caused by misuse, unless the failure was caused by a manufacturing defect". The carve-back belongs
in the exclusion's scope, as a negated member of the scope's condition (§9, §16.3), not as a second
relation.

#### 4.2.10 **`ins:Power`.**

Hohfeld's *power*: the ability, by one's own act, to change someone else's legal position. Contracts write it as "may" with an effect: "the Lenders may by notice declare all loans due", "may terminate", "may accept". "May" is a permission if it only frees the holder, and a power if it changes someone else's relations. Distinct from *Right* ("right to terminate" is a power, but "right" covers four things), *Option* (one kind of power), *Authority* (an agent's power, which an applied ontology may specialise from `ins:Power`).

**Power and permission, side by side.** "The Tenant may decorate the interior" and "the Tenant may
terminate the lease on six months' notice" both say "may", but they do different things. After the
tenant decorates, nobody's rights have changed: the act was simply allowed. After the tenant gives
notice, the lease ends in six months, and with it the tenant's duty to pay rent and the landlord's
duty to give possession. The first is a permission. The second is a power, because exercising it
has a legal effect on someone else.

**What exercising a power does.** The act that exercises a power is its `ins:activity`. Its effect is
on the counterparty's legal position, in one of three ways:

```mermaid
flowchart LR
    P["power<br/>the holder's act"]
    P -- "ends relations" --> E["terminate a lease,<br/>end a site's participation"]
    P -- "creates relations" --> C["accept an offer,<br/>exercise an option,<br/>make a call-off order"]
    P -- "changes relations" --> X["accelerate a loan,<br/>extend a deadline,<br/>appoint a replacement agent"]
```

Legal triggers say what a power's exercise does: an `ins:OnExercise` moves a regime, such as
a licence into its notice period, and a relation may arise or end on the exercise (§10). An
instrument made by exercising a power, such as an order under a framework agreement, records the
power it was made under (C9).

**When a power can be exercised.** A power is often limited: to its scope, to a regime's state
("only while an event of default is continuing", `ins:appliesInState`, §11.3), or by a consent rule where a group holds it ("by lenders
holding two thirds of the commitments", C9). The counterparty's end of a power is Hohfeld's
*liability*, a word this layer never uses (§4.6). An exclusion of the power gives the counterparty
an *immunity* (above).

#### 4.2.11 **`ins:Qualifier`.**

A limit, level, retention, or any other thing that qualifies a term or a relation: it says how much, not what.

A qualifier never creates a relation of its own. It bounds one that already exists:

- a cap: "the Licensor's aggregate liability under this agreement shall not exceed the fees paid in
  the previous twelve months" qualifies the licensor's obligations to pay damages
- a minimum: "the Buyer shall order at least 1,000 units in each quarter" qualifies the obligation
  to order
- a threshold: a covenant that bites only above a certain level of borrowing
- a level of performance: "with an availability of at least 99.9% in each month"

A qualifier arises under exactly one term, like a relation, and qualifies exactly one term or
relation (`ins:qualifies`). It is its own node because amounts are rarely just numbers: they have a
unit and currency, a period they reset over, and a basis, such as per claim or in the aggregate.
That structure is defined with contract amounts (C8), and C6 declares only the class and its links.

#### 4.2.12 **`ins:RelationParty`.**

A *party* is an entity (e.g., person or organisation) bound by or benefiting from an instrument. This union of types, names what may stand at the end of a relation: a role occupancy (a party filling a role for a period, Party layer), a participation group (several parties acting together), or, in stated meaning only, a role. "Party" alone would read as a person, and sit beside the property `ins:party` (C6-Q4).

The three members come from the Party layer, and each answers a different question:

| Member | Answers | Example |
|---|---|---|
| `pty:Role` | which capacity? | the Borrower, the Licensee, the Sponsor |
| `pty:RoleOccupancy` | who fills it, from when? | Acme Holdings plc as Borrower, from 1 January |
| `pty:ParticipationGroup` | which several parties, acting how? | the lenders, each for its own share |

A **role** is a capacity, independent of who fills it. Stated meaning names roles, because a
clause's words do: "the Borrower" means whoever is the borrower under each contract the clause is
used in (law I13). A **role occupancy** is one party filling one role, for a period. Bound meaning
names occupancies, because a contract's parties are particular entities. An occupancy may exist
before anyone fills it, a *contingent* occupancy, for a party that depends on the case (§8).

A **participation group** is several occupancies standing at one end of a relation together, with a
composition rule that says how they stand there:

- **several**: each is owed, or owes, only its own share. Two lenders lending 60% and 40% are each
  owed repayment of their own part only
- **joint and several**: each is liable for the whole, and the creditor may pursue any one of them.
  Two tenants who sign one lease are often jointly and severally liable for the whole rent

**Party to the instrument, and party to a relation.** These differ. `ins:party` lists who is party to
the instrument: who signed it. The ends of a relation name whoever the relation binds or benefits,
who may include persons who signed nothing: a beneficiary for whose benefit a promise was made, or
a regulator given a power of inspection. That is why `ins:party` is authored, and never derived from
the relations' parties (§6.1).

```mermaid
---
config:
  layout: elk
---
flowchart TB
    IN["ins:Instrument"]
    A["Acme, as Borrower<br/>a party"]
    B["the lenders<br/>a group of parties"]
    T["a trustee<br/>not a party"]
    O["an obligation<br/>owed by Acme"]
    IN -- "party" --> A
    IN -- "party" --> B
    O -- "obligor" --> A
    O -- "obligee" --> B
    O -- "obligee" --> T
```

#### 4.2.13 **`ins:Regime`.**

In legal terminology, a regime is a body of rules that applies to a specific situation, or for a specific period of time, for example an insolvency regime, or "the regime that applies during the notice period", and so on. It is synonymous with *dispensation*, in its older sense of an order of things that holds for a period. In this substrate, a *regime* is modelled as a set of states an instrument can be in, along with rules that can be used to move it between states. Some examples include a notice regime (in force, notice period, terminated), suspension regime (in force, suspended), or event-of-default regime (performing, cure period, defaulted).

Arising and ending (§4.2.4) are about events that happen once: a relation comes into existence, later it ends, and it does not come back. Contracts also describe *situations* that an instrument enters and leaves, sometimes more than once, which change what the contract applies while they last. For example:

- while notice of termination is running
- while deliveries are suspended
- while an event of default is continuing
- while a force majeure event prevents performance

A regime models one such family of situations. Its states are the situations (notice period, in force, terminated), and its transitions are the operative facts that move the instrument from one to the next (giving notice, the notice period running out).

##### 4.2.13.1 **Where an instrument's regimes come from.**

A regime arises under the term of the clause that describes the situation (`ins:arisesUnder`), as a relation does. A licence's termination clause states its notice regime, and a supply agreement's suspension clause states its suspension regime. An instrument has a regime only if its wording includes the clause that states it: a licence with no termination on notice has no notice regime, and nothing in it can depend on a notice period. So an instrument has as many regimes as it has clauses describing situations: often none, often several, each independent of the others. A clause may state a regime and relations together (the licence's clause 11.1 states the power to end on notice and the notice regime its exercise starts), or a regime alone (a force majeure clause).

```mermaid
flowchart LR
    subgraph WORDING["The licence's assembled wording"]
        C41["clause 4.1<br/>sub-licensing"]
        C111["clause 11.1<br/>termination on notice"]
        C113["clause 11.3<br/>no sub-licensing during notice"]
        C141["clause 14.1<br/>force majeure"]
    end
    P41["power to grant sub-licences"]
    P111["power to end on notice"]
    NR["notice regime"]
    X113["sub-licensing excluded<br/>gated by the notice period"]
    FR["force majeure regime"]
    C41 -- "states" --> P41
    C111 -- "states" --> P111
    C111 -- "states" --> NR
    C113 -- "states" --> X113
    C141 -- "states" --> FR
    X113 -. "appliesInState" .-> NR
    style WORDING fill:#BBDEFB
```

A licence on a form without clause 14.1 would have one regime, not two.

**An instrument is always in exactly one state of each of its regimes.** From the moment the instrument takes effect it is in each regime's initial state (`bhv:initialState`). After that it moves only along the regime's transitions, each on a legal trigger, and at every moment it is in exactly one of the regime's states.

Each regime runs on its own: being in a notice period says nothing about force majeure. The instrument's position is not part of what was agreed. It is a runtime record, a Behaviour *state occupancy* for the instrument's persistent identity, which begins when the instrument enters the state and ends when a transition leaves it (§11.1). One licence, over a year (dates illustrative):

```mermaid
gantt
    dateFormat YYYY-MM-DD
    axisFormat %b
    section Notice regime
    in force                :a1, 2027-01-01, 2027-06-01
    notice period           :active, a2, 2027-06-01, 2027-08-30
    terminated              :done, a3, 2027-08-30, 2027-12-31
    section Force majeure regime
    unaffected              :b1, 2027-01-01, 2027-07-05
    affected                :crit, b2, 2027-07-05, 2027-07-26
    unaffected              :b3, 2027-07-26, 2027-12-31
```

##### 4.2.13.2 **Gating: relations that apply only in a situation.**

Most relations apply whenever they exist. Some apply only under specific circumstances, and their clauses say so, for example: "during the notice period, the Licensee may not grant sub-licences", or "while an Event of Default is continuing, the Lender may declare the Loan due", or "the Supplier is relieved of clause 3.1 while a force majeure event prevents it from performing". 

Such a relation names the states it applies in (`ins:appliesInState`). Those states are its *gate*. While the instrument is in one of them, the gate is open and the relation applies. Otherwise the gate is closed, and the relation, though it still exists, does not apply. The licence again, with the exclusion of sub-licensing and the power it excepts beneath its notice regime:

```mermaid
gantt
    dateFormat YYYY-MM-DD
    axisFormat %b
    section Notice regime
    in force                       :a1, 2027-01-01, 2027-06-01
    notice period                  :active, a2, 2027-06-01, 2027-08-30
    terminated                     :done, a3, 2027-08-30, 2027-12-31
    section Sub-licensing excluded
    exists, gate closed            :x1, 2027-01-01, 2027-06-01
    exists, gate open, applies     :crit, x2, 2027-06-01, 2027-08-30
    section Power to sub-license
    exists, exercisable            :p1, 2027-01-01, 2027-06-01
    exists, excluded               :crit, p2, 2027-06-01, 2027-08-30
```

The exclusion exists all along and applies only while its gate is open. While it applies, the power it excepts cannot be exercised. When the licence terminates, both end with it.

**A relation's regimes** are those its named states belong to. They are its instrument's, stated by
the relation's own clause or another. Most relations name no state, so have no gate and no regimes. Like its scope, a relation's gate is fixed by its clause's words.

Three questions about one relation at one moment have separate answers, from separate parts of the model. Taking the licence's exclusion of the power to grant sub-licences (§16.5):

| Question | Answered by | For the exclusion |
|---|---|---|
| Does it exist? | arising and ending (`ins:arisesOn`, `ins:endsOn`, §4.2.4) | from signing, since its clause names no operative fact, until the licence ends |
| Does it apply now? | its gate (`ins:appliesInState`), read against the instrument's regimes | only while the licence is in its notice period |
| Does it apply to this case? | its scope (`ins:scope`) | to every sub-licence, since it has no scope |

For an obligation, a fourth question, whether it is due, performed or breached for a case, is answered by its occasion's state (§4.2.4, C7b, C12). The questions are asked in order, and a relation takes effect for a case only when every answer is yes:

```mermaid
flowchart LR
    Q1{"Does it exist?<br/>arisen, not ended"}
    Q2{"Does it apply now?<br/>its gate is open"}
    Q3{"Does it apply<br/>to this case?<br/>its scope"}
    Y["it takes effect<br/>for the case"]
    N["it has no effect<br/>for the case"]
    Q1 -- "yes" --> Q2
    Q2 -- "yes" --> Q3
    Q3 -- "yes" --> Y
    Q1 -- "no" --> N
    Q2 -- "no" --> N
    Q3 -- "no" --> N
```

**Why a gate, and not arising and ending.** "During the notice period, the Licensee may not grant sub-licences" could also be read as an exclusion that arises when notice is given and ends when the licence terminates. For a regime that only moves forward, the two readings agree. They part in three ways:

- **Situations recur.** A supply agreement can be suspended, reinstated and suspended again. Ending is final, so a relation that ended on suspension would not return on reinstatement. A gate opens and closes as often as the instrument enters and leaves the state. This is why a suspension is a state and not an ending: it can be reinstated.

  ```mermaid
  gantt
      dateFormat YYYY-MM-DD
      axisFormat %b
      section Suspension regime
      in force                      :s1, 2027-01-01, 2027-03-01
      suspended                     :crit, s2, 2027-03-01, 2027-04-01
      in force                      :s3, 2027-04-01, 2027-08-01
      suspended                     :crit, s4, 2027-08-01, 2027-09-01
      in force                      :s5, 2027-09-01, 2027-12-31
      section Duty to deliver, gated
      applies                       :active, g1, 2027-01-01, 2027-03-01
      applies                       :active, g2, 2027-04-01, 2027-08-01
      applies                       :active, g3, 2027-09-01, 2027-12-31
      section Duty to deliver, ended on suspension
      exists                        :active, e1, 2027-01-01, 2027-03-01
      ended for good                :done, e2, 2027-03-01, 2027-12-31
  ```
- **Situations are shared.** Several relations often depend on one situation: during a notice period
  a licensee may lose its power to sub-license and gain a duty to help migrate its users. With a gate,
  the situation is stated once, in its regime, and each relation names the state. With arising and
  ending, each relation would restate the facts that start and stop the situation, and nothing
  would keep them in step.

  ```mermaid
  flowchart LR
      subgraph GATE["With a gate: the situation stated once"]
          NP["notice period"]
          X1["sub-licensing excluded"] -- "appliesInState" --> NP
          X2["help migrate users"] -- "appliesInState" --> NP
      end
      subgraph ARISE["With arising and ending: restated per relation"]
          Y1["sub-licensing excluded"] -- "arisesOn" --> N1["notice given"]
          Y1 -- "endsOn" --> E1["licence ends"]
          Y2["help migrate users"] -- "arisesOn" --> N2["notice given"]
          Y2 -- "endsOn" --> E2["licence ends"]
      end
      style GATE fill:#BBDEFB
  ```
- **Situations are not cases.** A relation's scope says which cases it covers, and design-time
  comparisons read it: does version 2 of the licence widen the licensee's powers? A gate says when
  the relation applies, and is read only at runtime. Keeping the two apart is what stops serving
  notice from looking like an amendment (DP6, §11.5).

**Several regimes on one relation.** A relation may name states of more than one regime. The states
of one regime are alternatives: the relation applies in any of them. The regimes combine: the
relation applies only when every one of them is in a named state. The supply agreement's duty to
deliver names *in force* from its suspension regime and *unaffected* from its force majeure regime,
so it applies only when deliveries are not suspended and no force majeure continues (§11.3).

**Regimes for each occasion.** Some situations belong to one occasion of a relation, not to the
instrument: one month's service failure is disputed while the others are not. A *per-occasion*
regime (`bhv:perOccasionOf` a relation) runs once for each occasion of that relation, from when the
occasion exists. A relation gated by its state must say which occasion it is about, and it does so
through arising: an exclusion that arises on breach of the service obligation reads the dispute
regime of the occasion that was breached (§11.4). This is where arising and regimes meet most
directly:

```mermaid
flowchart TB
    S["provide the service<br/>one relation"]
    S --> F["February's occasion<br/>Performed"]
    S --> M["March's occasion<br/>Breached"]
    S --> A["April's occasion<br/>Breached"]
    M --> MD["March's dispute regime<br/>disputed"]
    A --> AD["April's dispute regime<br/>undisputed"]
    XM["termination excluded<br/>for March's breach: applies"] -- "reads" --> MD
    XA["termination excluded<br/>for April's breach: does not apply"] -- "reads" --> AD
```

The customer may end the agreement for April's failure, which the provider has not disputed, and
not for March's, which it has.

**One operative fact, several effects.** The legal triggers that make relations arise and end are
the same triggers that move regimes (§4.2.15). One fact can therefore do several things at once:
when the licensor gives notice under clause 11.1, that exercise of its power moves the licence's
notice regime into the notice period, which opens the gate on the exclusion of sub-licensing, and
starts the 90 days after which the licence terminates.

```mermaid
flowchart LR
    F["an operative fact<br/>the licensor gives notice"]
    T["a legal trigger<br/>ins:OnExercise of the power<br/>to end on notice"]
    R["the notice regime<br/>moves to the notice period"]
    G["the exclusion's gate opens<br/>sub-licensing excluded"]
    X["the 90 days start<br/>then: terminated"]
    A["a relation arises<br/>whose ins:arisesOn names the trigger"]
    F --> T
    T --> R
    R --> G
    R --> X
    T -. "where a relation's words say so" .-> A
```

| Kind | Examples | Shape |
|---|---|---|
| **period** | notice, cure, probation, garden leave, run-off | entered on a trigger, left at a duration from entry or on an end trigger, whichever comes first |
| **switching** | suspension and reinstatement, force majeure | states switched back and forth by triggers |
| **threshold** | a usage cap, an aggregate limit exhausted | states defined by ranges of a measured value, entered as the value crosses into each |

**A regime is stated once.** Unlike a relation, a regime has no bound form. Its clause states its states and transitions once, every instrument that includes the clause shares them, and each instrument's progress through them is held at runtime against the instrument's persistent identity
(§11.1). The regimes an instrument has are therefore the stated regimes of the clauses its wording
includes, and its own positions in them are its occupancies.

#### 4.2.14 **`ins:RegimeTransition`.**

A move between two states of a regime, on a legal trigger: "on the expiry of the notice period, this licence terminates", "if the Borrower remedies the breach within the cure period, the Event of Default does not occur". It is a `bhv:TransitionDefinition` whose engine settings are fixed: a regime takes one transition at a time (`bhv:SingleMatch`), and takes it at once (`bhv:ImmediateActivation`). A contract's words never say that two outcomes compete, or that a change waits for someone to run it. Distinct from *event*, what happened, which the runtime records,
and *amendment*, a change of the words (C9).

#### 4.2.15 **The legal triggers: `ins:OnExercise`, `ins:OnBreach`, `ins:OnAct`, `ins:OnCondition`, `ins:OnExpiry`.**

A *trigger* is what makes something happen. Contracts write it as "on", "upon", "if", "when", "following". The five legal triggers are the five things a contract's words make a consequence turn on:

| Trigger | Contract English | Fires on | Behaviour's kind |
|---|---|---|---|
| `ins:OnExercise` | "on the giving of notice under clause 11.1", "upon acceptance" | the exercise of a power (`ins:ofPower`) | an external stimulus: a party acts |
| `ins:OnBreach` | "if the Borrower fails to pay", "following any breach of clause 4" | the breach of an obligation (`ins:ofObligation`) | derived: the runtime works it out from the obligation's occasions |
| `ins:OnAct` | "if the Provider disputes the report", "on delivery" | an act that exercises no power (`ins:activity`, optionally `ins:by`) | an external stimulus |
| `ins:OnCondition` | "if leverage exceeds 3.0 to 1", "while a force majeure event prevents performance" | a condition coming to hold (`ins:condition`) | derived |
| `ins:OnExpiry` | "on the expiry of 90 days", "within 30 Business Days" | the end of a period counted from entering a state (`ins:after`) | scheduled: known in advance |

The names follow drafting's "on" with the event: "on termination", "on expiry". *Exercise* and *breach* are the law's own words for a power used and an obligation not performed. *Expiry* is its word for a period coming to an end: "the expiry of the notice period". *Act* is the plain word, as in deontic logic, for what a party does. Distinct from *event* (what happened, not what an instrument waits for), *condition* in its other senses (§4.6: here only the trigger's Eligibility condition), and *deadline*, a due range (C7b).

Four of the triggers also say when a relation arises or ends (`ins:arisesOn`, `ins:endsOn`, §4.2.4). One vocabulary governs both an instrument's relations and its regimes: what moves a licence into its notice period is the same kind of thing as what gives a customer a power to terminate. `ins:OnExpiry` moves only regimes, since it counts from entering a state, and a relation has no state to enter. A relation's own periods, such as a duty due within 30 days of arising, are due ranges (C7b).

```mermaid
flowchart LR
    T["a legal trigger"]
    T -- "moves" --> R["a regime<br/>between its states"]
    T -- "makes arise, or end<br/>(not an expiry)" --> L["a legal relation"]
    R -- "its states gate" --> L
```

### 4.3 Properties

The properties fall into five groups: those that tie meaning to text and to its owner, those that name a relation's parties, those that state a relation's content, a party's details for one instrument, and those of triggers, regimes and gating.

#### Text and ownership: `ins:expressedIn`, `ins:alsoExpressedIn`, `ins:boundIn`, `ins:boundFrom`, `ins:impliedBy`, `ins:arisesUnder`

These six properties are how every computable node reaches the words that create it (§5.1).

- **`ins:expressedIn`** comes from the law's *express* terms, terms the words state: "the terms
  expressed in this agreement". A stated term is expressed in exactly one clause version, which owns
  it. An instrument version is expressed in exactly one assembled wording, the text its parties
  signed. One property serves both, because both say "these are the words that state this".
- **`ins:alsoExpressedIn`** carries the same stated term into a second element: the French text of a
  bilingual agreement, or a consolidated copy that restates amended clauses. The term still has one
  owner, its `ins:expressedIn`. A deployment that never does this can load the optional
  `single-expression.ttl` to refuse it (ADR-A96).
- **`ins:boundIn`** and **`ins:boundFrom`** borrow computing's *bound variable*. A template's roles and
  variables are free, waiting for values. Instantiating it for one contract binds them to that
  contract's parties and values. The result is bound meaning: each bound term is part of exactly one
  instrument version (`ins:boundIn`), and each bound node points at the stated node it was
  instantiated from (`ins:boundFrom`), so its derivation is always traceable. `ins:boundFrom` is a
  sub-property of PROV's `prov:wasDerivedFrom`, the W3C provenance vocabulary's word for exactly
  this. The phrase also echoes the law's "the parties are bound by its terms".
- **`ins:impliedBy`** takes the place of `ins:boundFrom` for an implied term (§4.2, `ins:Term`): a
  term no clause states has no template to be instantiated from, so it names the statute, custom or
  course of dealing that implies it.
- **`ins:arisesUnder`** is contract English: "any obligation arising under this agreement", "any
  dispute arising under this licence". A relation, definition, deeming or qualifier arises under the
  term that creates it, and belongs to it. Only the term carries `ins:expressedIn` or `ins:boundIn`,
  so a relation reaches its clause or its instrument through its term, never directly.

```mermaid
---
config:
  layout: elk
---
flowchart LR
    BR["bound relation"] -- "arisesUnder" --> BT["bound term"]
    BT -- "boundIn" --> IN["instrument version"]
    BT -- "boundFrom" --> ST["stated term"]
    BR -- "boundFrom" --> SR["stated relation"]
    SR -- "arisesUnder" --> ST
    ST -- "expressedIn" --> CL["clause version"]
    ST -. "alsoExpressedIn" .-> TR["the clause in French"]
    IT["implied term"] -- "boundIn" --> IN
    IT -- "impliedBy" --> SRC["a statute"]
```

#### A relation's parties: `ins:party`, `ins:obligor`, `ins:obligee`, `ins:holder`, `ins:counterparty`

- **`ins:party`** is "the parties to this agreement": who is party to the instrument, as authored.
  It is not the same as who stands at the ends of the relations (§4.2, `ins:RelationParty`).
- **`ins:obligor`** and **`ins:obligee`** are civil law's names for the two ends of an *obligatio*:
  the one who owes and the one owed. They are used for every obligation, continuing obligation and
  prohibition.
- **`ins:holder`** and **`ins:counterparty`** name the two ends of the other three kinds. *Holder* is
  how the law speaks of a power or a right: "the holder of the power", "the holder of the option".
  *Counterparty* is finance's word for the other side of an arrangement. Hohfeld named the far end
  of each kind (no-right, liability, disability), but those words are never used: "liability" in
  particular has settled senses of its own, such as a liability to pay.

| Kind | The bound or freed end | The other end |
|---|---|---|
| `ins:Obligation`, `ins:ContinuingObligation`, `ins:Prohibition` | `ins:obligor` (exactly one), who owes | `ins:obligee` (at least one), who is owed |
| `ins:Permission` | `ins:holder` (exactly one), who may act | `ins:counterparty`, who cannot object |
| `ins:Exclusion` | `ins:holder` (exactly one), who need not act or is immune | `ins:counterparty`, who cannot demand or cannot exercise the power |
| `ins:Power` | `ins:holder` (exactly one), who can act | `ins:counterparty`, whose position the act changes |

#### A relation's content: `ins:activity`, `ins:scope`, `ins:maintains`, `ins:fulfilledWhen`, `ins:excepts`, `ins:qualifies`

- **`ins:activity`** is deontic logic's *action*: the act a relation is about. It names the act
  plainly, without its circumstances: `Repay`, `Enrol`, `Terminate`. An activity is a concept from a
  scheme bound to `ins-voc:ActivityContract`, so a deployment can use its own list of acts (§13). The same property names the act an `ins:OnAct`
  trigger waits for (§10), so a trigger on an act of repaying names the same concept as the duty to
  repay.
- **`ins:scope`** is "the scope of the exclusion", "within the scope of this clause": the cases a
  relation applies to. It is an Eligibility condition, so the same machinery that decides whether
  a case is admissible decides whether a relation applies to it. Keeping circumstances in the scope
  rather than the activity is what lets a permission except part of a prohibition: both have the
  activity `Enrol`, and their scopes say where enrolment is forbidden and where it is allowed.
- **`ins:maintains`** is deontic logic's *maintenance* obligation (§4.2,
  `ins:ContinuingObligation`): the state a continuing obligation keeps holding, as a condition.
- **`ins:fulfilledWhen`** is the *fulfilment* or *performance* of an obligation: the test that says
  it was performed. It is needed only when performance is more than the act being done, such as a
  report that must be accepted, not merely sent.
- **`ins:excepts`** comes from "except", "save that", "does not apply to": an *exception* names what
  it takes effect against. A permission excepts a prohibition, and an exclusion an obligation or a
  power.
- **`ins:qualifies`** links a qualifier to the term or relation whose amount it bounds.

#### A party's details for one instrument: `ins:noticeAddress`, `ins:operatesAt`

Instruments state where each party takes notices and where it operates, and these are details of
the party *for this instrument*, so they sit on the role occupancy rather than on the party itself
(S97). The same company may give one notice address in its lease and another in its loan.

- **`ins:noticeAddress`** comes from the notices clause: "notices shall be given at the address set
  out above". It is the address as written, a string. It never identifies the party, whose identity
  is its keys (Foundation §8).
- **`ins:operatesAt`** is "operates at", "carries on business at": a place the party operates at
  under this instrument, as a concept from the deployment's own territory or site scheme, bound to
  `ins-voc:LocationContract`.

#### Triggers, regimes and gating: `ins:ofPower`, `ins:ofObligation`, `ins:by`, `ins:condition`, `ins:after`, `ins:tolledIn`, `ins:stateKind`, `ins:appliesInState`, `ins:arisesOn`, `ins:arisesOnBreachOf`, `ins:arisesOnExerciseOf`, `ins:endsOn`

- **`ins:ofPower`** and **`ins:ofObligation`** come from "the exercise *of* the power", "a breach
  *of* clause 4.1". They name the relation an exercise or breach trigger watches. In a regime they
  name the stated relation, and match the exercise or breach of every bound relation instantiated
  from it (§11.1).
- **`ins:by`** is "notice given *by* the Licensor": a party whose act an `ins:OnAct` waits for.
  Without it, an act of that kind by any party fires the trigger.
- **`ins:condition`** is the Eligibility condition an `ins:OnCondition` waits for. The trigger fires
  when the condition comes to hold.
- **`ins:after`** is "*after* 90 days": the length of an `ins:OnExpiry` period, a Quantification
  quantity in a unit of time, counted from entering the state the transition leaves. A unit whose
  length depends on a calendar, such as a business day, is a `qnt:CalendarUnit` (ADR-A94).
- **`ins:tolledIn`** comes from *tolling*, the law's word for a period that stops running: a
  limitation period is *tolled*, and a *tolling agreement* stops time running between the parties.
  English drafting says "time shall not run while ...", or writes a "stop the clock" provision.
  `ins:tolledIn` names the states during which an expiry period does not run: "the cure period
  does not run while a force majeure event continues". *Suspended* is not used, since Behaviour's
  core occasion state `bhv:Suspended` has that name, and *paused* is not legal English.
- **`ins:stateKind`** says what kind of state a regime's state is (a notice period, a cure period,
  suspended), as a concept from a scheme bound to `ins-voc:StateKindContract`. It serves readers
  and reports, so that two instruments' notice periods can be found together although each clause
  states its own states. The evaluator never reads it. A state no reader needs to classify has
  none.
- **`ins:appliesInState`** is "this clause applies only while ...", "during the notice period the
  Licensee may not ...". A relation applies only while its regimes are in the states it names: the
  state *gates* a relation that otherwise exists (§11.3).
- **`ins:arisesOn`** and **`ins:endsOn`** are "the obligation arises on ...", "this licence ends on
  ...": the legal trigger on which a relation arises, or ends. Several values are alternatives.
- **`ins:arisesOnBreachOf`** and **`ins:arisesOnExerciseOf`** are short forms of `ins:arisesOn` with
  an `ins:OnBreach` or an `ins:OnExercise`: "if the Provider fails to meet clause 4.1, the Customer
  may end this agreement" is a power arising on breach of the service obligation. A breach chain,
  from a primary duty to the consequences of its breach, is written with them.

```mermaid
---
config:
  layout: elk
---
flowchart LR
    OE["ins:OnExercise"] -- "ofPower" --> PW["ins:Power"]
    OB["ins:OnBreach"] -- "ofObligation" --> OG["ins:Obligation"]
    OA["ins:OnAct"] -- "activity" --> AC["skos:Concept"]
    OA -- "by" --> PA["a party"]
    OC["ins:OnCondition"] -- "condition" --> EC["elg:Condition"]
    OX["ins:OnExpiry"] -- "after" --> QT["qnt:Quantity"]
    OX -- "tolledIn" --> TS["bhv:State<br/>of another state space"]
    LR["ins:LegalRelation"] -- "appliesInState" --> ST["bhv:State<br/>of an ins:Regime"]
    LR -- "arisesOn, endsOn" --> TG["a legal trigger"]
    LR -- "arisesOnBreachOf" --> OG
    LR -- "arisesOnExerciseOf" --> PW
    ST -- "stateKind" --> SK["skos:Concept"]
```

#### At a glance

| Property | Origin | Why this name |
|---|---|---|
| `ins:expressedIn`, `ins:alsoExpressedIn` | "the terms expressed in this agreement", *express* terms: terms the words state | a term is expressed in its clause, and an instrument in its wording. "Also" carries the same term in another language or a consolidated text |
| `ins:boundIn`, `ins:boundFrom` | from computing's *bound variable*: a template's roles and variables are bound to particular parties and values. Also echoes "the parties are bound by its terms" | bound meaning is the template's meaning with its roles and variables bound. "Bound" is also a term of art in some domains, so it is always written "bound meaning" or "bound term", never alone |
| `ins:impliedBy` | *implied terms*: terms implied by statute, custom or the course of dealing, which no clause states | names the source that implies the term in place of a clause |
| `ins:arisesUnder` | "obligations arising under this agreement", "any dispute arising under this licence" | a relation arises under the term that gives rise to it, and belongs to it |
| `ins:party` | "the parties to this agreement" | lists who is party to the instrument, as authored. A beneficiary named in a relation may be no party |
| `ins:obligor`, `ins:obligee` | civil law's *obligor* and *obligee*, the two ends of an *obligatio* | standard legal terms, and unambiguous where "debtor" and "creditor" suggest money |
| `ins:holder`, `ins:counterparty` | "the holder of the power", "the holder of the right", and finance's *counterparty*, the other side of an arrangement | the two ends of a permission, exclusion or power. Hohfeld's names for the far end (no-right, liability, disability) are never used: "liability" has settled senses of its own, such as a liability to pay |
| `ins:activity` | deontic logic's *action*: what a party does | the act a relation is about, or an act a trigger waits for, named plainly (repay, terminate), never with its circumstances |
| `ins:scope` | "the scope of the exclusion", "within the scope of this clause" | the cases a relation applies to, as an Eligibility condition |
| `ins:maintains` | deontic logic's *maintenance* obligation | the state a continuing obligation keeps holding |
| `ins:fulfilledWhen` | *fulfilment* or *performance* of an obligation | the test of performance |
| `ins:excepts` | "except", "save that", "does not apply to": an *exception* | what an exception takes effect against |
| `ins:qualifies` | a qualifier qualifies | what a limit or level applies to |
| `ins:noticeAddress` | the *notices* clause: "notices shall be given at the address set out" | a party's address for notices under this instrument |
| `ins:operatesAt` | "operates at", "carries on business at" | a place a party operates at under this instrument |
| `ins:ofPower`, `ins:ofObligation` | "the exercise of the power", "a breach of clause 4.1" | the relation an exercise or breach trigger watches |
| `ins:by` | "notice given by the Licensor" | a party whose act a trigger waits for |
| `ins:condition` | "if leverage exceeds 3.0 to 1" | the Eligibility condition a trigger waits for |
| `ins:after` | "after 90 days", "on the expiry of 30 Business Days" | the length of an expiry period |
| `ins:tolledIn` | *tolling*: "time shall not run while" | the states in which an expiry period stops running |
| `ins:stateKind` | "a notice period", "a cure period" | what kind of state a regime's state is |
| `ins:appliesInState` | "applies only while", "during the notice period" | the states that gate a relation |
| `ins:arisesOn`, `ins:endsOn` | "arises on", "ends on" | the triggers a relation arises or ends on |
| `ins:arisesOnBreachOf`, `ins:arisesOnExerciseOf` | "if the Provider fails to", "on exercise of" | short forms for arising on a breach or an exercise |

### 4.4 Hohfeld's legal relations

Wesley Newcomb Hohfeld, an American legal theorist, showed that the word "right" in judges' reasoning covered four different things, and that confusing them produced bad decisions. He proposed eight fundamental conceptions, arranged as four pairs of **correlatives**: the two ends of one relation between two people. Whenever one person has the first, the other has the second.

| One party has | The other party has | Means | In this layer |
|---|---|---|---|
| a **claim** (right) | a **duty** | B must do X for A | `ins:Obligation`: obligee and obligor |
| a **privilege** (liberty) | a **no-right** | A may do X, and B cannot demand otherwise | `ins:Permission` (A may act despite a duty not to), `ins:Exclusion` of an obligation (A need not act despite a duty to) |
| a **power** | a **liability** | A can, by an act, change B's legal position | `ins:Power`: holder and counterparty |
| an **immunity** | a **disability** | B cannot change A's legal position | `ins:Exclusion` excepting a `ins:Power` |

```mermaid
flowchart LR
    subgraph FIRST["First order: what a party must or may do"]
        CL["claim"] ---|"correlative"| DU["duty"]
        PV["privilege"] ---|"correlative"| NR["no-right"]
    end
    subgraph SECOND["Second order: who can change the first order"]
        PW["power"] ---|"correlative"| LI["liability"]
        IM["immunity"] ---|"correlative"| DI["disability"]
    end
    OB["ins:Obligation"] -.- DU
    PE["ins:Permission<br/>ins:Exclusion of an obligation"] -.- PV
    PO["ins:Power"] -.- PW
    EX["ins:Exclusion of a power"] -.- IM
```

Why this matters for a computable model:

- **Correlatives are one node.** A duty and its claim are the two ends of one `ins:Obligation`, the
  obligor's end and the obligee's. Nothing has to keep a duty and a claim consistent, because they
  are the same fact seen from two sides.
- **No word is overloaded.** "Right to be paid" is the obligee's end of an obligation, "right to
  terminate" is a power, "right to use" is a permission. Each lands on its own class.
- **Privileges are exceptions.** Hohfeld defines a privilege as the absence of a duty to the
  contrary. Contracts create one by excepting a duty, which is exactly what `ins:excepts` records: a
  permission excepts a prohibition, an exclusion excepts an obligation or a power.
- **First and second order.** Claims, duties and privileges say what parties must and may do now.
  Powers and immunities say who can change that: a power to terminate ends obligations, a power of
  acceptance creates them. Instrument's legal triggers and regimes carry the changes (§10, §11).

Contract English names the privileges differently depending on the duty they are against, so the
T-Box does too: a privilege against a duty not to act is a **permission**, a privilege against a
duty to act is an **exclusion**, and an immunity, a privilege against a power, is also an
**exclusion**.

The same classes meet **deontic logic**, the logic of obligation and permission: O ("obligatory")
is `ins:Obligation`, F ("forbidden", O ¬) is `ins:Prohibition`, and P ("permitted") is
`ins:Permission`, in its strong sense, as an exception.

### 4.5 One modal verb per class

Each class can be read with one modal verb, so a sentence rendered from data can be consistently made:

| Class | Reads as |
|---|---|
| `ins:Obligation` | *the obligor **must** {activity} for the obligee* |
| `ins:ContinuingObligation` | *the obligor **must ensure** that {state} holds* |
| `ins:Prohibition` | *the obligor **must not** {activity}* |
| `ins:Permission` | *the holder **may** {activity}, despite {the prohibition}* |
| `ins:Exclusion` | *the holder **need not** {the obligation's activity}*, or *{the power} **cannot be exercised** against the holder* |
| `ins:Power` | *the holder **may** {activity}, which changes the counterparty's position* |

```mermaid
flowchart TB
    subgraph WORDS["What the wording says"]
        SH["shall, must"]
        SE["shall ensure"]
        SN["shall not, must not"]
        DN["does not apply to, save that, permitted"]
        NL["shall not be liable, not obliged"]
        MN["may by notice, may terminate, may accept"]
    end
    SH --> OB["ins:Obligation"]
    SE --> CO["ins:ContinuingObligation"]
    SN --> PR["ins:Prohibition"]
    DN --> PE["ins:Permission"]
    NL --> EX["ins:Exclusion"]
    MN --> PO["ins:Power"]
```

### 4.6 Words this layer does not use

| Word | Why not |
|---|---|
| Right | covers four Hohfeldian things. Each has its own class |
| Duty, Claim | one end of an obligation each |
| Liability | has settled senses of its own, such as a liability to pay, so a reader would misread it. The far end of a power is `ins:counterparty` |
| Condition | three senses in contracts (§4.2) |
| Provision | both a clause and what it provides |
| Clause, Section, Schedule | parts of a document, so Wording's element types |
| Contract | the whole of wording and instrument |
| Norm, Statement | legal theory, not contract English |
| Lifecycle | not used in the T-Box (CC-D8). An instrument may be in several regimes at once, each named for what it is (§4.2, `ins:Regime`) |
| Status | one value, where an instrument may be in several regimes at once. A regime's state is a `bhv:State` |
| Suspended, paused (of a period) | a period that stops running is *tolled* (`ins:tolledIn`). `bhv:Suspended` is Behaviour's core occasion state |
| Event (for a trigger) | names what happened, which the runtime records. What an instrument waits for is a legal trigger |
| Basis | reserved for the unit an amount applies on (contract amounts) |
| Binder | a term of art in some domains, with a meaning of its own. What turns stated meaning into bound meaning is **instantiation** |

## 5. Model Overview

### 5.1 The words are the contract

A contract's legal force comes from its words. A court reads the wording the parties signed, not a
database. A computable contract therefore keeps two things side by side, and never lets them drift
apart:

- **the wording**, held exactly as written by the Wording layer: every clause, each in its own
  version, assembled for each instrument with the values its particulars supply
- **the meaning**, held by this layer: the terms the clauses give rise to, and the legal relations
  under them, as data a machine can check and, in later slices, evaluate

The connection between the two is the point of the whole substrate. Every computable node in this
layer is tied back to the words that create it:

- a **stated term** is part of exactly one clause version (`ins:expressedIn`). The meaning is the
  clause's, and it cannot change unless the clause does, since a changed clause is a new clause
  version with new stated meaning
- an **instrument** is expressed in exactly one assembled wording (`ins:expressedIn`, law I1): the
  exact text this instrument's parties agreed
- a **bound term** is part of exactly one instrument version (`ins:boundIn`), instantiated from the
  stated term of a clause that instrument's wording includes (`ins:boundFrom`)
- a **relation** belongs to its term (`ins:arisesUnder`), and through it to the clause or the
  instrument

So from any relation the evaluator acts on, there is one path back to the words: relation, bound
term, stated term, clause version, the text itself. Nothing in this layer has legal effect of its
own. If the data and the words ever disagree, the words win, and the data is wrong. A term no clause
states, a term *implied* by law, names the statute, custom or course of dealing that implies it
(`ins:impliedBy`) in place of a clause.

```mermaid
---
config:
  layout: elk
---
flowchart TB
    subgraph LEGAL["Legally binding: the Wording layer"]
        F["the form<br/>wrd:Wording"]
        C1["clause 6.1, version 1<br/>The Borrower shall repay each loan..."]
        AW["Acme's assembled wording<br/>wrd:AssembledWording<br/>the text Acme signed"]
        F -- "comprises" --> C1
        AW -- "assembledFrom" --> F
        AW -- "includes" --> C1
    end
    subgraph COMPUTABLE["Computable: this layer"]
        ST["stated term 6.1<br/>the clause's meaning, in roles"]
        SR["stated obligation<br/>Borrower must repay Lenders"]
        IN["Acme's facility<br/>ins:Instrument"]
        BT["bound term 6.1<br/>for Acme's facility"]
        BR["bound obligation<br/>Acme must repay the lenders"]
        SR -- "arisesUnder" --> ST
        BR -- "arisesUnder" --> BT
        BT -- "boundFrom" --> ST
        BR -- "boundFrom" --> SR
    end
    ST -- "expressedIn" --> C1
    IN -- "expressedIn" --> AW
    BT -- "boundIn" --> IN
    style LEGAL fill:#BBDEFB
    style COMPUTABLE fill:#bcdee1
```

### 5.2 From words to data

Meaning is written once per clause, and instantiated once per instrument. A lender's form holds
clauses used in every facility it signs. Each clause's stated meaning names the form's roles: "the
Borrower", "the Lenders". When Acme signs a facility on the form, instantiation takes the stated
meaning of each clause Acme's wording includes, the values Acme's particulars supply, and Acme's
parties, and produces the bound meaning of Acme's facility: Acme Holdings plc must repay North Bank
and South Bank. Bound meaning is a derived artefact (ADR-A92): it can be rebuilt from its three
inputs at any time, and is never the source of truth.

```mermaid
flowchart LR
    CL["clause versions<br/>Wording"] -- "state" --> SM["stated meaning<br/>templates, naming roles"]
    AW["the instrument's assembled wording<br/>which clauses, which values"] --> INST
    PA["the instrument's parties<br/>role occupancies, groups"] --> INST
    SM --> INST(("instantiation"))
    INST --> BM["bound meaning<br/>naming parties and values"]
    BM --> EV["evaluation<br/>C12, C13"]
    style INST fill:#fff3cd
```

### 5.3 Tracing a decision back to the words

When the evaluator later reports that Acme is in breach of its leverage covenant, the finding must
point at the clause that makes it so. The path is always the same, and always one step at a time:

```mermaid
sequenceDiagram
    participant E as evaluation (later slices)
    participant BR as bound relation
    participant BT as bound term
    participant ST as stated term
    participant CL as clause version
    E->>BR: Acme's leverage covenant is breached
    BR->>BT: arisesUnder
    BT->>ST: boundFrom
    ST->>CL: expressedIn
    CL-->>E: clause 7.1, version 1, its text
```

### 5.4 When the words change

Meaning never changes on its own (law I18). New words are a new clause version, which states new
meaning. An instrument reaches new words only through a new assembled wording, and so a new
instrument version, made by an amendment (C9), whose bound meaning is instantiated afresh. The old
version, its wording and its bound meaning stay as they were, so what was agreed at any time can
always be read.

```mermaid
flowchart LR
    subgraph V1["Version 1"]
        C1["clause 7.1 v1<br/>3.0 to 1"] --> S1["stated term v1"]
        I1["facility v1"] --> B1["bound term<br/>3.0 to 1"]
    end
    subgraph V2["Version 2, after an amendment"]
        C2["clause 7.1 v2<br/>3.5 to 1"] --> S2["stated term v2"]
        I2["facility v2"] --> B2["bound term<br/>3.5 to 1"]
    end
    C1 -. "superseded by" .-> C2
    I1 -. "superseded by" .-> I2
    B1 -. "boundFrom" .-> S1
    B2 -. "boundFrom" .-> S2
```

A correction, fixing how a clause was read with no change to its words, regenerates the clause's
stated meaning and is not an amendment (law I18).

### 5.5 The model in one picture

The whole layer, with the law each link enforces:

```mermaid
flowchart LR
    IN["ins:Instrument<br/>a fnd:Version"]
    AW["wrd:AssembledWording"]
    EL["wrd:Element<br/>a clause version"]
    ST["stated ins:Term<br/>a ins:Template"]
    BT["bound ins:Term"]
    SR["stated relation<br/>names pty:Roles"]
    BR["bound relation<br/>names occupancies and groups"]
    IN -- "expressedIn (exactly one, I1)" --> AW
    AW -- "includes" --> EL
    ST -- "expressedIn (exactly one, I2)" --> EL
    BT -- "boundIn (exactly one, I2)" --> IN
    BT -- "boundFrom (exactly one)" --> ST
    SR -- "arisesUnder (exactly one)" --> ST
    BR -- "arisesUnder (exactly one)" --> BT
    BR -- "boundFrom" --> SR
```

Every relation arises under exactly one term, and belongs to it. A stated term belongs to the
element version of the wording that expresses it. A bound term belongs to the instrument version
that binds it, and is bound from the stated term it instantiates (§6). An exception names what it
excepts.

### 5.6 The relation classes

The four kinds of legal relation, and the two kinds of obligation (§7):

```mermaid
flowchart TB
    LR["ins:LegalRelation<br/>≡ Obligation ⊔ Permission ⊔ Exclusion ⊔ Power"]
    OB["ins:Obligation<br/>obligor must perform for obligee"]
    CO["ins:ContinuingObligation<br/>must keep a state holding"]
    PR["ins:Prohibition<br/>must not perform"]
    PE["ins:Permission<br/>may perform despite a prohibition"]
    EX["ins:Exclusion<br/>need not perform, or is immune"]
    PO["ins:Power<br/>can change the counterparty's position"]
    OB --> LR
    PE --> LR
    EX --> LR
    PO --> LR
    CO --> OB
    PR --> OB
    PE -. "excepts" .-> PR
    EX -. "excepts" .-> OB
    EX -. "excepts" .-> PO
```

### 5.7 Regimes and triggers in one picture

A regime is stated by its clause, like a template, and is never bound. Each instrument that includes
the clause has its own progress through it, held at runtime as Behaviour occupancies of the
regime's states for the instrument's persistent identity. A bound relation gated by a state names
the stated regime's state, and reads that occupancy (§11).

```mermaid
flowchart LR
    subgraph STATED["Stated meaning: part of the clause version"]
        ST["stated term"]
        RG["ins:Regime<br/>a bhv:StateSpace"]
        S1["in force<br/>a bhv:State"]
        S2["notice period<br/>a bhv:State"]
        RT["ins:RegimeTransition"]
        TG["ins:OnExercise<br/>ofPower the stated power"]
        RG -- "arisesUnder" --> ST
        S1 -- "inStateSpace" --> RG
        S2 -- "inStateSpace" --> RG
        RT -- "fromState" --> S1
        RT -- "toState" --> S2
        RT -- "hasTrigger" --> TG
    end
    subgraph BOUND["Bound meaning: part of the instrument version"]
        BR["bound relation"]
    end
    subgraph RUNTIME["Runtime: Behaviour's records"]
        OC["occupancy<br/>forSubject the instrument's identity"]
    end
    BR -- "appliesInState" --> S2
    OC -- "occupiesState" --> S2
    style STATED fill:#BBDEFB
    style BOUND fill:#bcdee1
```

## 6. Instrument and Term

### 6.1 Instrument

An instrument is the legal instrument itself: a contract, policy, agreement, deed, licence or
protocol. It is the only version in this layer. Its persistent identity carries its keys, such as
an agreement number (Foundation §8), and its runtime state (ADR-A106).

`ins:party` lists the parties to the instrument as authored: who signs it. It is not derived from
the relations' parties, because a relation may name a beneficiary or a regulator who is no party
(CC-Q4), and each party executes separately (S90, C9).

```turtle-spec
ins:Instrument a owl:Class ;
	rdfs:subClassOf fnd:Version ;
	rdfs:comment "A legal instrument: a contract, policy, agreement, deed, licence or protocol. The only version in this layer." ;
	fnd:utility "Subject: one version of an instrument. Expressed in exactly one assembled wording (ins:expressedIn, law I1). Its persistent identity carries its keys and its runtime state. Its terms are bound in it (ins:boundIn)." .

ins:party a owl:ObjectProperty ;
	rdfs:domain ins:Instrument ;
	rdfs:range ins:RelationParty ;
	rdfs:comment "A party to an instrument version." ;
	fnd:utility "Subject: an instrument version. Value: a role occupancy or participation group party to it, as authored. Never derived from the relations' parties: a beneficiary or regulator named in a relation may be no party." .

ins:expressedIn a owl:ObjectProperty ;
	rdfs:comment "The text that states an instrument version or a stated term." ;
	fnd:utility "Subject: an instrument version, or a stated term. Value: for an instrument, exactly one wrd:AssembledWording (law I1). For a stated term, exactly one wrd:Element version, its owner (law I2). The shapes check each case." .
```

### 6.2 Terms in two tiers

A term is a provision the parties are bound by. It exists apart from its relations because:

- one provision may give rise to several relations: "shall not create security, except a lien
  arising by operation of law" is a prohibition and the permission excepting it (the facility
  example, clause 8.1)
- what belongs to the whole provision attaches to the term: its classification and survival, the
  sections it applies within, and definitions and deemings, which arise under terms without being
  relations (C7b), and qualifiers such as limits (C8)
- terms implied by law (`ins:impliedBy`) and incorporated terms (C9) work at the level of the
  provision
- the term is the unit that is owned and bound: one stated term per element version, one bound
  term per instrument version

Every clause's meaning exists in two tiers, each with exactly one owner (CC-D12, ADR-A104
decision 2):

| Tier | Says | Names | Owner |
|---|---|---|---|
| **stated meaning** (`ins:Template`) | what the clause says in its own words: "the Borrower shall repay" | `pty:Role`s, defined words, variables | exactly one element version (`ins:expressedIn`) |
| **bound meaning** | what it says for one instrument: Acme owes the lenders | role occupancies, groups, values | exactly one instrument version (`ins:boundIn`) |

A relation belongs to its term (`ins:arisesUnder`), and through it to the term's owner. Only terms
carry `ins:expressedIn` or `ins:boundIn`.

Bound meaning is what **instantiation** produces from stated meaning, the wording's variable values
and the instance's parties (a derived artefact, ADR-A92). A bound relation restates its template in
full. RDF has no override: a bound relation that stated only what differs would leave both the
template's role and the occupancy as its parties. Only bound relations are evaluated (law I13).
Regimes have one tier: a regime is stated meaning only, read as stated for each subject (§11.1).

```mermaid
flowchart TB
    subgraph STATED["Stated meaning: part of the clause version"]
        S1["tmpl:term-8-1<br/>a ins:Term, ins:Template"]
        S2["tmpl:negative-pledge<br/>obligor Borrower (a role)"]
        S3["tmpl:permitted-liens<br/>holder Borrower (a role)"]
        S2 -- "arisesUnder" --> S1
        S3 -- "arisesUnder" --> S1
    end
    subgraph BOUND["Bound meaning: part of the instrument version"]
        B1["ex:term-8-1<br/>a ins:Term"]
        B2["ex:negative-pledge<br/>obligor ex:borrower-occ"]
        B3["ex:permitted-liens<br/>holder ex:borrower-occ"]
        B2 -- "arisesUnder" --> B1
        B3 -- "arisesUnder" --> B1
    end
    CL["clause 8.1 v1"]
    IN["ex:facility-v1"]
    S1 -- "expressedIn" --> CL
    B1 -- "boundIn" --> IN
    B1 -- "boundFrom" --> S1
    B2 -- "boundFrom" --> S2
    B3 -- "boundFrom" --> S3
    style STATED fill:#BBDEFB
    style BOUND fill:#bcdee1
```

```turtle-spec
ins:Term a owl:Class ;
	rdfs:comment "A provision the parties are bound by." ;
	fnd:utility "Subject: a term, stated or bound. Not a version: it is part of its owner and changes only with it. A stated term (an ins:Template) is expressed in exactly one element version. A bound term is bound in exactly one instrument version, from exactly one stated term or implied by a source (law I2). Relations and qualifiers arise under it." .

ins:Template a owl:Class ;
	rdfs:comment "Stated meaning: a term, relation or qualifier as its clause states it." ;
	fnd:utility "A mixin on ins:Term, ins:LegalRelation, ins:Qualifier and ins:Regime. A template names pty:Roles, defined words and variables, never occupancies or values (law I13). A term, relation or qualifier template is never evaluated. A regime is always a template, stated once and read as stated for each subject (C7a-Q1). Its term is expressed in exactly one element version." .

ins:alsoExpressedIn a owl:ObjectProperty ;
	rdfs:domain ins:Term ;
	rdfs:range wrd:Element ;
	rdfs:comment "Another element that states the same stated term." ;
	fnd:utility "Subject: a stated term. Value: an element version stating it again, in another language or a consolidated text (ADR-A96). Its owner stays its one ins:expressedIn. The optional shapes/single-expression.ttl refuses it where every term is expressed once." .

ins:boundIn a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain ins:Term ;
	rdfs:range ins:Instrument ;
	rdfs:comment "The instrument version a bound term is part of." ;
	fnd:utility "Subject: a bound term. Value: the one instrument version that owns it (law I2). Relations carry none: they belong to their term." .

ins:boundFrom a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:subPropertyOf prov:wasDerivedFrom ;
	rdfs:comment "The stated node a bound node was instantiated from." ;
	fnd:utility "Subject: a bound term, relation or qualifier. Value: the one stated node of the same kind it was instantiated from. A bound node has this or ins:impliedBy, never both." .

ins:impliedBy a owl:ObjectProperty ;
	rdfs:comment "The source that implies a term no clause states." ;
	fnd:utility "Subject: a bound term or relation implied by law. Value: the statute, custom or course of dealing that implies it, in place of ins:boundFrom." .
```

## 7. Legal Relations

Five classes, each arising under exactly one term ([ADR-A104](../../docs/architecture/decisions/ADR-A104-instrument-terms-and-legal-relations.md)
decision 3). Permission and Exclusion are both Hohfeldian privileges: a liberty to act despite a
duty not to, and a liberty not to act despite a duty to, or an immunity against a power. Contract
English names them differently, and so does the T-Box.

| Class | Reads as | Parties | Required content |
|---|---|---|---|
| `ins:Obligation` | the obligor must perform the activity for the obligees | one `ins:obligor`, `ins:obligee`s | `ins:activity` |
| `ins:ContinuingObligation` | the obligor must keep a state holding | same | `ins:maintains` |
| `ins:Prohibition` | the obligor must not perform the activity within the scope | same | `ins:activity` |
| `ins:Permission` | the holder may perform the activity despite a prohibition | one `ins:holder`, `ins:counterparty`s | `ins:activity`, `ins:excepts` a prohibition |
| `ins:Exclusion` | the holder need not perform an obligation, or is immune from a power, within the scope | same | `ins:excepts` an obligation or a power |
| `ins:Power` | the holder can, by an act, change the counterparty's legal position | same | `ins:activity` |

```turtle-spec
ins:LegalRelation a owl:Class ;
	owl:equivalentClass [ a owl:Class ; owl:unionOf ( ins:Obligation ins:Permission ins:Exclusion ins:Power ) ] ;
	rdfs:comment "A legal relation between parties: an obligation, permission, exclusion or power." ;
	fnd:utility "Subject: a relation, stated or bound. Arises under exactly one term (ins:arisesUnder) and belongs to it. Never a version." .

ins:Obligation a owl:Class ;
	rdfs:subClassOf ins:LegalRelation ;
	rdfs:comment "The obligor must perform an activity for the obligees." ;
	fnd:utility "Subject: an obligation. Exactly one ins:obligor, at least one ins:obligee, and an ins:activity unless continuing." .

ins:ContinuingObligation a owl:Class ;
	rdfs:subClassOf ins:Obligation ;
	rdfs:comment "The obligor must ensure a state holds throughout." ;
	fnd:utility "Subject: a continuing obligation, such as a financial covenant. States the state it keeps with ins:maintains." .

ins:Prohibition a owl:Class ;
	rdfs:subClassOf ins:Obligation ;
	rdfs:comment "The obligor must not perform an activity within the scope." ;
	fnd:utility "Subject: a prohibition, such as a negative pledge. A permission may except it." .

ins:Permission a owl:Class ;
	rdfs:subClassOf ins:LegalRelation ;
	rdfs:comment "The holder may perform an activity despite a prohibition." ;
	fnd:utility "Subject: a permission. Excepts exactly one prohibition, whose obligor is its holder, with the same activity (law I8). A licence to act with nothing forbidding it is no relation in this layer." .

ins:Exclusion a owl:Class ;
	rdfs:subClassOf ins:LegalRelation ;
	rdfs:comment "The holder need not perform an obligation, or cannot be made subject to a power, within the scope." ;
	fnd:utility "Subject: an exclusion. Excepts exactly one obligation, whose obligor is its holder, or one power, whose counterparty is its holder (law I8). An exclusion of a power is an immunity." .

ins:Power a owl:Class ;
	rdfs:subClassOf ins:LegalRelation ;
	rdfs:comment "The holder can, by an act, change the counterparty's legal position." ;
	fnd:utility "Subject: a power, such as acceleration or termination. Its activity is the act that exercises it." .

[] a owl:AllDisjointClasses ;
	owl:members ( ins:Obligation ins:Permission ins:Exclusion ins:Power ) .

ins:ContinuingObligation owl:disjointWith ins:Prohibition .

ins:arisesUnder a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:range ins:Term ;
	rdfs:comment "The term a relation, regime or qualifier arises under, and belongs to." ;
	fnd:utility "Subject: a relation, regime or qualifier. Value: its one term. A stated relation arises under a stated term, a bound relation under a bound term. A regime is stated only, so it arises under a stated term." .

ins:excepts a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:range ins:LegalRelation ;
	rdfs:comment "The relation an exception takes effect against." ;
	fnd:utility "Subject: a permission or an exclusion. Value: for a permission, the prohibition it excepts. For an exclusion, the obligation or power it excepts. Bound exceptions except bound relations." .
```

## 8. Parties

The four party properties range over one union, named once ([C6-Q4](../../docs/developer/plans/computable-contract-substrate.md)):
a role occupancy, a participation group, or, on stated meaning only, a role (law I13).

- A **group** is the obligee of a several duty (each lender for its share) or the holder of a
  joint power (the lenders together). Its composition rule says how its members act. How a stated
  clause says so ("each for its share") is stated in C7b, by a defined party word.
- A **contingent occupancy** (ADR-A102), a role with no actor, stands for a party that depends on
  the case: the owner of a product when a claim is made. How it is resolved for each case is
  decided in C7b.
- **Party details** belong to the occupancy, since they are this party's details for this
  instrument (S97). A notice address is a string as written: the party's identity is its keys.

What stands at each end of a relation, in each tier, and who is party to the instrument:

```mermaid
---
config:
  layout: elk
---
flowchart TB
    subgraph STATED["Stated meaning"]
        SO["stated obligation"] -- "obligor" --> RB["pty:Role Borrower"]
        SO -- "obligee" --> RL["pty:Role Lender"]
    end
    subgraph BOUND["Bound meaning"]
        BO["bound obligation"] -- "obligor" --> OC["pty:RoleOccupancy<br/>Acme as Borrower"]
        BO -- "obligee" --> GR["pty:ParticipationGroup<br/>the lenders, several only"]
        BO -- "obligee" --> TR["pty:RoleOccupancy<br/>trustee, no party"]
        GR -- "hasParticipant" --> M1["membership 0.6<br/>North Bank"]
        GR -- "hasParticipant" --> M2["membership 0.4<br/>South Bank"]
    end
    IN["ins:Instrument"] -- "party" --> OC
    IN -- "party" --> M1occ["North Bank's occupancy"]
    IN -- "party" --> M2occ["South Bank's occupancy"]
    M1 -- "memberOccupancy" --> M1occ
    M2 -- "memberOccupancy" --> M2occ
    BO -- "boundFrom" --> SO
    style STATED fill:#BBDEFB
    style BOUND fill:#bcdee1
```

A contingent occupancy has a role and no actor until the case fills it:

```mermaid
flowchart LR
    RE["repair<br/>ins:Obligation"] -- "obligee" --> OW["owner occupancy<br/>inRole Owner<br/>no occupiedBy"]
    CL["a claim, later"] -. "fills it for that claim (C7b)" .-> OW
```

```turtle-spec
ins:RelationParty a owl:Class ;
	owl:equivalentClass [ a owl:Class ; owl:unionOf ( pty:RoleOccupancy pty:ParticipationGroup pty:Role ) ] ;
	rdfs:comment "What a relation's party may be: a role occupancy, a participation group, or on stated meaning a role." ;
	fnd:utility "The range of the four party properties and of ins:party. Stated meaning names roles, bound meaning occupancies and groups (law I13)." .

pty:RoleOccupancy rdfs:subClassOf ins:RelationParty .
pty:ParticipationGroup rdfs:subClassOf ins:RelationParty .
pty:Role rdfs:subClassOf ins:RelationParty .

ins:obligor a owl:ObjectProperty ;
	rdfs:domain ins:Obligation ;
	rdfs:range ins:RelationParty ;
	rdfs:comment "The party who must perform an obligation." ;
	fnd:utility "Subject: an obligation. Value: exactly one party: a role on stated meaning, an occupancy or group on bound meaning." .

ins:obligee a owl:ObjectProperty ;
	rdfs:domain ins:Obligation ;
	rdfs:range ins:RelationParty ;
	rdfs:comment "A party an obligation is owed to." ;
	fnd:utility "Subject: an obligation. Value: one of at least one parties it is owed to, who need not be a party to the instrument." .

ins:holder a owl:ObjectProperty ;
	rdfs:domain ins:LegalRelation ;
	rdfs:range ins:RelationParty ;
	rdfs:comment "The party who holds a permission, exclusion or power." ;
	fnd:utility "Subject: a permission, exclusion or power. Value: exactly one party." .

ins:counterparty a owl:ObjectProperty ;
	rdfs:domain ins:LegalRelation ;
	rdfs:range ins:RelationParty ;
	rdfs:comment "A party against whom a permission, exclusion or power holds." ;
	fnd:utility "Subject: a permission, exclusion or power. Value: one of at least one parties whose position it affects." .

ins:noticeAddress a owl:DatatypeProperty ;
	rdfs:domain pty:RoleOccupancy ;
	rdfs:range xsd:string ;
	rdfs:comment "Where a party takes notices under an instrument." ;
	fnd:utility "Subject: a role occupancy. Value: the address as written in the instrument. Never the party's identity, which is its keys (CC-D9)." .

ins:operatesAt a owl:ObjectProperty ;
	rdfs:domain pty:RoleOccupancy ;
	rdfs:range skos:Concept ;
	rdfs:comment "A place a party operates at under an instrument." ;
	fnd:utility "Subject: a role occupancy. Value: a concept from the territory or site scheme a deployment binds to ins-voc:LocationContract." .
```

## 9. Content of a Relation and Qualifiers

An activity names the act, never the circumstances it is done in: those are the scope. Enrolment
is `ins-voc:Enrol` whether or not the participant meets the criteria, and a prohibition on
enrolling the ineligible is `Enrol` with that scope. Termination for convenience and for breach are
both `ins-voc:Terminate`.

What a relation says, besides its parties:

```mermaid
flowchart LR
    R["a legal relation"]
    R -- "activity (the act)" --> A["ins-voc:Terminate<br/>a concept"]
    R -- "scope (the cases)" --> S["elg:Condition<br/>without cause"]
    R -- "arisesUnder" --> T["its term"]
    CO["a continuing obligation"] -- "maintains (the state)" --> M["elg:Condition<br/>leverage ≤ 3.0"]
    OB["an obligation"] -- "fulfilledWhen (performance)" --> F["elg:Condition"]
    EXC["a permission or exclusion"] -- "excepts" --> X["the relation it excepts"]
    Q["ins:Qualifier"] -- "qualifies" --> R
```

A scope with a carve-back, from the warranty: the exclusion applies to misuse, unless the failure
was caused by a manufacturing defect.

```mermaid
flowchart LR
    EX["misuse exclusion"] -- "scope" --> AND["misuse, not a defect<br/>AllRequired"]
    AND -- "hasCondition" --> M["caused by misuse"]
    AND -- "hasCondition" --> D["caused by a defect<br/>negated: the carve-back"]
    EX -- "excepts" --> RE["the duty to repair"]
```

```turtle-spec
ins:activity a owl:ObjectProperty ;
	rdfs:range skos:Concept ;
	rdfs:comment "The act a relation is about, or an act a trigger waits for." ;
	fnd:utility "Subject: a relation, or an ins:OnAct trigger. No domain, since its subjects are of both kinds (C7a-Q2): the shapes check each. Value: a concept naming the act, from the scheme bound to ins-voc:ActivityContract. Never a circumstance of the act, which is the scope." .

ins:scope a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain ins:LegalRelation ;
	rdfs:range elg:Condition ;
	rdfs:comment "The cases a relation applies to." ;
	fnd:utility "Subject: a relation. Value: at most one Eligibility condition over the case. A carve-back is a negated member of it." .

ins:maintains a owl:ObjectProperty ;
	rdfs:domain ins:ContinuingObligation ;
	rdfs:range elg:Condition ;
	rdfs:comment "The state a continuing obligation keeps holding." ;
	fnd:utility "Subject: a continuing obligation. Value: exactly one condition that must hold throughout." .

ins:fulfilledWhen a owl:ObjectProperty ;
	rdfs:domain ins:Obligation ;
	rdfs:range elg:Condition ;
	rdfs:comment "The test of an obligation's performance." ;
	fnd:utility "Subject: an obligation. Value: the condition its performance meets. Without one, performance is an act of its activity for the case by the obligor or a delegate." .

ins:Qualifier a owl:Class ;
	rdfs:comment "A limit, level or retention on a term or a relation." ;
	fnd:utility "Subject: a qualifier. Arises under exactly one term and qualifies exactly one term or relation. Its amounts are defined with contract amounts (C8)." .

ins:qualifies a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain ins:Qualifier ;
	rdfs:comment "The term or relation a qualifier qualifies." ;
	fnd:utility "Subject: a qualifier. Value: exactly one term or relation." .

[] a owl:AllDisjointClasses ;
	owl:members ( ins:Instrument ins:Term ins:LegalRelation ins:Qualifier ) .

ins:Term owl:disjointWith fnd:Version .
ins:LegalRelation owl:disjointWith fnd:Version .
ins:Qualifier owl:disjointWith fnd:Version .
ins:Template owl:disjointWith ins:Instrument .
```

## 10. Legal Triggers

A legal trigger is what an instrument makes a consequence turn on (§4.2). Each of the five is a
Behaviour trigger definition with one required value ([ADR-A104](../../docs/architecture/decisions/ADR-A104-instrument-terms-and-legal-relations.md)
decision 6). Each moves regimes, as the trigger of a regime transition (§11), and all but
`ins:OnExpiry` also mark the moment a relation arises or ends (`ins:arisesOn`, `ins:endsOn`). An
expiry counts from entering a state, and a relation has no state to enter: a relation's own periods
are due ranges (C7b).

| Trigger | Required value | Optional | Kind, fixed by the class |
|---|---|---|---|
| `ins:OnExercise` | `ins:ofPower`: exactly one power | | `bhv:ExternalStimulus` |
| `ins:OnBreach` | `ins:ofObligation`: exactly one obligation | | `bhv:DerivedTrigger` |
| `ins:OnAct` | `ins:activity`: exactly one concept | `ins:by`: the parties whose act counts | `bhv:ExternalStimulus` |
| `ins:OnCondition` | `ins:condition`: exactly one Eligibility condition | | `bhv:DerivedTrigger` |
| `ins:OnExpiry` | `ins:after`: exactly one quantity of time | `ins:tolledIn`: the states in which the period does not run | `bhv:ScheduledTrigger` |

**The kind follows from the class.** An exercise and an act come from outside: a party does
something, and the runtime receives it as a stimulus. A breach and a condition are derived: the
runtime works them out from what it already holds. An expiry is scheduled: the runtime knows in
advance when it falls. Each class therefore fixes its kind as an `owl:hasValue` restriction, and
its shape permits that one value (§12).

**An expiry** counts its period from entering the state its transition leaves, and fires when the
period has run. The length is a `qnt:Quantity` in a unit of time: days in the licence (§16.5),
business days in the facility (§16.7). Counting business days needs the calendar in force, which a
conversion context names when the expiry is evaluated (ADR-A94, C12). A length the instance
supplies, such as a notice period set by a variable, is resolved for each instrument at runtime
(C8).

**Tolling.** "The cure period does not run while a force majeure event prevents the Borrower from
reporting" is `ins:tolledIn` on the cure period's expiry, naming the force majeure regime's affected
state. The period's clock stops while the subject is in any of the named states, and runs again
when it leaves them. C12 counts the period over the occupancy history (ADR-A106 addendum, decision
9). A tolling state is never a state of the state space the period runs in: leaving the period's
state for a sibling ends the period anyway, and the period's own state cannot stop its own clock.
A sub-state of the period's state, in a region of it, may (C11a-Q2).

The facility's cure period, with force majeure arising part way through it (dates illustrative):

```mermaid
gantt
    dateFormat YYYY-MM-DD
    axisFormat %d %b
    section Default regime
    cure period, counting         :active, c1, 2027-10-01, 2027-10-20
    cure period, tolled           :crit, c2, 2027-10-20, 2027-10-27
    cure period, counting again   :active, c3, 2027-10-27, 2027-11-15
    default                       :done, d1, 2027-11-15, 2027-11-25
    section Force majeure regime
    unaffected                    :u1, 2027-10-01, 2027-10-20
    affected                      :crit, f1, 2027-10-20, 2027-10-27
    unaffected                    :u2, 2027-10-27, 2027-11-25
```

**Arising and ending** (§4.2.4 explains both). A relation that exists only once something has
happened says so with `ins:arisesOn`: a power to terminate that arises on breach of the service obligation, a duty to
repay at once that arises on acceleration. `ins:arisesOnBreachOf` and `ins:arisesOnExerciseOf` are
its short forms, and the usual way to write a breach chain: the primary duty, then each consequence
of its breach. Several values of these properties are alternatives: the relation arises on any of
them. `ins:endsOn` names the triggers on which a relation ends. A relation with no arising trigger
has arisen once its instrument takes effect. A bound relation's arising names bound relations,
since it restates its template in full (ADR-A104 2026-10-04 addendum, decision 3). Due ranges,
recurrence, survival and `ins:ends` are C7b's.

```mermaid
flowchart LR
    PS["provide service<br/>ins:Obligation"]
    EF["end for failure<br/>ins:Power"]
    TX["termination excluded<br/>ins:Exclusion"]
    EF -- "arisesOnBreachOf" --> PS
    TX -- "arisesOnBreachOf" --> PS
    TX -. "excepts" .-> EF
```

```turtle-spec
ins:OnExercise a owl:Class ;
	rdfs:subClassOf bhv:TriggerDefinition ,
		[ a owl:Restriction ; owl:onProperty bhv:triggerKind ; owl:hasValue bhv:ExternalStimulus ] ;
	rdfs:comment "A legal trigger: the exercise of a power." ;
	fnd:utility "Subject: a trigger. Names exactly one power (ins:ofPower). In a regime, a stated power: the trigger fires on the exercise of every bound power instantiated from it. Its kind is bhv:ExternalStimulus. Assert bhv:TriggerDefinition and the kind where no reasoner runs (§12)." .

ins:OnBreach a owl:Class ;
	rdfs:subClassOf bhv:TriggerDefinition ,
		[ a owl:Restriction ; owl:onProperty bhv:triggerKind ; owl:hasValue bhv:DerivedTrigger ] ;
	rdfs:comment "A legal trigger: the breach of an obligation." ;
	fnd:utility "Subject: a trigger. Names exactly one obligation (ins:ofObligation). In a regime, a stated obligation: the trigger fires on the breach of an occasion of every bound obligation instantiated from it. Its kind is bhv:DerivedTrigger. Assert bhv:TriggerDefinition and the kind where no reasoner runs (§12)." .

ins:OnAct a owl:Class ;
	rdfs:subClassOf bhv:TriggerDefinition ,
		[ a owl:Restriction ; owl:onProperty bhv:triggerKind ; owl:hasValue bhv:ExternalStimulus ] ;
	rdfs:comment "A legal trigger: an act that exercises no power." ;
	fnd:utility "Subject: a trigger. Names exactly one act (ins:activity), and optionally the parties whose act counts (ins:by). Its kind is bhv:ExternalStimulus. Assert bhv:TriggerDefinition and the kind where no reasoner runs (§12)." .

ins:OnCondition a owl:Class ;
	rdfs:subClassOf bhv:TriggerDefinition ,
		[ a owl:Restriction ; owl:onProperty bhv:triggerKind ; owl:hasValue bhv:DerivedTrigger ] ;
	rdfs:comment "A legal trigger: a condition coming to hold." ;
	fnd:utility "Subject: a trigger. Names exactly one Eligibility condition (ins:condition), and fires when it comes to hold. Its kind is bhv:DerivedTrigger. Assert bhv:TriggerDefinition and the kind where no reasoner runs (§12)." .

ins:OnExpiry a owl:Class ;
	rdfs:subClassOf bhv:TriggerDefinition ,
		[ a owl:Restriction ; owl:onProperty bhv:triggerKind ; owl:hasValue bhv:ScheduledTrigger ] ;
	rdfs:comment "A legal trigger: the end of a period counted from entering a state." ;
	fnd:utility "Subject: a trigger. Names exactly one length (ins:after), counted from entering the state its transition leaves, and optionally the states in which the period does not run (ins:tolledIn). Its kind is bhv:ScheduledTrigger. Assert bhv:TriggerDefinition and the kind where no reasoner runs (§12)." .

ins:ofPower a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain ins:OnExercise ;
	rdfs:range ins:Power ;
	rdfs:comment "The power whose exercise a trigger waits for." ;
	fnd:utility "Subject: an ins:OnExercise, which the domain lets a reasoner infer (§12). Value: exactly one power. In a regime, a stated power." .

ins:ofObligation a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain ins:OnBreach ;
	rdfs:range ins:Obligation ;
	rdfs:comment "The obligation whose breach a trigger waits for." ;
	fnd:utility "Subject: an ins:OnBreach, which the domain lets a reasoner infer (§12). Value: exactly one obligation. In a regime, a stated obligation." .

ins:by a owl:ObjectProperty ;
	rdfs:range ins:RelationParty ;
	rdfs:comment "A party whose act an act trigger waits for." ;
	fnd:utility "Subject: an ins:OnAct. Value: a party, any number. A regime is stated, so its triggers name roles. Without one, an act of the kind by any party fires the trigger." .

ins:condition a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:range elg:Condition ;
	rdfs:comment "The condition a condition trigger waits for." ;
	fnd:utility "Subject: an ins:OnCondition. Value: exactly one Eligibility condition. The trigger fires when the condition comes to hold. No domain: terms in time may reuse the property (C7b)." .

ins:after a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:range qnt:Quantity ;
	rdfs:comment "The length of an expiry period." ;
	fnd:utility "Subject: an ins:OnExpiry. Value: exactly one quantity of time, counted from entering the state the trigger's transition leaves. A business day or another calendar-dependent unit is a qnt:CalendarUnit (ADR-A94). No domain: terms in time may reuse the property (C7b)." .

ins:tolledIn a owl:ObjectProperty ;
	rdfs:domain ins:OnExpiry ;
	rdfs:range bhv:State ;
	rdfs:comment "A state in which an expiry period does not run." ;
	fnd:utility "Subject: an ins:OnExpiry, which the domain lets a reasoner infer (§12). Value: a state, any number, never of the state space the period runs in. The period's clock stops while the subject is in any of them (C11a-Q2)." .

ins:arisesOn a owl:ObjectProperty ;
	rdfs:range bhv:TriggerDefinition ;
	rdfs:comment "A legal trigger on which a relation arises." ;
	fnd:utility "Subject: a relation. Value: an exercise, breach, act or condition trigger, any number: alternatives. Never an ins:OnExpiry, which counts from entering a state. A relation with none has arisen once its instrument takes effect." .

ins:arisesOnBreachOf a owl:ObjectProperty ;
	rdfs:range ins:Obligation ;
	rdfs:comment "An obligation on whose breach a relation arises." ;
	fnd:utility "Subject: a relation. Value: an obligation, any number: alternatives. Short for ins:arisesOn an ins:OnBreach of it. A stated relation names a stated obligation, a bound relation a bound one." .

ins:arisesOnExerciseOf a owl:ObjectProperty ;
	rdfs:range ins:Power ;
	rdfs:comment "A power on whose exercise a relation arises." ;
	fnd:utility "Subject: a relation. Value: a power, any number: alternatives. Short for ins:arisesOn an ins:OnExercise of it. A stated relation names a stated power, a bound relation a bound one." .

ins:endsOn a owl:ObjectProperty ;
	rdfs:range bhv:TriggerDefinition ;
	rdfs:comment "A legal trigger on which a relation ends." ;
	fnd:utility "Subject: a relation. Value: an exercise, breach, act or condition trigger, any number: alternatives. Never an ins:OnExpiry, which counts from entering a state. A relation with none ends with its instrument." .
```

## 11. Regimes and Gating

### 11.1 A regime is stated once

A relation has two tiers (§6.2): its clause states it once, and instantiation binds it for each
instrument. A regime has one tier. It is stated meaning only (ADR-A104 2026-10-04 addendum,
decision 1):

- it arises under the stated term of the clause that states it, and its states, transitions and
  triggers are shared by every instrument whose wording includes that clause
- each instrument's progress through it is an occupancy of its states, `bhv:forSubject` the
  instrument's persistent identity. The occupancies tell the instruments apart, as a relation's
  bound forms do
- a bound relation gated by the regime names the stated regime's state in `ins:appliesInState`
- a value an instrument supplies, such as a notice length set by a variable, is resolved for that
  instrument at runtime from its assembled wording (C8)

Law I13 reads accordingly: only bound relations are evaluated, and regimes are read as stated, for
each subject.

**Why one tier.** Two facts of Behaviour's model decide it:

- **A state belongs to exactly one state space** (`bhv:inStateSpace` is functional). A bound copy of
  a regime per instrument version would need its own copy of every state and transition, restated in
  full, since RDF has no override.
- **Runtime state belongs to the instrument's persistent identity**, so that a notice period
  survives an amendment that leaves the notice clause alone. With a copy per version, every
  amendment would move every regime's occupancy from one version's states to the next version's,
  even where nothing changed. Stated once, an occupancy moves to new states only when the regime's
  own clause changes, as a new clause version (C9).

```mermaid
flowchart LR
    subgraph CLAUSE["Clause 11.1, stated once"]
        IF["in force"]
        NP["notice period"]
        TM["terminated"]
    end
    A["Fernwood's licence"] -. "occupies, from 1 June" .-> NP
    B["Ashby's licence"] -. "occupies, from 1 March" .-> IF
    C["Moreton's licence"] -. "occupies, from 9 May" .-> TM
    style CLAUSE fill:#BBDEFB
```

**Triggers name stated relations.** A regime's `ins:ofPower` and `ins:ofObligation` name the stated
relation, and fire on the exercise or breach of any bound relation instantiated from it. In the
licence (§16.5) the notice trigger names `tmpl:end-on-notice`, and Corvid's exercise of
`ex:end-on-notice`, the bound power in Fernwood's licence, fires it for that licence: the subject is the
persistent identity of the instrument the bound power's term is bound in. A per-occasion regime
names its stated relation the same way (§11.4). A bound relation's own references, its arising
triggers and what it excepts, name bound relations, since it restates its template in full.

**Examples.** Stating a regime once matters wherever one clause serves many instruments, or one
instrument changes often:

- **A framework agreement with many call-off orders.** The framework's suspension clause applies to
  every order made under it. Its regime has one set of states, and each order's suspension is an
  occupancy for that order. A thousand orders are a thousand subjects, not a thousand copies.
- **A facility amended many times.** A facility is amended to add a lender, extend a date, reset a
  covenant. Its event-of-default regime is untouched by all of these, so a cure period running on
  the day of an amendment simply carries on.
- **Layered insurance cover, an example use-case.** A broker divides a large risk into layers, each
  attaching where the one below is exhausted, and places each with one or more insurers. Before
  anything is accepted, insurers respond with proposals at different levels of commitment, and each
  proposal is checked by the same rules as a contract. The proposals are many: stated once, a
  proposal's regimes are its clauses' regimes, checked once, and running one for a what-if, such as
  how a limit erodes under a claim scenario, means creating occupancies for that proposal as the
  subject. Several insurers may share a layer, a following insurer adding terms of its own for its
  share: those give rise to a regime under the follower's own clause, while the leader's stay
  shared. Endorsements land mid-term and renewals replace the contracts each year, and the
  occupancies stay where they are unless a regime's own clause changes. A proposal's commitment is
  itself legal (a binding quote confers a power of acceptance), while how precise or complete its
  values are is recorded beside its terms, never inside them.

### 11.2 Kinds of regime

**Period regimes** are entered on a trigger and left at a duration from entry or on an end trigger,
whichever comes first. The licence's notice regime (§16.5):

```mermaid
stateDiagram-v2
    state "in force" as InForce
    state "notice period" as NoticePeriod
    state "terminated" as Terminated
    [*] --> InForce
    InForce --> NoticePeriod : OnExercise, the power to end on notice
    NoticePeriod --> Terminated : OnExpiry, 90 days
    InForce --> Terminated : OnExercise, the power to end for breach
    NoticePeriod --> Terminated : OnExercise, the power to end for breach
```

A transition has one source state, so "at any time, for breach" is a transition from each state it
applies in. The facility's cure period (§16.7) is a period regime with a way back, tolled by another
regime:

```mermaid
stateDiagram-v2
    state "performing" as Performing
    state "cure period" as Cure
    state "default" as InDefault
    [*] --> Performing
    Performing --> Cure : OnCondition, leverage above 3.0
    Cure --> Performing : OnCondition, leverage within 3.0
    Cure --> InDefault : OnExpiry, 30 business days, tolled while affected
```

**Switching regimes** move back and forth. The supply agreement (§16.6) has two, on one instrument:
they are separate regimes, drawn together here, each in one state at every moment:

```mermaid
stateDiagram-v2
    state "suspension regime" as SR {
        state "in force" as InForce
        state "suspended" as Suspended
        [*] --> InForce
        InForce --> Suspended : OnExercise, the power to suspend
        Suspended --> InForce : OnExercise, the power to require resumption
    }
    state "force majeure regime" as FR {
        state "unaffected" as Unaffected
        state "affected" as Affected
        [*] --> Unaffected
        Unaffected --> Affected : OnCondition, force majeure prevents performance
        Affected --> Unaffected : OnCondition, it no longer does
    }
```

**Threshold regimes** have states defined by a `qnt:RangeSet` partition of a measured value, each
entered by an `ins:OnCondition` whose condition is an Eligibility interval condition over one range.
The measured value changes with use, such as an aggregate eroded by claims or a usage cap, and is
held by an applied layer's capacity model. No example in this layer runs one:

```mermaid
stateDiagram-v2
    state "within the cap" as Within
    state "over the cap" as Over
    [*] --> Within
    Within --> Over : OnCondition, usage above the cap
    Over --> Within : OnCondition, usage within the cap
```

A static classification of a case, such as whether a site is within the territory, is an
Eligibility decision, not a regime. A regime exists where something switches over time.

### 11.3 Gating

A relation's `ins:appliesInState` values are its **gate** (nested states sketch §6.2):

1. the values are grouped by the top-level regime their states belong to
2. within one regime's group, the relation applies in any of the named states
3. across regimes, it applies only when every group holds
4. a composite state holds while any of its descendants is active

The supply agreement's duty to deliver names one state of each of its two regimes (§16.6):

```mermaid
flowchart LR
    D["duty to deliver"]
    D -- "appliesInState" --> IF["in force<br/>suspension regime"]
    D -- "appliesInState" --> UN["unaffected<br/>force majeure regime"]
    IF --> G1{"suspension group:<br/>in force?"}
    UN --> G2{"force majeure group:<br/>unaffected?"}
    G1 -- "and" --> AP["the duty applies"]
    G2 -- "and" --> AP
```

| Suspension regime | Force majeure regime | The duty to deliver |
|---|---|---|
| in force | unaffected | applies |
| in force | affected | does not apply |
| suspended | unaffected | does not apply |
| suspended | affected | does not apply |

A relation that names two states of one regime applies in either: a power exercisable "while this
agreement is in force or during the notice period" names both. A relation with no
`ins:appliesInState` is not gated. While a relation's gate is closed, the relation does not apply.
How a gated relation is evaluated is C13's.

Regimes never rank one another. A conflict between relations is Instrument's to resolve, through
exceptions and, later, precedence (NRS N10), never Behaviour's. One regime reacts to another only through legal triggers or a guard
that reads the other's state (nested states sketch §6.2).

### 11.4 Whose state gates a relation

A gate reads the occupancy of one subject (C7a-Q5):

- for a regime of the instrument, the relation's own instrument: the persistent identity of the
  instrument its term is bound in
- for a per-occasion regime (`bhv:perOccasionOf`), the occasion the relation's arising chain
  reaches (C11a-Q4)

A **per-occasion regime** runs once for each occasion of a relation: every month's service, every
invoice. It names the stated relation, and covers the occasions of every bound relation
instantiated from it. A relation gated by its state must therefore say which occasion it is about,
and it does so by arising on that relation's breach or exercise. The services agreement (§16.8):
the exclusion of the customer's power to terminate arises on breach of the service obligation, so
for one month's breach its gate reads that month's dispute regime. Where the chain does not reach
exactly one occasion, the gate is Undetermined (ADR-A106 addendum, decision 9). A relation gated by
a per-occasion state that arises on no breach or exercise of the relation is rejected at design
time (§14.2).

```mermaid
flowchart LR
    TX["termination excluded<br/>bound ins:Exclusion"] -- "appliesInState" --> DS["disputed"]
    TX -- "arisesOnBreachOf" --> PS["provide service<br/>bound ins:Obligation"]
    PS -- "boundFrom" --> SPS["provide service<br/>stated"]
    DR["dispute regime"] -- "perOccasionOf" --> SPS
    DS -- "inStateSpace" --> DR
    PS -. "has occasion" .-> MO["March's occasion<br/>breached"]
    MO -. "its dispute occupancy" .-> DS
```

The model is consistent within one legally binding agreement first. A gate whose subject is
something else is held: one participant's share within an agreement, where several parties are each
liable for their own share and each share has its own state, or another agreement altogether, where
one contract responds only once another is exhausted (CCS plan, held design question HQ-2).

### 11.5 Structure and state stay apart (DP6)

`ins:appliesInState` never enters a design-time comparison: authority envelopes, materiality,
overlaps, gaps (ADR-A104 decision 8). A comparison asks what a relation covers over every case, and
a state is a fact about one subject at one time. A state may be a fixed parameter of a comparison
("compare the two licences as they stand during a notice period"), never a variable within one (law
B8, ADR-A106).

The licence shows the separation (§16.5). The licensee's power to grant sub-licences has an
activity and parties, and its scope never mentions the notice period. The notice period's effect is
a separate exclusion, gated by the state. Two versions of the licence compare equal on the power's
terms whatever regime either is in.

```mermaid
flowchart LR
    subgraph STRUCTURE["Structure: compared at design time"]
        PW["grant sub-licences<br/>activity, scope, parties"]
    end
    subgraph STATE["State: read at runtime"]
        EX["sub-licensing excluded"]
        NP["notice period"]
        EX -- "appliesInState" --> NP
    end
    EX -. "excepts" .-> PW
    style STRUCTURE fill:#BBDEFB
    style STATE fill:#bcdee1
```

```turtle-spec
ins:Regime a owl:Class ;
	rdfs:subClassOf bhv:StateSpace ;
	skos:altLabel "Dispensation"@en ;
	rdfs:comment "A state space whose states gate legal relations." ;
	fnd:utility "Subject: a regime, stated meaning only (an ins:Template, C7a-Q1). Arises under exactly one stated term, and is shared by every instrument whose wording includes the term's clause. Each instrument's progress through it is an occupancy for its persistent identity. Its transitions are ins:RegimeTransitions. Assert bhv:StateSpace where no reasoner runs (§12)." .

ins:RegimeTransition a owl:Class ;
	rdfs:subClassOf bhv:TransitionDefinition ,
		[ a owl:Restriction ; owl:onProperty bhv:selectionPolicy ; owl:hasValue bhv:SingleMatch ] ,
		[ a owl:Restriction ; owl:onProperty bhv:activationPolicy ; owl:hasValue bhv:ImmediateActivation ] ;
	rdfs:comment "A transition between a regime's states, on a legal trigger." ;
	fnd:utility "Subject: a transition of a regime. Its triggers are legal triggers. Its selection is bhv:SingleMatch and its activation bhv:ImmediateActivation, fixed: assert bhv:TransitionDefinition and both where no reasoner runs, and an OWL 2 RL reasoner adds them where one does (§12)." .

ins:stateKind a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:range skos:Concept ;
	rdfs:comment "What kind of state a regime's state is." ;
	fnd:utility "Subject: a state of a regime. Value: at most one concept from the scheme bound to ins-voc:StateKindContract. For readers and reports: the evaluator never reads it." .

ins:appliesInState a owl:ObjectProperty ;
	rdfs:range bhv:State ;
	rdfs:comment "A state a relation applies in." ;
	fnd:utility "Subject: a relation. Value: a state of an ins:Regime, any number. Grouped by top-level regime: within one, any named state admits the relation, and across regimes every group must. A composite state holds while any descendant does. Read for the relation's own instrument, or for the occasion its arising chain reaches (§11.4). Never part of a design-time comparison (DP6)." .
```

## 12. Authoring With and Without a Reasoner

Behaviour's engine reads only Behaviour's terms: a `bhv:StateSpace`, a `bhv:TransitionDefinition`
with its `bhv:selectionPolicy` and `bhv:activationPolicy`, a `bhv:TriggerDefinition` with its
`bhv:triggerKind`. Every Instrument specialisation fixes some of these. A regime is always a state
space, a regime transition always selects one match and activates at once, and each legal trigger
always has the same kind. Because a regime is stated once and never instantiated, no instantiation
step can add them, so they come from one of two places (ADR-A104 2026-10-04 addendum, decision 5).

### 12.1 Asserted: the baseline

Data read without a reasoner states every Behaviour term beside its Instrument term. Every example
in this layer is written this way, and so is every library template, so that both kinds of consumer
can use it:

```turtle-example
tmpl:notice-regime a ins:Regime , bhv:StateSpace , ins:Template ;
    fnd:hasIdentity tmpl:notice-regime-identity ;
    ins:arisesUnder tmpl:term-11-1 ;
    bhv:initialState tmpl:in-force .

tmpl:on-notice-given a ins:OnExercise , bhv:TriggerDefinition ;
    bhv:triggerKind bhv:ExternalStimulus ;
    ins:ofPower tmpl:end-on-notice .

tmpl:give-notice a ins:RegimeTransition , bhv:TransitionDefinition ;
    bhv:fromState tmpl:in-force ; bhv:toState tmpl:notice-period ;
    bhv:hasTrigger tmpl:on-notice-given ;
    bhv:selectionPolicy bhv:SingleMatch ; bhv:activationPolicy bhv:ImmediateActivation .
```

The explicit `bhv:` type is law B4, and a shape requires it (§14.1). The engine matches
`rdf:type bhv:TransitionDefinition` as written, and a node typed only `ins:RegimeTransition` would
be invisible to it. Shapes alone do not show the gap. SHACL's `sh:targetClass` and `sh:class` follow
the `rdfs:subClassOf` triples in the data graph: validated with this spec, as §14.1 asks, a node
typed only `ins:RegimeTransition` is selected by Behaviour's shapes, and its missing policies are
reported. Validated without it, Behaviour's shapes never select the node. So the B4 shapes check
the `rdf:type` triple itself (`sh:path rdf:type ; sh:hasValue`), which no subclass axiom
satisfies.

### 12.2 Entailed: the convenience

An author working with an OWL 2 RL reasoner, or a more expressive one, may write the Instrument
terms alone, and let the reasoner add Behaviour's:

```turtle-example
tmpl:notice-regime a ins:Regime , ins:Template ;
    fnd:hasIdentity tmpl:notice-regime-identity ;
    ins:arisesUnder tmpl:term-11-1 ;
    bhv:initialState tmpl:in-force .

tmpl:on-notice-given ins:ofPower tmpl:end-on-notice .

tmpl:give-notice a ins:RegimeTransition ;
    bhv:fromState tmpl:in-force ; bhv:toState tmpl:notice-period ;
    bhv:hasTrigger tmpl:on-notice-given .
```

The axioms that make this work are on the Instrument classes and properties (§10, §11):

| Term | Axiom | What a reasoner adds, and by which OWL 2 RL rule |
|---|---|---|
| `ins:Regime` | `rdfs:subClassOf bhv:StateSpace` | `bhv:StateSpace` (cax-sco) |
| `ins:RegimeTransition` | `rdfs:subClassOf bhv:TransitionDefinition`, `owl:hasValue bhv:SingleMatch` on `bhv:selectionPolicy`, `owl:hasValue bhv:ImmediateActivation` on `bhv:activationPolicy` | the type (cax-sco), both policies (cls-hv1) |
| `ins:OnExercise`, `ins:OnAct` | `rdfs:subClassOf bhv:TriggerDefinition`, `owl:hasValue bhv:ExternalStimulus` on `bhv:triggerKind` | the type, the kind |
| `ins:OnBreach`, `ins:OnCondition` | the same, with `bhv:DerivedTrigger` | the type, the kind |
| `ins:OnExpiry` | the same, with `bhv:ScheduledTrigger` | the type, the kind |
| `ins:ofPower` | `rdfs:domain ins:OnExercise` | the trigger's class (prp-dom), and from it the type and the kind |
| `ins:ofObligation` | `rdfs:domain ins:OnBreach` | the same |
| `ins:tolledIn` | `rdfs:domain ins:OnExpiry` | the same |

Three points of OWL decide the shape of these axioms:

- **`owl:hasValue`, not `owl:allValuesFrom`.** An `owl:allValuesFrom` restriction only constrains a
  value already stated: it says what the value must be, if there is one. An `owl:hasValue`
  restriction in a superclass says the value is there, so a reasoner adds it to every member of the
  class.
- **OWL 2 RL, not RDFS.** RDFS inference follows `rdfs:subClassOf` and `rdfs:domain`, so it adds the
  `bhv:` types, but it does not read restrictions, so it adds no policy and no kind. OWL 2 RL, the
  rule-based profile, does (rule cls-hv1). pySHACL's `inference="owlrl"` closes the graph under OWL
  2 RL before it validates.
- **Domains only where every subject is that class.** `ins:ofPower`, `ins:ofObligation` and
  `ins:tolledIn` are used by one trigger class each, so a domain infers nothing false. `ins:condition`
  and `ins:after` have no domain, because terms in time (C7b) may reuse them on other subjects.

### 12.3 Validate the graph the engine reads

```mermaid
flowchart TB
    A["authored data"] --> Q{"a reasoner<br/>at design time?"}
    Q -- "no" --> V1["validate the asserted graph<br/>with every layer's shapes"]
    Q -- "yes, OWL 2 RL or more" --> C["close the graph"]
    C --> V2["validate the closed graph<br/>with every layer's shapes"]
    V1 --> E1["the engine reads<br/>the asserted graph"]
    V2 --> E2["the engine reads<br/>the closed graph"]
```

Without a reasoner, the engine reads the asserted graph, and the shapes validate it: B4's shape
rejects a regime node that lacks its `bhv:` type. With one, the engine reads the closed graph, and
the shapes validate that: B4 holds there, because the reasoner added the types. The lean form above
fails B4 on its asserted graph, and passes every shape on its closed graph.

### 12.4 A wrong stated value

`bhv:selectionPolicy`, `bhv:activationPolicy` and `bhv:triggerKind` are functional, and Behaviour
does not declare its policy and kind individuals distinct. An author who states `bhv:selectionPolicy
bhv:AllMatches` on a regime transition, with a reasoner running, leads it to conclude that
`bhv:AllMatches` and `bhv:SingleMatch` are one individual (`owl:sameAs`). After that, every
transition in the graph has both values, and the error shows everywhere but where it was made.

Two measures meet it:

- **Instrument's value shapes** list the one permitted value with `sh:in`: `sh:in ( bhv:SingleMatch
  )` on a regime transition's selection, and so on for activation and each trigger kind (§14.1). On
  the asserted graph they report a wrong value at the node that states it, in either mode, and let
  a value the reasoner will add be absent. On the closed graph they report the wrong value at every
  node the merge reached.
- **Distinct individuals in Behaviour.** `owl:AllDifferent` over the policies and the kinds would let
  a reasoner report the merge as an inconsistency, at the triple that caused it. It is a change to
  Behaviour's vocabulary, held as follow-up FU-C7a-a (CCS plan) and TD-17.

`sh:hasValue` is not used for the fixed values, because it fails both modes:

| Case | `sh:hasValue bhv:SingleMatch` | `sh:in ( bhv:SingleMatch )` |
|---|---|---|
| correct lean data, asserted graph | rejected: the value is not yet there | passes |
| correct lean data, closed graph | passes | passes |
| a wrong stated value, asserted graph | reported at that transition | reported at that transition |
| a wrong stated value, closed graph | missed: the merge also supplies `bhv:SingleMatch` | reported at every regime transition |

A value's presence is checked by the minimum counts, Behaviour's for the two policies and
Instrument's for each trigger's kind, on the graph the engine reads.

## 13. Vocabulary

The activity scheme follows Wording's element types (C3-Q1): `ins-voc:ActivityContract` constrains
`ins:activity`, with a baseline scheme bound as fallback that a deployment may extend or replace.
The location contract has no baseline: a deployment binds its own territory or site scheme. The
state kind scheme follows the activity scheme: `ins-voc:StateKindContract` constrains
`ins:stateKind`, with a baseline of the kinds the examples use. `ins-voc:Suspended` is a kind of
regime state, the state of an instrument whose performance is suspended, and is distinct from
Behaviour's core occasion state `bhv:Suspended`.

```turtle-vocab
@prefix ins:     <https://www.nebularis.org/neuro-semantic/lattice/instrument#> .
@prefix ins-voc: <https://www.nebularis.org/neuro-semantic/lattice/instrument/vocab#> .
@prefix bhv:     <https://www.nebularis.org/neuro-semantic/lattice/behaviour#> .
@prefix fnd:     <https://www.nebularis.org/neuro-semantic/lattice/foundation#> .
@prefix voc:     <https://www.nebularis.org/neuro-semantic/lattice/vocabulary#> .
@prefix skos:    <http://www.w3.org/2004/02/skos/core#> .
@prefix owl:     <http://www.w3.org/2002/07/owl#> .
@prefix rdf:     <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs:    <http://www.w3.org/2000/01/rdf-schema#> .

<https://www.nebularis.org/neuro-semantic/instrument-vocab>
	rdf:type owl:Ontology ;
	owl:versionIRI <https://www.nebularis.org/neuro-semantic/lattice/instrument-vocab/0.10.0> ;
	owl:imports <https://www.nebularis.org/neuro-semantic/lattice/instrument/0.10.0> .

ins-voc:ActivityContract a voc:SchemeContract ;
	fnd:hasIdentity ins-voc:ActivityContract-identity ;
	fnd:hasGovernanceState fnd:Active ;
	skos:prefLabel "Activity scheme contract"@en ;
	voc:constrainsProperty ins:activity ;
	voc:boundScheme ins-voc:Activities .

ins-voc:LocationContract a voc:SchemeContract ;
	fnd:hasIdentity ins-voc:LocationContract-identity ;
	fnd:hasGovernanceState fnd:Active ;
	skos:prefLabel "Location scheme contract"@en ;
	voc:constrainsProperty ins:operatesAt .

ins-voc:Activities a voc:ConceptScheme ;
	fnd:hasIdentity ins-voc:Activities-identity ;
	fnd:hasGovernanceState fnd:Active ;
	skos:prefLabel "Baseline activities"@en ;
	skos:definition "Acts a relation may be about. A baseline, not a closed set. Each names the act, never the circumstances of it."@en .

ins-voc:Repay a skos:Concept ; skos:inScheme ins-voc:Activities ;
	skos:prefLabel "Repay"@en ; skos:definition "Pay back money lent."@en .

ins-voc:CreateSecurity a skos:Concept ; skos:inScheme ins-voc:Activities ;
	skos:prefLabel "Create security"@en ; skos:definition "Grant a security interest over an asset."@en .

ins-voc:DeclareDue a skos:Concept ; skos:inScheme ins-voc:Activities ;
	skos:prefLabel "Declare due"@en ; skos:definition "Declare amounts immediately due and payable."@en .

ins-voc:ReportAdverseEvent a skos:Concept ; skos:inScheme ins-voc:Activities ;
	skos:prefLabel "Report adverse event"@en ; skos:definition "Report an adverse event to another party."@en .

ins-voc:Enrol a skos:Concept ; skos:inScheme ins-voc:Activities ;
	skos:prefLabel "Enrol"@en ; skos:definition "Admit a participant to a programme or study."@en .

ins-voc:EndParticipation a skos:Concept ; skos:inScheme ins-voc:Activities ;
	skos:prefLabel "End participation"@en ; skos:definition "End another party's participation in an arrangement."@en .

ins-voc:Repair a skos:Concept ; skos:inScheme ins-voc:Activities ;
	skos:prefLabel "Repair"@en ; skos:definition "Restore a product to working order."@en .

ins-voc:Terminate a skos:Concept ; skos:inScheme ins-voc:Activities ;
	skos:prefLabel "Terminate"@en ; skos:definition "End an instrument or a relationship under it."@en .

ins-voc:GrantSublicence a skos:Concept ; skos:inScheme ins-voc:Activities ;
	skos:prefLabel "Grant sub-licence"@en ; skos:definition "Grant another party a licence of rights held under a licence."@en .

ins-voc:Deliver a skos:Concept ; skos:inScheme ins-voc:Activities ;
	skos:prefLabel "Deliver"@en ; skos:definition "Hand over goods to another party."@en .

ins-voc:Suspend a skos:Concept ; skos:inScheme ins-voc:Activities ;
	skos:prefLabel "Suspend"@en ; skos:definition "Stop performing under an instrument for a time, without ending it."@en .

ins-voc:Reinstate a skos:Concept ; skos:inScheme ins-voc:Activities ;
	skos:prefLabel "Reinstate"@en ; skos:definition "Restore performance that has been suspended."@en .

ins-voc:ProvideService a skos:Concept ; skos:inScheme ins-voc:Activities ;
	skos:prefLabel "Provide service"@en ; skos:definition "Make a service available to another party."@en .

ins-voc:Dispute a skos:Concept ; skos:inScheme ins-voc:Activities ;
	skos:prefLabel "Dispute"@en ; skos:definition "Contest a claim, report or assertion another party has made."@en .

ins:InstrumentTarget a bhv:TargetKind ;
	rdfs:comment "A Behaviour effect's target kind for an instrument." ;
	fnd:utility "Declared here, since Behaviour no longer names Instrument (ADR-A106). Behaviour's bhv:InstrumentTarget is deprecated in its favour." .
```

The state kinds:

```turtle-vocab
ins-voc:StateKindContract a voc:SchemeContract ;
	fnd:hasIdentity ins-voc:StateKindContract-identity ;
	fnd:hasGovernanceState fnd:Active ;
	skos:prefLabel "State kind scheme contract"@en ;
	voc:constrainsProperty ins:stateKind ;
	voc:boundScheme ins-voc:StateKinds .

ins-voc:StateKinds a voc:ConceptScheme ;
	fnd:hasIdentity ins-voc:StateKinds-identity ;
	fnd:hasGovernanceState fnd:Active ;
	skos:prefLabel "Baseline state kinds"@en ;
	skos:definition "Kinds of state a regime's state may be. A baseline, not a closed set: a deployment adds kinds without a release of this layer."@en .

ins-voc:InForce a skos:Concept ; skos:inScheme ins-voc:StateKinds ;
	skos:prefLabel "In force"@en ; skos:definition "The instrument is in force and performed in the ordinary course."@en .

ins-voc:NoticePeriod a skos:Concept ; skos:inScheme ins-voc:StateKinds ;
	skos:prefLabel "Notice period"@en ; skos:definition "Notice has been given and is running."@en .

ins-voc:CurePeriod a skos:Concept ; skos:inScheme ins-voc:StateKinds ;
	skos:prefLabel "Cure period"@en ; skos:definition "A breach or a failed test may still be remedied before it has its consequence."@en .

ins-voc:Default a skos:Concept ; skos:inScheme ins-voc:StateKinds ;
	skos:prefLabel "Default"@en ; skos:definition "An event of default has occurred and is continuing."@en .

ins-voc:Suspended a skos:Concept ; skos:inScheme ins-voc:StateKinds ;
	skos:prefLabel "Suspended"@en ; skos:definition "Performance under the instrument is suspended. A regime's state, not Behaviour's core occasion state bhv:Suspended."@en .

ins-voc:ForceMajeure a skos:Concept ; skos:inScheme ins-voc:StateKinds ;
	skos:prefLabel "Force majeure"@en ; skos:definition "An event beyond a party's control prevents it from performing."@en .

ins-voc:Disputed a skos:Concept ; skos:inScheme ins-voc:StateKinds ;
	skos:prefLabel "Disputed"@en ; skos:definition "A claim, report or assertion has been disputed, and the dispute is not settled."@en .

ins-voc:Terminated a skos:Concept ; skos:inScheme ins-voc:StateKinds ;
	skos:prefLabel "Terminated"@en ; skos:definition "The instrument, or the arrangement the regime governs, has ended."@en .
```

## 14. Shapes

### 14.1 Structural shapes (SHACL Core)

Each property's subject and value, a relation's single term, its required content per class, the
two tiers (law I2) and what each names (law I13). For regimes: a regime's term, its explicit
Behaviour types (law B4), each trigger's one required value, the fixed values of §12 as `sh:in`
shapes, and what may be gated or arise. Validate data with this spec, so that subclasses are known,
and validate the graph the engine reads (§12.3).

```turtle-shapes
@prefix sh:   <http://www.w3.org/ns/shacl#> .
@prefix ins:  <https://www.nebularis.org/neuro-semantic/lattice/instrument#> .
@prefix fnd:  <https://www.nebularis.org/neuro-semantic/lattice/foundation#> .
@prefix pty:  <https://www.nebularis.org/neuro-semantic/lattice/party#> .
@prefix elg:  <https://www.nebularis.org/neuro-semantic/lattice/eligibility#> .
@prefix wrd:  <https://www.nebularis.org/neuro-semantic/lattice/wording#> .
@prefix bhv:  <https://www.nebularis.org/neuro-semantic/lattice/behaviour#> .
@prefix qnt:  <https://www.nebularis.org/neuro-semantic/lattice/quantification#> .
@prefix rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .

ins:InstrumentShape a sh:NodeShape ;
	sh:targetClass ins:Instrument ;
	sh:property [
		sh:path ins:expressedIn ; sh:minCount 1 ; sh:maxCount 1 ; sh:class wrd:AssembledWording ;
		sh:message "An instrument version is expressed in exactly one assembled wording (law I1)."
	] ;
	sh:property [
		sh:path ins:party ; sh:or ( [ sh:class pty:RoleOccupancy ] [ sh:class pty:ParticipationGroup ] ) ;
		sh:message "An instrument's parties are role occupancies or participation groups, never roles."
	] .

ins:TermShape a sh:NodeShape ;
	sh:targetClass ins:Term ;
	sh:message "A term is either stated, an ins:Template expressed in exactly one element version and bound in none, or bound, bound in exactly one instrument version from exactly one stated term or implied by a source, and expressed in none (law I2)." ;
	sh:xone (
		[ sh:class ins:Template ;
		  sh:property [ sh:path ins:expressedIn ; sh:minCount 1 ; sh:maxCount 1 ; sh:class wrd:Element ] ;
		  sh:property [ sh:path ins:boundIn ; sh:maxCount 0 ] ]
		[ sh:not [ sh:class ins:Template ] ;
		  sh:property [ sh:path ins:boundIn ; sh:minCount 1 ; sh:maxCount 1 ; sh:class ins:Instrument ] ;
		  sh:property [ sh:path ins:expressedIn ; sh:maxCount 0 ] ;
		  sh:xone (
			[ sh:property [ sh:path ins:boundFrom ; sh:minCount 1 ; sh:maxCount 1 ; sh:class ins:Template ] ]
			[ sh:property [ sh:path ins:impliedBy ; sh:minCount 1 ] ]
		  ) ]
	) .

ins:LegalRelationShape a sh:NodeShape ;
	sh:targetClass ins:LegalRelation ;
	sh:property [
		sh:path ins:arisesUnder ; sh:minCount 1 ; sh:maxCount 1 ; sh:class ins:Term ;
		sh:message "A relation arises under exactly one term."
	] ;
	sh:property [
		sh:path ins:boundIn ; sh:maxCount 0 ;
		sh:message "A relation carries no ins:boundIn: it belongs to its term, which does (law I2)."
	] ;
	sh:property [
		sh:path ins:scope ; sh:maxCount 1 ; sh:class elg:Condition ;
		sh:message "A relation has at most one scope, an Eligibility condition."
	] ;
	sh:property [
		sh:path ins:activity ; sh:maxCount 1 ; sh:nodeKind sh:IRI ;
		sh:message "A relation has at most one activity, a concept."
	] ;
	sh:not [ sh:class fnd:Version ] ;
	sh:message "A relation is never a version: it changes only with its owner (law I18)." .

ins:RelationTierShape a sh:NodeShape ;
	sh:targetClass ins:LegalRelation ;
	sh:message "A stated relation (an ins:Template) arises under a stated term and names roles as its parties. A bound relation arises under a bound term, names occupancies or groups, and is instantiated from exactly one stated relation or implied by a source (laws I2, I13)." ;
	sh:xone (
		[ sh:class ins:Template ;
		  sh:property [ sh:path ins:arisesUnder ; sh:class ins:Template ] ;
		  sh:property [ sh:path [ sh:alternativePath ( ins:obligor ins:obligee ins:holder ins:counterparty ) ] ; sh:class pty:Role ] ]
		[ sh:not [ sh:class ins:Template ] ;
		  sh:property [ sh:path ins:arisesUnder ; sh:not [ sh:class ins:Template ] ] ;
		  sh:property [ sh:path [ sh:alternativePath ( ins:obligor ins:obligee ins:holder ins:counterparty ) ] ;
		                sh:or ( [ sh:class pty:RoleOccupancy ] [ sh:class pty:ParticipationGroup ] ) ] ;
		  sh:xone (
			[ sh:property [ sh:path ins:boundFrom ; sh:minCount 1 ; sh:maxCount 1 ; sh:class ins:Template ] ]
			[ sh:property [ sh:path ins:impliedBy ; sh:minCount 1 ] ]
		  ) ]
	) .

ins:ObligationShape a sh:NodeShape ;
	sh:targetClass ins:Obligation ;
	sh:property [ sh:path ins:obligor ; sh:minCount 1 ; sh:maxCount 1 ;
		sh:message "An obligation has exactly one obligor. Several owing together are a participation group." ] ;
	sh:property [ sh:path ins:obligee ; sh:minCount 1 ;
		sh:message "An obligation is owed to at least one obligee." ] ;
	sh:property [ sh:path ins:excepts ; sh:maxCount 0 ;
		sh:message "An obligation excepts nothing: only a permission or an exclusion does." ] ;
	sh:or (
		[ sh:class ins:ContinuingObligation ]
		[ sh:property [ sh:path ins:activity ; sh:minCount 1 ] ]
	) ;
	sh:message "An obligation that is not continuing states its activity." .

ins:ContinuingObligationShape a sh:NodeShape ;
	sh:targetClass ins:ContinuingObligation ;
	sh:property [ sh:path ins:maintains ; sh:minCount 1 ; sh:maxCount 1 ; sh:class elg:Condition ;
		sh:message "A continuing obligation states the one condition it keeps holding (ins:maintains)." ] .

ins:HeldRelationShape a sh:NodeShape ;
	sh:targetClass ins:Permission , ins:Exclusion , ins:Power ;
	sh:property [ sh:path ins:holder ; sh:minCount 1 ; sh:maxCount 1 ;
		sh:message "A permission, exclusion or power has exactly one holder. Several holding together are a participation group." ] ;
	sh:property [ sh:path ins:counterparty ; sh:minCount 1 ;
		sh:message "A permission, exclusion or power has at least one counterparty." ] ;
	sh:property [ sh:path ins:obligor ; sh:maxCount 0 ; sh:message "Only an obligation has an obligor." ] ;
	sh:property [ sh:path ins:obligee ; sh:maxCount 0 ; sh:message "Only an obligation has obligees." ] .

ins:PermissionShape a sh:NodeShape ;
	sh:targetClass ins:Permission ;
	sh:property [ sh:path ins:activity ; sh:minCount 1 ;
		sh:message "A permission states the activity it permits." ] ;
	sh:property [ sh:path ins:excepts ; sh:minCount 1 ; sh:maxCount 1 ; sh:class ins:Prohibition ;
		sh:message "A permission excepts exactly one prohibition." ] .

ins:ExclusionShape a sh:NodeShape ;
	sh:targetClass ins:Exclusion ;
	sh:property [ sh:path ins:excepts ; sh:minCount 1 ; sh:maxCount 1 ;
		sh:or ( [ sh:class ins:Obligation ] [ sh:class ins:Power ] ) ;
		sh:message "An exclusion excepts exactly one obligation or power." ] .

ins:PowerShape a sh:NodeShape ;
	sh:targetClass ins:Power ;
	sh:property [ sh:path ins:activity ; sh:minCount 1 ;
		sh:message "A power states the act that exercises it." ] ;
	sh:property [ sh:path ins:excepts ; sh:maxCount 0 ;
		sh:message "A power excepts nothing: only a permission or an exclusion does." ] .

ins:QualifierShape a sh:NodeShape ;
	sh:targetClass ins:Qualifier ;
	sh:property [ sh:path ins:arisesUnder ; sh:minCount 1 ; sh:maxCount 1 ; sh:class ins:Term ;
		sh:message "A qualifier arises under exactly one term." ] ;
	sh:property [ sh:path ins:qualifies ; sh:minCount 1 ; sh:maxCount 1 ;
		sh:or ( [ sh:class ins:Term ] [ sh:class ins:LegalRelation ] ) ;
		sh:message "A qualifier qualifies exactly one term or relation." ] .

ins:PartyDetailsShape a sh:NodeShape ;
	sh:targetSubjectsOf ins:noticeAddress , ins:operatesAt ;
	sh:class pty:RoleOccupancy ;
	sh:property [ sh:path ins:noticeAddress ; sh:datatype xsd:string ;
		sh:message "A notice address is a string, the address as written." ] ;
	sh:property [ sh:path ins:operatesAt ; sh:nodeKind sh:IRI ;
		sh:message "An operating location is a concept from the bound location scheme." ] ;
	sh:message "Party details belong to a role occupancy." .

ins:RegimeShape a sh:NodeShape ;
	sh:targetClass ins:Regime ;
	sh:class ins:Template ;
	sh:message "A regime is stated meaning only, an ins:Template: it is stated once and read for each subject (C7a-Q1)." ;
	sh:property [ sh:path ins:arisesUnder ; sh:minCount 1 ; sh:maxCount 1 ; sh:class ins:Term ;
		sh:message "A regime arises under exactly one term." ] ;
	sh:property [ sh:path ins:arisesUnder ; sh:class ins:Template ;
		sh:message "A regime arises under a stated term (C7a-Q1)." ] ;
	sh:property [ sh:path ins:boundFrom ; sh:maxCount 0 ;
		sh:message "A regime is never bound: it is stated once and read for each subject (law I13)." ] .

# Law B4 is about the triple the engine reads, so these shapes check rdf:type
# itself. sh:class would follow ins:Regime's rdfs:subClassOf in the data graph
# and pass without the triple (§12.1).
ins:RegimeTypeShape a sh:NodeShape ;
	sh:targetClass ins:Regime ;
	sh:property [ sh:path rdf:type ; sh:hasValue bhv:StateSpace ;
		sh:message "A regime is also typed bhv:StateSpace in the graph the engine reads: assert it where no reasoner runs (law B4, §12)." ] .

ins:RegimeTransitionShape a sh:NodeShape ;
	sh:targetClass ins:RegimeTransition ;
	sh:property [ sh:path bhv:hasTrigger ;
		sh:or ( [ sh:class ins:OnExercise ] [ sh:class ins:OnBreach ] [ sh:class ins:OnAct ] [ sh:class ins:OnCondition ] [ sh:class ins:OnExpiry ] ) ;
		sh:message "A regime transition's triggers are legal triggers." ] ;
	sh:property [ sh:path bhv:selectionPolicy ; sh:in ( bhv:SingleMatch ) ;
		sh:message "A regime transition's selection policy is bhv:SingleMatch, fixed (ADR-A104 decision 7). A reasoner adds it where none is stated (§12)." ] ;
	sh:property [ sh:path bhv:activationPolicy ; sh:in ( bhv:ImmediateActivation ) ;
		sh:message "A regime transition's activation policy is bhv:ImmediateActivation, fixed (ADR-A104 decision 7). A reasoner adds it where none is stated (§12)." ] .

ins:RegimeTransitionTypeShape a sh:NodeShape ;
	sh:targetClass ins:RegimeTransition ;
	sh:property [ sh:path rdf:type ; sh:hasValue bhv:TransitionDefinition ;
		sh:message "A regime transition is also typed bhv:TransitionDefinition in the graph the engine reads: assert it where no reasoner runs (law B4, §12)." ] .

ins:LegalTriggerTypeShape a sh:NodeShape ;
	sh:targetClass ins:OnExercise , ins:OnBreach , ins:OnAct , ins:OnCondition , ins:OnExpiry ;
	sh:property [ sh:path rdf:type ; sh:hasValue bhv:TriggerDefinition ;
		sh:message "A legal trigger is also typed bhv:TriggerDefinition in the graph the engine reads: assert it where no reasoner runs (law B4, §12)." ] .

ins:OnExerciseShape a sh:NodeShape ;
	sh:targetClass ins:OnExercise ;
	sh:property [ sh:path ins:ofPower ; sh:minCount 1 ; sh:maxCount 1 ; sh:class ins:Power ;
		sh:message "An exercise trigger names exactly one power (ins:ofPower)." ] ;
	sh:property [ sh:path bhv:triggerKind ; sh:minCount 1 ; sh:in ( bhv:ExternalStimulus ) ;
		sh:message "An exercise trigger's kind is bhv:ExternalStimulus, fixed. Assert it where no reasoner runs (§12)." ] .

ins:OnBreachShape a sh:NodeShape ;
	sh:targetClass ins:OnBreach ;
	sh:property [ sh:path ins:ofObligation ; sh:minCount 1 ; sh:maxCount 1 ; sh:class ins:Obligation ;
		sh:message "A breach trigger names exactly one obligation (ins:ofObligation)." ] ;
	sh:property [ sh:path bhv:triggerKind ; sh:minCount 1 ; sh:in ( bhv:DerivedTrigger ) ;
		sh:message "A breach trigger's kind is bhv:DerivedTrigger, fixed. Assert it where no reasoner runs (§12)." ] .

ins:OnActShape a sh:NodeShape ;
	sh:targetClass ins:OnAct ;
	sh:property [ sh:path ins:activity ; sh:minCount 1 ; sh:maxCount 1 ; sh:nodeKind sh:IRI ;
		sh:message "An act trigger names exactly one act (ins:activity), a concept." ] ;
	sh:property [ sh:path ins:by ;
		sh:or ( [ sh:class pty:Role ] [ sh:class pty:RoleOccupancy ] [ sh:class pty:ParticipationGroup ] ) ;
		sh:message "An act trigger's ins:by names parties." ] ;
	sh:property [ sh:path bhv:triggerKind ; sh:minCount 1 ; sh:in ( bhv:ExternalStimulus ) ;
		sh:message "An act trigger's kind is bhv:ExternalStimulus, fixed. Assert it where no reasoner runs (§12)." ] .

ins:OnConditionShape a sh:NodeShape ;
	sh:targetClass ins:OnCondition ;
	sh:property [ sh:path ins:condition ; sh:minCount 1 ; sh:maxCount 1 ; sh:class elg:Condition ;
		sh:message "A condition trigger names exactly one Eligibility condition (ins:condition)." ] ;
	sh:property [ sh:path bhv:triggerKind ; sh:minCount 1 ; sh:in ( bhv:DerivedTrigger ) ;
		sh:message "A condition trigger's kind is bhv:DerivedTrigger, fixed. Assert it where no reasoner runs (§12)." ] .

ins:OnExpiryShape a sh:NodeShape ;
	sh:targetClass ins:OnExpiry ;
	sh:property [ sh:path ins:after ; sh:minCount 1 ; sh:maxCount 1 ; sh:class qnt:Quantity ;
		sh:message "An expiry trigger states exactly one length (ins:after), a quantity of time." ] ;
	sh:property [ sh:path ins:tolledIn ; sh:class bhv:State ;
		sh:message "An expiry period is tolled in states." ] ;
	sh:property [ sh:path bhv:triggerKind ; sh:minCount 1 ; sh:in ( bhv:ScheduledTrigger ) ;
		sh:message "An expiry trigger's kind is bhv:ScheduledTrigger, fixed. Assert it where no reasoner runs (§12)." ] .

ins:StateKindShape a sh:NodeShape ;
	sh:targetSubjectsOf ins:stateKind ;
	sh:class bhv:State ;
	sh:message "Only a state has a state kind." ;
	sh:property [ sh:path ins:stateKind ; sh:maxCount 1 ; sh:nodeKind sh:IRI ;
		sh:message "A state has at most one kind, a concept." ] .

ins:GatedRelationShape a sh:NodeShape ;
	sh:targetSubjectsOf ins:appliesInState ;
	sh:class ins:LegalRelation ;
	sh:message "Only a legal relation is gated by a state (ins:appliesInState)." ;
	sh:property [ sh:path ins:appliesInState ; sh:class bhv:State ;
		sh:message "A relation is gated by states." ] .

ins:ArisingShape a sh:NodeShape ;
	sh:targetSubjectsOf ins:arisesOn , ins:endsOn , ins:arisesOnBreachOf , ins:arisesOnExerciseOf ;
	sh:class ins:LegalRelation ;
	sh:message "Only a legal relation arises or ends on a trigger." ;
	sh:property [ sh:path [ sh:alternativePath ( ins:arisesOn ins:endsOn ) ] ;
		sh:or ( [ sh:class ins:OnExercise ] [ sh:class ins:OnBreach ] [ sh:class ins:OnAct ] [ sh:class ins:OnCondition ] ) ;
		sh:message "A relation arises or ends on an exercise, a breach, an act or a condition. An expiry counts from entering a state, so it moves only regimes: a relation's own periods are due ranges (C7b)." ] ;
	sh:property [ sh:path ins:arisesOnBreachOf ; sh:class ins:Obligation ;
		sh:message "A relation arises on the breach of an obligation." ] ;
	sh:property [ sh:path ins:arisesOnExerciseOf ; sh:class ins:Power ;
		sh:message "A relation arises on the exercise of a power." ] .

ins:ArisingTierShape a sh:NodeShape ;
	sh:targetClass ins:LegalRelation ;
	sh:message "A stated relation arises on the breach or exercise of stated relations, and a bound relation of bound ones (ADR-A104 2026-10-04 addendum, decision 3)." ;
	sh:or (
		[ sh:class ins:Template ;
		  sh:property [ sh:path [ sh:alternativePath ( ins:arisesOnBreachOf ins:arisesOnExerciseOf ) ] ; sh:class ins:Template ] ]
		[ sh:not [ sh:class ins:Template ] ;
		  sh:property [ sh:path [ sh:alternativePath ( ins:arisesOnBreachOf ins:arisesOnExerciseOf ) ] ; sh:not [ sh:class ins:Template ] ] ]
	) .
```

### 14.2 Constraint shapes (SHACL-SPARQL)

Supersession within one identity, and law I8: an exception's holder is the party the excepted
relation binds, and a permission permits the act the prohibition forbids. For regimes: every
transition between a regime's states is a regime transition, a gate names a state of a regime, a
gate on a per-occasion regime reaches its occasion (C11a-Q4), and a period is never tolled by a
state of its own state space.

```turtle-shapes
@prefix sh:   <http://www.w3.org/ns/shacl#> .
@prefix ins:  <https://www.nebularis.org/neuro-semantic/lattice/instrument#> .

ins:SupersessionSameIdentityShape a sh:NodeShape ;
	sh:targetClass ins:Instrument ;
	sh:sparql [
		sh:message "An instrument version is superseded only by a version of the same instrument: fnd:supersededBy points to a version with another fnd:hasIdentity." ;
		sh:select """
			PREFIX fnd: <https://www.nebularis.org/neuro-semantic/lattice/foundation#>
			SELECT $this WHERE {
				$this fnd:hasIdentity ?identity ;
					  fnd:supersededBy ?next .
				?next fnd:hasIdentity ?other .
				FILTER (?identity != ?other)
			}
		"""
	] .

ins:PermissionExceptsOwnProhibitionShape a sh:NodeShape ;
	sh:targetClass ins:Permission ;
	sh:sparql [
		sh:message "The permission's holder {?holder} is not the obligor of the prohibition it excepts, {?prohibition} (law I8)." ;
		sh:select """
			PREFIX ins: <https://www.nebularis.org/neuro-semantic/lattice/instrument#>
			SELECT $this ?holder ?prohibition WHERE {
				$this ins:excepts ?prohibition ;
					  ins:holder ?holder .
				FILTER NOT EXISTS { ?prohibition ins:obligor ?holder }
			}
		"""
	] ;
	sh:sparql [
		sh:message "The permission's activity {?activity} is not the activity of the prohibition it excepts, {?prohibition} (law I8)." ;
		sh:select """
			PREFIX ins: <https://www.nebularis.org/neuro-semantic/lattice/instrument#>
			SELECT $this ?activity ?prohibition WHERE {
				$this ins:excepts ?prohibition ;
					  ins:activity ?activity .
				FILTER NOT EXISTS { ?prohibition ins:activity ?activity }
			}
		"""
	] .

ins:ExclusionHolderShape a sh:NodeShape ;
	sh:targetClass ins:Exclusion ;
	sh:sparql [
		sh:message "The exclusion's holder {?holder} is not the obligor of the obligation it excepts, {?excepted} (law I8)." ;
		sh:select """
			PREFIX ins:  <https://www.nebularis.org/neuro-semantic/lattice/instrument#>
			PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
			PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
			SELECT $this ?holder ?excepted WHERE {
				$this ins:excepts ?excepted ;
					  ins:holder ?holder .
				?excepted rdf:type/rdfs:subClassOf* ins:Obligation .
				FILTER NOT EXISTS { ?excepted ins:obligor ?holder }
			}
		"""
	] ;
	sh:sparql [
		sh:message "The exclusion's holder {?holder} is not a counterparty of the power it excepts, {?excepted}: an immunity protects the party the power is held against (law I8)." ;
		sh:select """
			PREFIX ins:  <https://www.nebularis.org/neuro-semantic/lattice/instrument#>
			PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
			PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
			SELECT $this ?holder ?excepted WHERE {
				$this ins:excepts ?excepted ;
					  ins:holder ?holder .
				?excepted rdf:type/rdfs:subClassOf* ins:Power .
				FILTER NOT EXISTS { ?excepted ins:counterparty ?holder }
			}
		"""
	] .

ins:RegimeTransitionsShape a sh:NodeShape ;
	sh:targetClass ins:Regime ;
	sh:sparql [
		sh:message "{?transition} moves to or from a state of the regime {$this}, but is not an ins:RegimeTransition." ;
		sh:select """
			PREFIX ins:  <https://www.nebularis.org/neuro-semantic/lattice/instrument#>
			PREFIX bhv:  <https://www.nebularis.org/neuro-semantic/lattice/behaviour#>
			PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
			PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
			SELECT DISTINCT $this ?transition WHERE {
				?transition (bhv:fromState|bhv:toState)/bhv:inStateSpace $this .
				FILTER NOT EXISTS { ?transition rdf:type/rdfs:subClassOf* ins:RegimeTransition }
			}
		"""
	] .

ins:GateStateShape a sh:NodeShape ;
	sh:targetSubjectsOf ins:appliesInState ;
	sh:sparql [
		sh:message "{$this} is gated by {?state}, which is not a state of an ins:Regime." ;
		sh:select """
			PREFIX ins:  <https://www.nebularis.org/neuro-semantic/lattice/instrument#>
			PREFIX bhv:  <https://www.nebularis.org/neuro-semantic/lattice/behaviour#>
			PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
			PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
			SELECT $this ?state WHERE {
				$this ins:appliesInState ?state .
				FILTER NOT EXISTS {
					?state bhv:inStateSpace/(bhv:regionOf/bhv:inStateSpace)* ?regime .
					?regime rdf:type/rdfs:subClassOf* ins:Regime .
				}
			}
		"""
	] .

ins:PerOccasionGateShape a sh:NodeShape ;
	sh:targetSubjectsOf ins:appliesInState ;
	sh:sparql [
		sh:message "{$this} is gated by {?state}, a state of a regime for each occasion of {?relation}, but arises on no breach or exercise of it, so no occasion is reached (C11a-Q4)." ;
		sh:select """
			PREFIX ins:  <https://www.nebularis.org/neuro-semantic/lattice/instrument#>
			PREFIX bhv:  <https://www.nebularis.org/neuro-semantic/lattice/behaviour#>
			SELECT $this ?state ?relation WHERE {
				$this ins:appliesInState ?state .
				?state bhv:inStateSpace/(bhv:regionOf/bhv:inStateSpace)* ?space .
				?space bhv:perOccasionOf ?relation .
				FILTER NOT EXISTS {
					$this (ins:arisesOnBreachOf|ins:arisesOnExerciseOf|ins:arisesOn/(ins:ofObligation|ins:ofPower)) ?arising .
					?arising ins:boundFrom? ?relation .
				}
			}
		"""
	] .

ins:TollingShape a sh:NodeShape ;
	sh:targetSubjectsOf ins:tolledIn ;
	sh:sparql [
		sh:message "The period of {$this} is tolled in {?state}, a state of the state space it runs in: a period's clock is stopped only by another space's state, such as another regime's or a sub-state's (C11a-Q2)." ;
		sh:select """
			PREFIX ins:  <https://www.nebularis.org/neuro-semantic/lattice/instrument#>
			PREFIX bhv:  <https://www.nebularis.org/neuro-semantic/lattice/behaviour#>
			SELECT DISTINCT $this ?state WHERE {
				$this ins:tolledIn ?state .
				?transition bhv:hasTrigger $this ;
					bhv:fromState/bhv:inStateSpace ?space .
				?state bhv:inStateSpace ?space .
			}
		"""
	] .
```

### 14.3 Optional: one expression per term

Load only where every stated term is expressed in one element version. A term may otherwise be
expressed again in another language or a consolidated text (ADR-A96).

```turtle-shapes
# Optional (ADR-A96). Load only where every stated term is expressed in one
# element version.

@prefix sh:  <http://www.w3.org/ns/shacl#> .
@prefix ins: <https://www.nebularis.org/neuro-semantic/lattice/instrument#> .

ins:SingleExpressionShape a sh:NodeShape ;
	sh:targetClass ins:Term ;
	sh:property [ sh:path ins:alsoExpressedIn ; sh:maxCount 0 ;
		sh:message "This deployment expresses each term in one element version only (ADR-A96)." ] .
```

## 15. Laws

| Law | Statement | Register in 0.10.0 |
|---|---|---|
| I1 | An instrument version is expressed in exactly one assembled wording | `ins:InstrumentShape` |
| I2 | A stated term is part of exactly one element version. A bound term is part of exactly one instrument version, bound from exactly one stated term or implied by a source. A relation belongs to its term | `ins:TermShape`, `ins:LegalRelationShape`, `ins:RelationTierShape` |
| I8 | A permission's holder is the excepted prohibition's obligor, with the same activity. An exclusion's holder is the excepted obligation's obligor or the power's counterparty | `ins:PermissionExceptsOwnProhibitionShape`, `ins:ExclusionHolderShape` |
| I13 | Stated meaning names roles, bound meaning occupancies and groups. Only bound relations are evaluated. A regime is stated only, read as stated for each subject (C7a-Q1) | `ins:RelationTierShape`, `ins:ArisingTierShape`, `ins:RegimeShape` |
| I18 | No term or relation is a version: meaning changes only with its owner | disjointness with `fnd:Version`, `ins:LegalRelationShape` |
| B4 (Behaviour's) | Every Instrument specialisation of a Behaviour term carries the Behaviour type in the graph the engine reads | `ins:RegimeTypeShape`, `ins:RegimeTransitionTypeShape`, `ins:LegalTriggerTypeShape` |

C7a's other design-time rules are registered without a law number: a regime's transitions are
regime transitions with legal triggers and the fixed engine settings (`ins:RegimeTransitionShape`,
`ins:RegimeTransitionsShape`), each trigger's required value and kind (`ins:OnExerciseShape` to
`ins:OnExpiryShape`), a gate names a state of a regime (`ins:GateStateShape`) and reaches its
occasion (`ins:PerOccasionGateShape`), and tolling (`ins:TollingShape`). The gating rule itself,
per-occasion resolution and tolling are evaluated by C12 and C13.

Laws I3 to I7, I9 to I12 and I14 to I17 arrive with the slices that build their terms. I6, the
acyclic graph of breach, exercise and state reading, is checked once C7b's due ranges and C13's
state reading exist.

## 16. Worked Examples

Eight instruments in [`examples/`](examples/), each with a small wording of its own, its clauses'
stated meaning, and the bound meaning of one instrument. The last four state regimes. Each is
validated with the lower layers' shapes and these, without a reasoner.

### 16.1 A facility agreement

[`facility-agreement.ttl`](examples/facility-agreement.ttl). A borrower and two lenders, 60% and 40%.

```mermaid
---
config:
  layout: elk
---
flowchart LR
    T61["term 6.1"] --- RP["repay<br/>Obligation"]
    T71["term 7.1"] --- LV["leverage<br/>ContinuingObligation<br/>maintains leverage ≤ 3.0"]
    T81["term 8.1"] --- NP["negative pledge<br/>Prohibition<br/>CreateSecurity"]
    T81 --- PL["permitted liens<br/>Permission<br/>scope: lien by law"]
    T101["term 10.1"] --- AC["accelerate<br/>Power<br/>DeclareDue"]
    PL -. "excepts" .-> NP
    BO["borrower occupancy<br/>Acme"]
    LG["lenders<br/>group, several only"]
    TR["security trustee<br/>no party"]
    RP -- "obligor" --> BO
    RP -- "obligee" --> LG
    LV -- "obligee" --> LG
    LV -- "obligee" --> TR
    AC -- "holder" --> LG
    AC -- "counterparty" --> BO
```

What it shows: term 8.1 gives rise to two relations, the negative pledge and the permission
excepting it. Repayment is owed to a group severally, under `pty:SeveralOnly`. The leverage
covenant is owed also to a security trustee who is no party to the agreement, so it is an obligee
and not in `ins:party`. The facility's agreement number and market reference are natural keys on
its persistent identity. Acceleration gated by an event of default is the facility of §16.7. The
consent rule for a group's power is C9's.

### 16.2 A clinical trial protocol

[`trial-protocol.ttl`](examples/trial-protocol.ttl). A sponsor and site 104's investigator.

```mermaid
flowchart LR
    SAE["report adverse events<br/>Obligation"]
    NE["no ineligible enrolment<br/>Prohibition: Enrol<br/>scope: fails the criteria"]
    WV["waiver<br/>Permission: Enrol<br/>scope: written waiver"]
    END["end participation<br/>Power"]
    INV["investigator"]
    SP["sponsor"]
    WV -. "excepts" .-> NE
    SAE -- "obligor" --> INV
    NE -- "obligor" --> INV
    WV -- "holder" --> INV
    END -- "holder" --> SP
    END -- "counterparty" --> INV
```

What it shows: law I8, where the waiver's holder is the prohibition's obligor, with the same
activity, `Enrol`. The prohibition's scope says whom it forbids enrolling, and the waiver's scope
when it permits it. The reporting deadline is a due range (C7b).

### 16.3 A product warranty

[`product-warranty.ttl`](examples/product-warranty.ttl). A manufacturer and whoever owns the kettle.

```mermaid
flowchart LR
    RE["repair<br/>Obligation"]
    EX["misuse exclusion<br/>Exclusion<br/>scope: misuse, not a defect"]
    MF["manufacturer"]
    OW["owner<br/>contingent occupancy<br/>role, no actor"]
    EX -. "excepts" .-> RE
    RE -- "obligor" --> MF
    RE -- "obligee" --> OW
    EX -- "holder" --> MF
    EX -- "counterparty" --> OW
```

What it shows: an exclusion excepting an obligation, whose holder is the obligation's obligor (I8).
Its carve-back is a negated member of its scope ("misuse, unless a manufacturing defect"). The
owner is a contingent occupancy: whoever owns the kettle when a claim is made fills it, as C7b
decides.

### 16.4 A software licence

[`software-licence.ttl`](examples/software-licence.ttl). A licensor and a licensee.

```mermaid
flowchart LR
    TC["end for convenience<br/>Power: Terminate<br/>scope: without cause"]
    IM["perpetual immunity<br/>Exclusion<br/>scope: perpetual fee paid"]
    LR["licensor"]
    LE["licensee<br/>notice address<br/>operates at Leeds, Dublin"]
    IM -. "excepts" .-> TC
    TC -- "holder" --> LR
    TC -- "counterparty" --> LE
    IM -- "holder" --> LE
```

What it shows: an immunity, an exclusion of a power held by the power's counterparty (I8). The
power's activity is plain `Terminate`, its scope "without cause". Party details sit on the
occupancies. The grant of use is not modelled: a permission excepts a prohibition, and a bare
licence to use has none to except.

### 16.5 A licence with a notice period

[`licence-notice.ttl`](examples/licence-notice.ttl). A licensor and a licensee. A period regime.

```mermaid
stateDiagram-v2
    state "in force" as InForce
    state "notice period" as NoticePeriod
    state "terminated" as Terminated
    [*] --> InForce
    InForce --> NoticePeriod : exercise of end on notice (11.1)
    NoticePeriod --> Terminated : expiry, 90 days
    InForce --> Terminated : exercise of end for breach (11.2)
    NoticePeriod --> Terminated : exercise of end for breach (11.2)
```

```mermaid
flowchart LR
    GS["grant sub-licences<br/>ins:Power: GrantSublicence"]
    SE["sub-licensing excluded<br/>ins:Exclusion"]
    NP["notice period"]
    SE -. "excepts" .-> GS
    SE -- "appliesInState" --> NP
```

What it shows: a period regime under clause 11.1, the term of the power whose exercise starts it.
Its triggers name the stated powers (§11.1). Termination for breach applies from either state, so
it is two transitions. Clause 11.3 takes away the licensee's power to grant sub-licences while
notice runs: an exclusion of the power, the licensor's immunity, held by the licensor as the power's
counterparty (I8), and gated by the notice period. The grant's own scope never mentions the regime
(DP6, §11.5). The 90 days are a quantity in a day unit, on a duration space the example declares.

### 16.6 A supply agreement with suspension and force majeure

[`supply-suspension.ttl`](examples/supply-suspension.ttl). A supplier and a buyer. Two switching
regimes on one instrument.

```mermaid
flowchart LR
    DL["deliver<br/>ins:Obligation"]
    SU["suspend<br/>ins:Power, Supplier"]
    RR["require resumption<br/>ins:Power, Buyer"]
    IF["in force"]
    SP["suspended"]
    UN["unaffected"]
    AF["affected"]
    DL -- "appliesInState" --> IF
    DL -- "appliesInState" --> UN
    RR -- "appliesInState" --> SP
    SU -. "exercise moves" .-> SP
    RR -. "exercise moves" .-> IF
    subgraph SR["suspension regime"]
        IF
        SP
    end
    subgraph FR["force majeure regime"]
        UN
        AF
    end
```

What it shows: a switching regime moved by two parties' powers, the supplier's to suspend and the
buyer's to have deliveries resumed, and a force majeure regime moved by conditions. The duty to
deliver is gated across both: it applies only in force and unaffected (§11.3). The buyer's power
is itself gated by the suspended state, so it exists only while there is a suspension to end.
Clause 14.1 states no relation of its own, only its regime, so its term binds nothing (ADR-A104
2026-10-04 addendum, decision 1). The unaffected state has no kind.

### 16.7 A facility with a cure period

[`facility-cure-period.ttl`](examples/facility-cure-period.ttl). A lender and a borrower. A period
regime entered and left on conditions, tolled by a second regime.

```mermaid
stateDiagram-v2
    state "performing" as Performing
    state "cure period" as Cure
    state "default" as InDefault
    [*] --> Performing
    Performing --> Cure : leverage above 3.0
    Cure --> Performing : leverage within 3.0
    Cure --> InDefault : expiry, 30 business days, tolled while affected
```

What it shows: the cure period is entered and left by `ins:OnCondition`s over two interval
conditions that partition the leverage ratio at 3.0, one of them the condition the covenant
maintains. Default follows the expiry of 30 business days, a `qnt:CalendarUnit`, counted only while
the force majeure regime is unaffected (`ins:tolledIn`, §10). The power to accelerate is gated by
the default state. Clauses 22.1 and 22.2 state only regimes, so their terms bind nothing.

### 16.8 A services agreement with a dispute per occasion

[`service-dispute.ttl`](examples/service-dispute.ttl). A provider and a customer. A per-occasion
regime.

```mermaid
stateDiagram-v2
    state "undisputed" as Undisputed
    state "disputed" as Disputed
    state "dispute over" as Over
    [*] --> Undisputed
    Undisputed --> Disputed : the Provider's act of disputing
    Disputed --> Over : the dispute is settled
```

What it shows: a dispute regime `bhv:perOccasionOf` the stated service obligation, so every month's
occasion of every bound service obligation has its own dispute. The customer's power to end the
agreement, and the exclusion of that power, both arise on breach of the service obligation
(`ins:arisesOnBreachOf`), and the exclusion is gated by the disputed state. For one month's breach
the gate reads that month's dispute (§11.4). Raising a dispute is an `ins:OnAct` naming the act
and the party (`ins:by`). Its activity is the same property a relation uses (C7a-Q2).

## 17. Release Notes

Breaking versions at major version zero ([ADR-A113](../../docs/architecture/decisions/ADR-A113-breaking-changes-at-major-version-zero.md)):

- 0.10.0 (CCS C7a, ADR-A104 and its 2026-10-04 addendum): additive. New: the five legal triggers
  (`ins:OnExercise`, `ins:OnBreach`, `ins:OnAct`, `ins:OnCondition`, `ins:OnExpiry`) with
  `ins:ofPower`, `ins:ofObligation`, `ins:by`, `ins:condition`, `ins:after` and `ins:tolledIn`,
  `ins:Regime`, `ins:RegimeTransition`, `ins:stateKind`, `ins:appliesInState`, and arising and
  ending (`ins:arisesOn`, `ins:arisesOnBreachOf`, `ins:arisesOnExerciseOf`, `ins:endsOn`). The
  Behaviour terms each Instrument class fixes are `owl:hasValue` restrictions, and
  `ins:ofPower`, `ins:ofObligation` and `ins:tolledIn` have domains, so an OWL 2 RL reasoner adds
  them (§12). `ins:activity` loses its domain, which rejects nothing that conformed (C7a-Q2).
  `instrument-vocab` 0.10.0 adds the state kind contract and its baseline scheme, and six
  activities. Shapes 0.3.0 (additive, rejecting only data that uses the new terms): regimes, their
  transitions and triggers, B4, gating, the per-occasion arising rule, tolling, and the tiers of
  arising.

- 0.9.0 (breaking, CCS C6, ADR-A104): the minimal ADR-A07b shape is replaced. Retired:
  `ins:Element`, `ins:Provision`, `ins:hasProvision`, `ins:partOfInstrument`, `ins:hasObligation`,
  `ins:inProvision`, `ins:hasQualifier`, `ins:hasCondition`, `ins:fulfilledBy`. New: the instrument,
  terms in two tiers, the five relations, their parties and content, qualifiers. `instrument-vocab`
  0.9.0 adds the activity and location contracts and `ins:InstrumentTarget`. Shapes 0.2.0
  (breaking): every shape is new, the supersession shape targets `ins:Instrument`, and the optional
  `single-provision.ttl` becomes `single-expression.ttl`. The projection to Party is retired, since
  Instrument now imports Party.
- 0.8.0: re-pinned to Foundation 0.4.0 and the layers re-pinned with it, with no other change (CCS
  F1, ADR-A114).
