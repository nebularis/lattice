<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

## 0. Why LATTICE
{: #why}

A contract governs data. A loan facility agreement decides who may borrow, how much, against which
limit, what happens when a covenant is breached, and who must be told. In most estates that meaning
is spread across a document store, a few relational tables with columns like `covenant_status`, and
application code that decides what the columns mean. Each copy drifts from the others, and none of
them can answer a question the designers did not anticipate.

LATTICE represents a governing instrument, such as a contract, a protocol or a policy, as a graph
of typed, versioned statements that a machine can query and check. It is a framework rather than an
application. You take the parts you need, extend them for your own domain, and leave the rest.

### What you will be able to do by the end

- read any of LATTICE's example files and say what each statement means
- place a concept from your own domain in the right layer, or recognise that it belongs in an
  applied module of your own
- explain to a colleague how LATTICE separates identity from version, text from meaning, and stated
  facts from the judgements drawn from them
- judge which parts of LATTICE a project of yours would use

### Three ideas that run through every layer

**Identity is separate from version.** A facility agreement amended twice is one agreement with
three versions. LATTICE gives the agreement a persistent identity and each version its own node, so
a question can ask about either. Chapter 4 shows how.

**Text is separate from meaning.** Clause 4.1 of a facility agreement is a piece of text with a
number and a position. What it obliges the borrower to do is a separate statement that points at
that text. One wording can serve many facilities, and its meaning is worked out for each one.
Chapters 5 and 6 cover this.

**Judgements are evaluated, never typed in.** Whether a borrower is eligible, or whether a covenant
is in default, is worked out from facts and rules each time it is asked. It is not a column someone
updates. The ontology states the rules and the facts, and code evaluates them. Chapters 8 and 9
show the evaluation, including the third answer, "undetermined", that a two-valued status column
cannot express.

### One agreement, followed through every layer

Most of LATTICE's layers ship worked examples built around the same kind of contract, a syndicated
loan facility. The borrower is Acme Holdings plc, the lenders include North Bank plc and South Bank
SA, and a security trustee holds security for them. The facility has a limit, a leverage covenant
tested each quarter, a cure period when the covenant fails, and drawdowns against the limit.

Each layer's example is written on its own, so details such as the agreement number differ from file
to file. The shape of the deal does not, which is what lets this tutorial add one layer at a time to
a model you already know.

### How to read this tutorial

Every excerpt is copied from a real file in the repository, and a check confirms it still matches.
The link above each excerpt opens the whole file on GitHub. Chapters 1 to 3 give you the vocabulary,
the notation and the map. Chapters 4 to 11 each add one layer to the facility. Chapter 12 shows how a
whole domain is built on top, and chapter 13 says where to go next.

Nothing here needs to be installed or run. A hands-on version, where you validate and break the
examples yourself, is planned separately.
