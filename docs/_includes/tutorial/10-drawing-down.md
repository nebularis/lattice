<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

## 10. Drawing down
{: #capacity}

A facility has a limit, and the borrower draws against it. The limit is a number in the agreement. What remains available changes with every drawdown and repayment. LATTICE keeps the two apart. The instrument states the **static** limit, and the running balance is **dynamic** state, kept by the Ledger layer as a record of facts rather than a number someone updates.

<div class="callout"><strong>Partly built.</strong> Ledger's account definition is released. The records of each draw, the postings and balance records shown below, are designed and appear in Ledger's own example, but are not yet released. The applied Capacity module, which joins limits into networks, has its runtime profile published and its source ontology still being designed. This chapter says which is which.</div>

### An account, not a balance column

A Ledger **account** states an amount that is consumed and restored. Here is a 20,000,000 sterling revolving facility that the borrower draws in euros.

<!-- source: ontology/ledger/examples/revolving-facility.ttl -->
```turtle
ex:q-commitment a qnt:Quantity ; qnt:onSpace ex:money ; qnt:numericValue "20000000"^^xsd:decimal ; qnt:inUnit ex:GBP .

ex:facility a ldg:AccountDefinition ;
    ldg:statedAmount ex:q-commitment ;
    ldg:unitOfAccount ex:money ;
    ldg:admitsOwnerKind ex:Borrower ;
    ldg:mergeRule ldg:Refuse ;
    ldg:conversionMethod ex:fx-2027-06-01 ;
    rdfs:comment "A 20,000,000 sterling revolving commitment, drawn in euros." .
```

- **`ldg:statedAmount`** is the commitment. It never changes when money is drawn or repaid.
- **`ldg:unitOfAccount`** is a value space from chapter 7, and it must be extensive, since a balance only means something if amounts add.
- **`ldg:admitsOwnerKind`** says whose account it can be, here a borrower.
- **`ldg:mergeRule`** says what happens when several claims arrive at the same moment. `ldg:Refuse` refuses them all. Other rules take them in priority order or share the amount in proportion.
- **`ldg:conversionMethod`** names how a drawing in another currency is converted, here by the day's recorded rate.

### Every draw is a fact, and the balance is derived

A relational design usually holds a `balance` column and updates it in place. Ledger records each draw or repayment as a fact of its own, a **posting**, and derives the balance by adding the postings up. If you have built an accounting journal, an event store or a fact table of transactions, the idea is the same, and so is the benefit. The history cannot be lost, and any balance can be read as of any point.

Postings are ordered by a whole number, the **position**, not by a clock, since clocks on two machines rarely agree closely enough to order two claims. The first drawing, at position 1, looks like this in the example.

<!-- source: ontology/ledger/examples/revolving-facility.ttl -->
```turtle
ex:draw-1-posting a ldg:Posting ;
    ldg:onAccount ex:facility ; ldg:forOwner ex:borrower ;
    ldg:atPosition "1"^^xsd:integer ; ldg:atMicroPosition "0"^^xsd:integer ;
    ldg:direction ldg:Debit ; ldg:amountValue "10005000"^^xsd:decimal ;
    ldg:amountAsDrawn ex:q-draw-1-eur ; ldg:conversionUsed ex:fx-2027-06-01 ;
    prov:wasDerivedFrom ex:draw-1-merge , ex:draw-1-grant .
ex:balance-1 a ldg:BalanceRecord ;
    ldg:onAccount ex:facility ; ldg:forOwner ex:borrower ;
    ldg:atPosition "1"^^xsd:integer ; ldg:atMicroPosition "0"^^xsd:integer ;
    ldg:remainingValue "9995000"^^xsd:decimal ; ldg:availableValue "9995000"^^xsd:decimal ;
    prov:wasDerivedFrom ex:draw-1-posting .
```

The posting keeps both the sterling amount it counts and the euros actually drawn, with the rate it used. The balance record says what remains after it, and `prov:wasDerivedFrom` records which facts it was worked out from. The example's three positions:

| Position | Event | Euros | Rate | Sterling | Balance after |
|---|---|---|---|---|---|
| 1 | drawing | 11,500,000 | 0.87 | 10,005,000 debit | 9,995,000 |
| 2 | repayment | 5,000,000 | 0.88 | 4,400,000 credit | 14,395,000 |
| 3 | revaluation of the 6,500,000 euros still out | | 0.90 | 245,000 debit | 14,150,000 |

Position 3 is not a new drawing. The euros still outstanding are worth more sterling at the year-end rate, so the account records the difference as a fact of its own. [Source on GitHub](https://github.com/nebularis/lattice/blob/main/ontology/ledger/examples/revolving-facility.ttl).

### Accounts inside accounts

Accounts form a tree with `ldg:partOf`, which means "part of, and not in addition to". A sublimit sits inside a facility, and a draw from the sublimit uses up the facility too. A **key dimension** creates one account per value of a key the first time a draw names it, for example one sublimit per borrower in a syndicate, without declaring each in advance. The relational counterpart is a hierarchy of budget lines, with the rule that a child can never offer more than its parent has left.

### Networks of limits, and a read model

Some limits interact in ways a tree does not capture. A secondary facility may open only once a primary one is exhausted. The applied **Capacity** module is designed for these networks, with resources joined by typed dependencies that deplete, bound or gate one another. Its design document works through a revolving facility of 10,000,000 with two subfacilities, of 4,000,000 and 6,000,000. [Capacity's design document](https://github.com/nebularis/lattice/blob/main/docs/architecture/capacity-domain-analysis-and-design.md).

Evaluating a drawdown by walking the whole graph would be slow at the moment a payment system needs an answer. Capacity therefore defines an **execution profile** (`capx:`), a compact copy of an arrangement materialised from the source graph, which stays the source of truth. A data architect would call it a read model. Its shapes carry the rules a ledger would enforce. One is conservation. What a draw requested must equal what it was allocated plus what went unmet.

<!-- source: ontology/applied/capacity/spec/capacity-execution.ttl -->
```turtle
  sh:sparql [
    a sh:SPARQLConstraint ;
    sh:message "Draw conservation violated: requested != allocated + unmet." ;
    sh:select """
      PREFIX capx: <https://www.nebularis.org/neuro-semantic/lattice/applied/capacity/execution#>
      SELECT $this WHERE {
        $this capx:drawRequestedAmount ?rq ;
              capx:allocatedAmount ?al ;
              capx:unmetAmount ?um .
        FILTER((?al + ?um) != ?rq)
      }
    """
  ] .
```

This is a SHACL shape written as a SPARQL query, the graph form of a reconciliation query that returns the rows that do not balance. A draw ends with one of five statuses, **Allocated**, **PartiallyAllocated**, **Denied**, **Unavailable** or **Undetermined**, and the last follows the rule used throughout LATTICE. If the data cannot decide, the answer says so. [Source on GitHub](https://github.com/nebularis/lattice/blob/main/ontology/applied/capacity/spec/capacity-execution.ttl).

### How the pieces meet

The facility's limit lives in its bound meaning (chapter 6), and its value may come from a blank in the form (chapter 5). Its account is a Ledger account. A draw can be refused by an eligibility decision (chapter 8), and can be caused by a transition (chapter 9). Behaviour's own simple allowances, a balance consumed by an effect, are to give way to Ledger accounts, so that every layer that counts down an amount does it the same way ([ADR-A131](https://github.com/nebularis/lattice/blob/main/docs/architecture/decisions/ADR-A131-ledger-layer.md)).
