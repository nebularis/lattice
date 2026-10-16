<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

## 4. Identity and keys
{: #identity}

The Foundation layer answers the first question any data architect asks about a record: what is
this, and is it the same thing as that? It gives LATTICE four capabilities: persistent identity
and versioning, evidence, time-bounded validity, and governance status. This chapter covers the
first in depth and the others briefly, because every later layer leans on them.

### One identity, many versions

If you have built a slowly changing dimension of type 2, you already know the pattern. A durable key
stays the same while each change adds a new row with its own surrogate key. Foundation makes that
pattern part of the model.

- A **persistent identity** (`fnd:PersistentIdentity`) is the agreement as a continuing thing, the
  durable key.
- A **version** (`fnd:Version`) is one state of it. The domain node itself is the version. There is
  no separate "version row" pointing at it.
- Each version points at its identity with `fnd:hasIdentity`, exactly once, and at the version that
  replaced it with `fnd:supersededBy`.

Here is the facility agreement, amended once.

<!-- source: ontology/foundation/examples/keys.ttl -->
```turtle
ex:facility-identity a ex:AgreementIdentity , fnd:PersistentIdentity , fnd:NaturallyKeyed ;
    fnd:naturalKey key-agr:FA-2027-0412 , key-mr:MR-2027-000412 ;
    # The account drawdowns are paid into. It locates the agreement, and
    # since the bank may reassign the number, it never identifies it.
    fnd:externalKey key:3f6a0c9e-2b7d-4e1f-a58c-06d9b2e47f13 .

ex:facility-v1 a ex:Agreement , fnd:Version ;
    fnd:hasIdentity ex:facility-identity ;
    fnd:supersededBy ex:facility-v2 .

ex:facility-v2 a ex:Agreement , fnd:Version ;            # the amended agreement
    fnd:hasIdentity ex:facility-identity .
```

[Source on GitHub](https://github.com/nebularis/lattice/blob/main/ontology/foundation/examples/keys.ttl).
There are no effective-from and effective-to columns, and no "current" flag. The current version is
the one nothing supersedes, which is a question you ask rather than a flag you maintain. The same
file shows the query in a comment.

<!-- source: ontology/foundation/examples/keys.ttl -->
```turtle
#   SELECT ?version WHERE {
#     ?key fnd:keyScheme ex:market-reference ; fnd:keyValue "MR-2027-000412" .
#     ?version fnd:hasIdentity/fnd:naturalKey ?key .
#     FILTER NOT EXISTS { ?version fnd:supersededBy ?later }
#   }
```

Read it as SQL with the joins written as paths. Find the key with this scheme and value, find every
version whose identity has it as a natural key, and keep the version with no successor. The `/` in
`fnd:hasIdentity/fnd:naturalKey` follows two properties in a row, a join in one step.

Not everything needs versions. In the same file the borrower, Acme Holdings plc, is an ordinary node
with no identity split. Versioning is something a class opts into by subclassing `fnd:Version`, as
`ex:Agreement` did in chapter 2.

### Identities and keys are different things

LATTICE mints the IRI of every identity itself, never reuses it, and keeps it opaque. The names the
world gives a thing are **keys**: an agreement number from the facility agent, a market reference
from a settlement platform, a company number and a legal entity identifier (LEI) for the borrower.

| | Identity (the IRI) | Key |
|---|---|---|
| Relational counterpart | surrogate key | natural or business key |
| Issued by | LATTICE | a registry, a market, a party |
| How many per thing | exactly one | any number, from different schemes |
| Can change | never | gained and withdrawn over time |
| Can be sensitive | never | sometimes, for example a national identity number |

Each key is a node with exactly one value and one **scheme**. The scheme records facts about its
values that a data architect would otherwise keep in a data dictionary.

<!-- source: ontology/foundation/examples/keys.ttl -->
```turtle
ex:account-number a fnd:KeyScheme ;                      # a bank reassigns closed accounts' numbers
    rdfs:label "Example Bank account numbers" ;
    fnd:reissuesValues true ;
    fnd:sensitiveDataScheme true ;
    fnd:personalDataScheme false ;
    fnd:keyNormalisation "NfkcTrimUppercase" .
```

`fnd:reissuesValues` says whether the issuer may later give a withdrawn value to something else.
`fnd:sensitiveDataScheme` and `fnd:personalDataScheme` drive privacy handling. A scheme can also
give a `fnd:valuePattern`, a regular expression its values must match, which a SHACL shape checks.
The normalisation names how two values are compared, here by Unicode normalisation, trimming and
upper-casing.

### Natural keys identify, external keys locate

The most useful distinction in Foundation for a data architect is between two properties.

- **`fnd:naturalKey` identifies.** The key picks out this thing and nothing else. A thing may have
  several. Acme has both its company number and its LEI.
- **`fnd:externalKey` locates.** The record carries the key without being the thing it names. Every
  drawdown request carries the facility's market reference, much as a fact row carries a foreign
  key.

<!-- source: ontology/foundation/examples/keys.ttl -->
```turtle
ex:drawdown-1 a ex:DrawdownRequest ;
    fnd:externalKey key-mr:MR-2027-000412 ,                       # the agreement drawn under
                    key:3f6a0c9e-2b7d-4e1f-a58c-06d9b2e47f13 .    # the account paid into
```

Only a scheme that never reissues values may supply natural keys, and a SHACL shape enforces it. The
bank account number in the excerpt above can be reassigned when an account closes, so it can locate
the account today but never identify it. In the first excerpt the facility uses it as an external key
for the same reason.

Keys belong to what persists. On a versioned thing they attach to the persistent identity, since the
agreement number names the agreement across all its versions. On an unversioned thing, such as Acme,
they attach to the thing itself.

### Sensitive values stay out of identifiers

The account number's key node is `key:3f6a0c9e-…`, a random surrogate, while the market reference's
is `key-mr:MR-2027-000412`. A sensitive scheme's values never appear in an IRI, hashed or not,
because IRIs travel into logs, URLs and other systems. The value is held only in `fnd:keyValue`,
where access control and erasure can reach it. If you have had to scrub national identity numbers
out of a primary key, you know why.

### Who enforces uniqueness

In a relational database a unique index rejects a duplicate. Foundation offers three levels, and
the choice matters.

- Its SHACL shapes report two things claiming the same natural key, after the fact.
- An adopter using only an OWL reasoner can mark a class so that sharing a natural key means "these
  are the same thing". The reasoner then merges the two nodes rather than rejecting either, and
  nothing in OWL can undo the merge or say why it happened.
- The Persistence layer (chapter 11) enforces uniqueness when the data is written. A duplicate is
  rejected, quarantined or recorded for review.

LATTICE recommends Persistence for any deployment that writes keyed data. This is the unique-name
point from chapter 1 again. Without a write-time guard, a graph merges where a database refuses.

### The other three capabilities, briefly

- **Governance status.** Anything that passes through review before it is trusted carries a
  `fnd:hasGovernanceState`, such as draft, active or superseded. Every clause in the next chapter is
  marked `fnd:Active`. Foundation records the current value only. Moving between values is
  Behaviour's job.
- **Time-bounded validity.** A temporal scope with `fnd:validFrom` and `fnd:validTo` says when a
  statement holds. Chapter 6 uses it for when a bank became a lender under the facility.
- **Evidence.** `fnd:hasEvidence` ties a statement to what supports it, with who asserted it and
  when it was recorded. This is lineage at the level of a single fact.

[Foundation's README](https://github.com/nebularis/lattice/blob/main/ontology/foundation/README.md)
defines every term used here, with the reasons for each design choice.
