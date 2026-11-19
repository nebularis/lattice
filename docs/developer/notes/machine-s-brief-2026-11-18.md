<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Machine S brief, 2026-11-18: the ledger's unit, the shared proof session, positions and amounts

**For:** the agent on machine S, working the [multi-store architecture epic](../plans/multi-store-architecture.md) on `spi/multi-store-architecture`. **Written on** `docs/placement-vehicles-structure` at the maintainer's request, to answer the two matters MSA-I2 and MSA-I5 raised. It adds to the [brief of 2026-11-17](machine-s-brief-2026-11-17.md), which still holds for the fixes MSA-F1 to MSA-F6 and for how a local workaround stays out of every commit.

Until this branch is merged into `main`, the texts named here are on `docs/placement-vehicles-structure` and nowhere else. Read them there, and do not copy them onto your branch. The maintainer accepted both addenda and confirmed the definition of a position on 2026-11-18.

## 1. What the maintainer decided

| Matter | Decision | Where it is written |
|---|---|---|
| which unit is the ledger's aggregate | the owner's ledger, every account of one owner | LG-Q44 of the [ledger plan](../plans/ledger.md), [ADR-A131](../../architecture/decisions/ADR-A131-ledger-layer.md)'s addendum of 2026-11-18 |
| whether a ledger is a node | yes, one for each owner, holding the revision, with each pass recording the revision it moved the ledger to | LG-Q37 |
| whether Behaviour's state must sit with the ledger it reads | no | the same addendum |
| where the shared types live | a new small proof session, `tools/proofs/shared/` | [ADR-A-FM2](../../architecture/decisions/ADR-A-FM2-formal-methods-theory-home.md)'s addendum of 2026-11-18 |
| the number type | generic over an ordered ring | the same addendum |
| what a position is | a natural number on a named axis, as section 4 has it | the same addendum |

## 2. The ledger's unit, for MSA-I2

You found that decision 5 of ADR-A131 makes an account and its postings an aggregate while the third addendum of 2026-11-16 serialises the owner's ledger, and you leaned to the owner's ledger. That is decided. Decision 5 is narrowed, not withdrawn.

**Three things the word covered, and only one moves.**

| What | Unit | Changed |
|---|---|---|
| who owns a posting | the account, which belongs to its owner and to no occasion | no |
| what a store holds together | a period's unit, named from an account's root and its close | no |
| what a write must see unchanged, what one writer serialises, what is placed in one store | the owner's ledger | yes, it was read as the account |

**Why the account cannot be the consistent unit.** The law that no account on a path falls below zero spans accounts. Take a parent holding 10 with two children. A draw of 6 on each child reads the parent, finds it fits, and writes its own child. Neither writes what the other read, so a guard for each account catches nothing, and the parent stands at minus 2. LG-17 measured this, which is why the writer was decided.

**Why the owner and not the tree.** The accounts joined by `ldg:partOf` and by the purposes they count are the smallest correct unit, but that unit has no stable key, since one new purpose joins two trees. Decision 5 already gathers accounts that interact under one owner, since an account drawn on by several instruments belongs to their ensemble.

**For the census.** Count a read of another account of the same ledger as inside the unit. Only a read from outside a ledger, such as a Behaviour guard reading a balance, crosses a unit.

### 2.1 The placement rule was not taken

You inferred that an identity's Behaviour state goes in the store of the ledger it guards on. The maintainer did not take that rule.

- **A revision orders the whole ledger.** A recorded position orders the postings of one account only. The ledger's revision orders every posting of the ledger, and each pass will record the revision it moved the ledger to.
- **A balance as of a revision does not change.** So a guard outside the ledger reads a fixed fact by naming the revision, and records the revision in its read set. That is a read of a pinned version, the kind the epic's sketch already allows across stores, and no read of changeable state.
- **A write to both needs no atomic change**, as far as we can see. An occasion's state is derived from records, so the posting is the fact and the occasion follows from it.

Co-placing the two is a deployment's choice. If MSA-I2 holds a guard that a read by revision does not cover, say which, with the example it comes from, since the decision rests on there being none.

**What is not built.** The ledger node, its revision and the revision on a pass are terms of the ledger's slice LG-27, which is planned. Until it is built no example carries them, so the census records such a read as "pinned by revision once LG-27 lands" and names the slice.

### 2.2 The cost, and what would reopen it

One owner's accounts are written one posting at a time. A single writer that keeps its balances measured 2,194 commits a second in memory, and on a durable store 83, rising to 1,745 in batches of 100. An owner that needs more, shown by measurement, would reopen the unit as a ledger declared within an owner, with a check that no path, purpose or allocation crosses two.

## 3. The shared proof session, MSA-I5a

MSA-I5 waited on shared types that nothing defines. They get a session of their own, built first as MSA-I5a.

| | |
|---|---|
| Where | `tools/proofs/shared/`, session `LatticeShared`, `session LatticeShared = LatticeBase +` |
| What it holds | a definition only where two developments both use it. Today a position and an amount |
| How it is kept | hand-written, with its claims gated as a layer's are |
| Who imports it | your model, and a layer's theorem theories where they need it |
| Who does not | a generated `Kernel.thy`, which keeps importing `Main` or `Complex_Main` so a layer's formal statement stands by itself |

