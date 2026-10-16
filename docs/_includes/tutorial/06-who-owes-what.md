<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

## 6. Who owes what
{: #instrument}

The Instrument layer states what an agreement binds its parties to. Party supplies the parties. This
chapter reads the facility's four key clauses as data, first on the lender's form and then for Acme's
facility.

| Clause | Text, abridged | What it creates |
|---|---|---|
| 6.1 | The Borrower shall repay each loan to the Lenders, each for its share. | an obligation owed to a group, severally |
| 7.1 | The Borrower shall ensure that leverage does not exceed 3.0 to 1. | a continuing obligation |
| 8.1 | The Borrower shall not create any security over its assets, except a lien arising by operation of law. | a prohibition, and a permission excepting it |
| 10.1 | The Lenders may by notice declare all loans immediately due and payable. | a power |

### Five relations, one verb each

"Right" is the word a data model reaches for first, and the one Instrument avoids. A lawyer's
"right" covers four different things, and a column called `has_right` cannot say which. Instrument
follows the legal theorist Wesley Hohfeld and gives each its own class, read with one modal verb.

| Class | Reads as | In the facility |
|---|---|---|
| `ins:Obligation` | the obligor **must** do something for the obligee | 6.1, repay |
| `ins:ContinuingObligation` | the obligor **must ensure** a state holds | 7.1, leverage at most 3.0 |
| `ins:Prohibition` | the obligor **must not** do something | 8.1, the negative pledge |
| `ins:Permission` | the holder **may** do it, despite a prohibition | 8.1, liens by law |
| `ins:Exclusion` | the holder **need not** perform an obligation, or a power **cannot be exercised** against them | not in this facility. The [software licence example](https://github.com/nebularis/lattice/blob/main/ontology/instrument/examples/software-licence.ttl) has one |
| `ins:Power` | the holder **can** act to change the other side's position | 10.1, acceleration |

Each relation is **one node with two ends**. The borrower's duty to repay and the lenders' claim to
be repaid are the obligor's and obligee's ends of one `ins:Obligation`. Nothing has to keep two
records in step, because there is only one.

### A clause can create more than one relation

Clause 8.1 is one provision with two relations. The form's stated meaning says so directly.

<!-- source: ontology/instrument/examples/facility-agreement.ttl -->
```turtle
# One provision, two relations: the prohibition and its exception.
tmpl:term-8-1 a ins:Term , ins:Template ; ins:expressedIn ex:cl-8-1 .
tmpl:negative-pledge a ins:Prohibition , ins:Template ;
    ins:arisesUnder tmpl:term-8-1 ;
    ins:obligor ex:Borrower ;
    ins:obligee ex:Lender ;
    ins:activity ins-voc:CreateSecurity .
tmpl:permitted-liens a ins:Permission , ins:Template ;
    ins:arisesUnder tmpl:term-8-1 ;
    ins:holder ex:Borrower ;                      # the excepted prohibition's obligor (I8)
    ins:counterparty ex:Lender ;
    ins:activity ins-voc:CreateSecurity ;         # the same activity (I8)
    ins:excepts tmpl:negative-pledge ;
    ins:scope ex:lien-by-law .
```

Read it top down.

- A **term** is the provision the parties are bound by. `ins:expressedIn` ties it to exactly one
  clause, clause 8.1 from chapter 5.
- Each relation **arises under** the term, so it belongs to the clause through it.
- The permission **excepts** the prohibition, for the same activity, within a scope. The scope,
  `ex:lien-by-law`, is an Eligibility condition (chapter 8). The comments marked `I8` cite a law of
  the layer, checked by a shape, that a permission's holder and activity match the prohibition it
  excepts.
- Everything is marked `ins:Template`, and names **roles** (`ex:Borrower`, `ex:Lender`), not
  companies. This is stated meaning, shared by every facility drawn from the form.

### Parties, roles and occupancies

Party separates three things that a single `party` table with a `role` column tends to fuse.

<!-- source: ontology/instrument/examples/facility-agreement.ttl -->
```turtle
ex:acme a pty:Actor ; rdfs:label "Acme Holdings plc" .
ex:north-bank a pty:Actor ; rdfs:label "North Bank plc" .
ex:south-bank a pty:Actor ; rdfs:label "South Bank SA" .
ex:harbour-trustees a pty:Actor ; rdfs:label "Harbour Trustees Ltd" .

ex:borrower-occ a pty:RoleOccupancy ;
    fnd:hasIdentity ex:borrower-occ-identity ;
    fnd:hasTemporalScope [ a fnd:TemporalScope ; fnd:validFrom "2027-01-01T00:00:00Z"^^xsd:dateTime ] ;
    pty:inRole ex:Borrower ;
    pty:occupiedBy ex:acme .
```

- An **actor** is a legal or natural person, such as Acme.
- A **role** is a position the form defines, such as Borrower. The form declares its roles with
  `pty:Role`.
- A **role occupancy** says that this actor holds this role, from this date, with evidence. It is the
  associative entity of a party-role bridge table, effective-dated, and versioned like anything else
  in chapter 4.

Relations for a particular facility point at occupancies and groups, never directly at actors. Who
holds a role, from when, and on what evidence, is then recorded in one place.

### Groups, and how their members stand

The two lenders hold 60% and 40% of the commitments, and each is owed only its own share. Party
models that with a group.

<!-- source: ontology/instrument/examples/facility-agreement.ttl -->
```turtle
ex:lenders a pty:ParticipationGroup ;
    fnd:hasIdentity ex:lenders-identity ;
    pty:hasCompositionRule pty:EachForOwnShare ;
    pty:hasParticipant ex:lender-1-share , ex:lender-2-share .
ex:lender-1-share a pty:GroupMembership ;
    pty:memberOf ex:lenders ; pty:memberOccupancy ex:lender-1-occ ; pty:outwardShare "0.6"^^xsd:decimal .
ex:lender-2-share a pty:GroupMembership ;
    pty:memberOf ex:lenders ; pty:memberOccupancy ex:lender-2-occ ; pty:outwardShare "0.4"^^xsd:decimal .
```

A membership is a weighted bridge row, with the share as its allocation factor. The **composition
rule** says what the weights mean. `pty:EachForOwnShare` makes each member stand for its own share
only, which lawyers call several liability. `pty:EachForWhole` makes each stand for the whole, as
in joint and several liability. Party states the two rules in neutral terms, and the legal reading is
the Instrument layer's. A [definitions example](https://github.com/nebularis/lattice/blob/main/ontology/instrument/examples/facility-definitions.ttl)
shows `pty:EachForWhole` for a borrower and its guarantors.

### Bound meaning: the same clause, for Acme

Instantiation, from chapter 5, produces Acme's own version of each relation.

<!-- source: ontology/instrument/examples/facility-agreement.ttl -->
```turtle
ex:term-6-1 a ins:Term ; ins:boundIn ex:facility-v1 ; ins:boundFrom tmpl:term-6-1 .
ex:repay a ins:Obligation ;
    ins:boundFrom tmpl:repay ;
    ins:arisesUnder ex:term-6-1 ;
    ins:obligor ex:borrower-occ ;
    ins:obligee ex:lenders ;                       # owed severally: pty:EachForOwnShare
    ins:activity ins-voc:Repay .
```

Compare it with the form's `tmpl:repay`.

- The bound term belongs to **Acme's facility** (`ins:boundIn`), and records the stated term it came
  from (`ins:boundFrom`).
- The obligor is Acme's **occupancy** of the Borrower role, and the obligee is the **group** of
  lenders, with its 60/40 rule. Roles have been replaced by parties.
- Everything else is restated in full, not only what differs. RDF has no override, so a relation that
  named both the template's role and Acme's occupancy as obligor would simply have two obligors.

Only bound meaning is ever evaluated. Stated meaning describes the form and never decides anything.

### A beneficiary who is not a party

The security trustee benefits from the leverage covenant but signs a separate deed, not this
agreement.

<!-- source: ontology/instrument/examples/facility-agreement.ttl -->
```turtle
ex:leverage a ins:ContinuingObligation ;
    ins:boundFrom tmpl:leverage ;
    ins:arisesUnder ex:term-7-1 ;
    ins:obligor ex:borrower-occ ;
    ins:obligee ex:lenders , ex:trustee-occ ;      # the trustee benefits, and is no party
    ins:maintains ex:leverage-ok .
```

The instrument lists its signatories separately, with `ins:party`. They are not derived from who
appears in its relations, because a relation can name someone, such as a beneficiary or a regulator,
who never signed. A query for "everyone this facility benefits" and a query for "everyone who signed
it" give different answers, as they should.

`ins:maintains ex:leverage-ok` points at the state the borrower must keep, an Eligibility condition
holding the 3.0 ceiling. Chapters 7 and 8 open it up.

### Every relation traces back to words

From any bound relation there is one path back to the text. Follow the relation to its bound term,
then to the stated term, then to the clause version, then to the clause's text parts. When someone
asks why the system says Acme must keep leverage at or below 3.0, the answer is a clause number and
its exact words.
[Source on GitHub](https://github.com/nebularis/lattice/blob/main/ontology/instrument/examples/facility-agreement.ttl).
