<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

## 10. Drawing down
{: #capacity}

A facility has a limit, and the borrower draws against it. The limit is a number in the agreement.
What remains available changes with every drawdown and repayment. LATTICE keeps the two apart. The
instrument states the **static** limit, and the running balance is **dynamic** state held
elsewhere. This chapter shows where, and introduces the first applied module in the tutorial,
Capacity.

<div class="callout"><strong>Under construction.</strong> Capacity's design is written, and its
runtime profile is published. Its source ontology, the classes an adopter would author against, is
designed but not yet written. This chapter teaches the design and the parts that exist, and says
which is which.</div>

### The generic mechanism: an allowance

Behaviour already has a domain-neutral idea of something finite that is consumed: an **allowance**.
Here is the smallest example, a balance of 100 and an effect that consumes 30.

<!-- source: ontology/behaviour/examples/sequential-allowance.ttl -->
```turtle
ex:allowance-definition
    a bhv:AllowanceDefinition ;
    bhv:allowanceSpace ex:allowance-space ;
    bhv:absorptionPolicy bhv:Sequential ;
    bhv:resetRecurrence ex:cycle-reset .

ex:balance-100 a qnt:Quantity ;
    qnt:onSpace ex:allowance-space ;
    qnt:numericValue "100"^^xsd:decimal .

ex:draw-30 a qnt:Quantity ;
    qnt:onSpace ex:allowance-space ;
    qnt:numericValue "30"^^xsd:decimal .

ex:account-1
    a bhv:AllowanceAccount ;
    bhv:tracksAllowance ex:allowance-definition ;
    bhv:availableBalance ex:balance-100 .

ex:consume-effect
    a bhv:EffectDefinition ;
    bhv:targetKind bhv:AllowanceTarget ;
    bhv:targetsAllowance ex:allowance-definition ;
    bhv:consumesAmount ex:draw-30 ;
    bhv:usesAllowance ex:allowance-definition .
```

The **definition** says what the allowance is measured in, how draws are absorbed, and when it
resets. The **account** holds the current balance. An **effect**, fired by a transition as in
chapter 9, consumes an amount. This is enough for one balance with one limit.
[Source on GitHub](https://github.com/nebularis/lattice/blob/main/ontology/behaviour/examples/sequential-allowance.ttl).

### What a facility needs beyond one balance

Real facilities are networks of limits. Capacity's design document works through a lending case.
A revolving facility of 10,000,000 has two subfacilities, 4,000,000 for working capital and
6,000,000 for acquisitions. One drawdown then has to do several things at once.

- draw from a specific subfacility
- stay within the total facility, not only the subfacility
- reduce what remains of the total facility
- leave a trace of what was allocated and why
- be refused if a covenant-related eligibility guard fails

Capacity models this as **resources** joined by typed **dependencies**. A subfacility *depletes* the
total, so drawing from one reduces the other. The total *bounds* the subfacility, so the subfacility
can never offer more than the total has left. A third kind of dependency *gates* a resource, making
its activation depend on another's state or balance, such as a secondary facility that becomes
available only once a primary facility is exhausted. A drawdown request is a **demand**, and what it actually received is a **draw**.

Capacity supplies the network. Lending supplies what a covenant, a borrower and a breach mean,
through the layers you have already seen.
[Capacity's design document](https://github.com/nebularis/lattice/blob/main/ontology/applied/capacity/docs/architecture-overview.md)
has this case and others, such as API quotas, in full.

### A read model for transaction time

Evaluating a drawdown by walking the general graph, through the instrument, its parameters and its
regimes, would be slow at the moment a payment system needs an answer. Capacity therefore defines an
**execution profile** (`capx:`), a compact, normalised copy of a capacity arrangement, materialised
from the source graph by a deterministic projection. The source graph stays the source of truth. A
data architect would call this a read model, or an operational data store built for one workload.

The profile's shapes carry the rules a ledger would enforce. One is conservation. What a draw
requested must equal what it was allocated plus what went unmet.

<!-- source: ontology/applied/capacity/spec/applied_capacity_execution_spec_capx_Version2.ttl -->
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

This is a SHACL shape written as a SPARQL query. The query selects every draw that breaks the rule,
and each row it returns is reported as a violation. It is the graph form of a reconciliation query
that returns the rows that do not balance.

A draw ends with one of five statuses: **Allocated**, **PartiallyAllocated**, **Denied**,
**Unavailable** or **Undetermined**. The last follows the same rule as everywhere else in LATTICE. If
the data cannot decide, the answer says so.
[Source on GitHub](https://github.com/nebularis/lattice/blob/main/ontology/applied/capacity/spec/applied_capacity_execution_spec_capx_Version2.ttl).

### How the pieces meet

The facility's limit lives in its bound meaning (chapter 6), and its value may come from a blank in
the form (chapter 5). A projection creates the dynamic resource from that static limit. Each draw
can require an eligibility decision (chapter 8), and can be caused by a transition execution
(chapter 9). When a construct proves general enough, it is promoted from Capacity into Behaviour
under criteria set out in a proposed decision record, so the module also shows how applied content
earns a place in the substrate.