**The prelude is untouched.** `tools/proofs/base/` still imports library theories and nothing else. A definition there would rebuild the heap every layer parents on at each edit, and it has nothing to gate.

**Your model never imports the ledger's session** while it models persistence alone. The ledger's kernel is generated from the ledger README, and the persistence model rests on no ledger law. When a later slice models a ledger family, importing the ledger's session is the right way round.

**Agreement is proved, not assumed.** The ledger's kernel defines `('k, 'n) amounts = 'k => 'n` for itself. One lemma in a theorem theory of the ledger's session shows that this is the shared session's amount, so a drift between the two fails a build. Where your model and a layer both state a position, the same holds.

**What MSA-I5a delivers.** The directory with its `ROOT` and README, the two definitions with the small laws both developments need, the session wired into the proof task so `mise run check:proofs` builds and gates it, the agreement lemma on the ledger's side, and a Validation Pack. It changes no kernel, so no existing digest moves.

## 4. What a position is

**A position is a natural number on a named axis, and two positions are compared only within one axis.**

| Axis | Who assigns it | Gaps | For example |
|---|---|---|---|
| a sequence | the writer, the next number at each write | none. Position n is the n-th write, and 0 means nothing is written yet | a version row's sequence, an account's recorded position, a ledger's revision |
| an effective axis | the arrangement the records describe | it may skip, and several facts may share one | the day a posting takes effect |

- **A second number orders facts that share a position.** The ledger's micro-position does this for postings recorded together. Your finding MSAI4-04 is the same case: one append writes several events under one sequence, so an event's place is the sequence and its `opSeq`.
- **The ledger's kernel already fits.** Its `counted` takes a day and a recording, both natural numbers.
- **Synonyms now.** The shared session states a position as a synonym for the natural numbers. A type of its own for each axis would have the checker refuse a comparison across axes, but it changes the layers' kernels, which is a decision for another day.

### 4.1 Does it hold in a relational store

Yes, and a relational store makes four rules worth stating, since each has a familiar way to go wrong.

| Rule | Why a relational store needs it said |
|---|---|
| A sequence position is assigned inside the write its axis serialises, as the successor of the value stored | a database's own sequence or identity column leaves gaps on a rollback, and hands out numbers before a commit, so a reader can see 6 before 5 appears. Take the row's lock, or guard on the expected value, and write the stored value plus one |
| It is never a clock, a transaction's identifier or a log position | those differ between stores and need not follow commit order, and a position has to mean the same in every store that holds it. This is also the rule that no `now()` enters an ordering key |
| The axis is in the key | a position alone identifies nothing. The key is the stream and its sequence, the ledger and its revision, or the account, its recorded position and its micro-position. A uniqueness constraint on that key is the store's own guard against two writers taking one position |
| A comparison across axes is prevented by the IR, not by the database | two integer columns compare freely in SQL, and a domain type does not stop it. The neutral IR of MSA-I4 types a position by its axis, and its lowering never emits a comparison of two axes |

Two smaller points.

- **The number is bounded there.** A natural number has no upper bound and a 64-bit integer has. At a million writes a second the bound is reached after about 290,000 years, so the realisation states it as an assumption and the model need not carry it.
- **It is what makes a read portable.** Because our writer assigns a position, "as of revision r" means the same to an RDF store, a relational store and a property graph. A reader in one store pins a read of another by it, and a replica can be asked whether it has reached it.

This is consistent with your MSAI4-05 as decided: the store computes the successor, and the caller's expected current value is the guard.

## 5. The number type

It stays generic.

- What only adds, subtracts and compares is stated once over an ordered ring. A rule that divides names a field. A rule over whole units names the integers. The ledger's kernel is written this way, and its laws are stated once for whole units and for exact amounts.
- Your persistence model stores an amount and computes nothing with it, so there an amount is a value of any type.
- Code exported from a theory fixes a number type when it is exported, the integers for whole units or the rationals for exact amounts. No law is restated to do it.

## 6. Order of work

1. The fixes MSA-F1 to MSA-F6, in the order of the brief of 2026-11-17, are unchanged and still first.
2. MSA-I2, with the ledger's unit as section 2 has it.
3. MSA-I5a, the shared session.
4. MSA-I5, on the shared session.

## 7. What else has changed that you will meet

- **The ledger's vocabulary is about to be reworked.** A [sketch](../sketches/ledger-vocabulary-rework.md) briefs four slices, LG-25 to LG-28, after LG-11: postings with a credit's kind, the amount offered and the cut, requests with their rank, the ledger node and its profile, and the account definition as a versioned thing. The balance record for each account and pass goes. MSA-I7, MSA-I8 and MSA-I10 name the ledger's records, so they wait for it.
- **The merge policy is built.** What an account declares for a merge sits on `ldg:MergePolicy`, which an account definition names.
- **The index.** Ask it before any decision and before any search, as the brief of 2026-11-17 says.

## 8. What to hand back

For MSA-I2, the census with each read marked as inside a ledger, pinned by revision or changeable across a unit, and any guard that a read by revision does not cover. For MSA-I5a, what section 3 lists. Each with its Validation Pack, its board row at `built`, and the index report.
