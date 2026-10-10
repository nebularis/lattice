# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""A small model of two overlapping writers on one aggregate, under snapshot isolation with
statement-level first-committer-wins (the store capabilities ``detectsWriteWriteConflict`` and
``statementLevelConflictDetection``). It is a model of the rule, not a store. It answers one
question the note asks: which pairs of operations need to meet on a shared statement for the
aggregate to stay correct, and which version-row disciplines make them meet.

A transaction reads a snapshot, computes its writes from it, and commits if no statement in its
write set was written by a transaction that committed after the snapshot was taken. A guard that
only reads, such as "the unit is not deleted", takes no part in conflict detection."""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import permutations

# ------------------------------------------------------------------ the aggregate

# unit -> parent unit. A unit is a node that owns a version row.
UNITS = {"P": None, "L1": "P", "L2": "P", "B1": "L1"}
BINDING_LIMIT = 3  # a cross-level invariant: at most this many bindings under the tower

OWNED = {"hasLayer", "hasBinding", "hasShare", "hasMarket"}


def initial_state() -> frozenset:
    t = {
        ("P", "hasMarket", "M1"),
        ("P", "hasLayer", "L1"), ("P", "hasLayer", "L2"),
        ("L1", "hasBinding", "B1"), ("L2", "hasBinding", "B2"),
        ("B1", "hasShare", "S1"),
        ("B1", "data", "d1"), ("B2", "data", "d2"), ("S1", "data", "d3"), ("M1", "data", "d4"),
    }
    for unit in UNITS:
        t.add((unit, "v", "0"))
    return frozenset(t)


def children(state, node):
    return {o for s, p, o in state if s == node and p in OWNED}


def closure(state, node) -> set:
    out, stack = set(), [node]
    while stack:
        n = stack.pop()
        for c in children(state, n):
            if c not in out:
                out.add(c)
                stack.append(c)
    return out


def descendants_units(state, unit) -> set:
    return {n for n in closure(state, unit) if n in UNITS}


def ancestors(unit):
    while UNITS[unit] is not None:
        unit = UNITS[unit]
        yield unit


def version(state, unit):
    return next(o for s, p, o in state if s == unit and p == "v")


def deleted(state, unit) -> bool:
    return (unit, "deleted", "true") in state


# ------------------------------------------------------------------ disciplines

@dataclass(frozen=True)
class Discipline:
    name: str
    rows: str  # "root" | "level"
    removal_marks_descendants: bool = False
    writers_touch_ancestors: bool = False
    invariant_row: bool = False


DISCIPLINES = [
    Discipline("D0 one row at the root (today)", rows="root"),
    Discipline("D1 one row per level", rows="level"),
    Discipline("D2 per level, removal marks the sub-units", rows="level", removal_marks_descendants=True),
    Discipline("D3 per level, writers touch every ancestor", rows="level", writers_touch_ancestors=True),
    Discipline("D4 D2 plus a row for the declared invariant", rows="level", removal_marks_descendants=True, invariant_row=True),
]


@dataclass
class Plan:
    adds: set = field(default_factory=set)
    dels: set = field(default_factory=set)
    refused: str = ""

    @property
    def writes(self) -> set:
        return self.adds | self.dels


def _bump(plan: Plan, state, unit):
    plan.dels.add((unit, "v", version(state, unit)))
    plan.adds.add((unit, "v", str(int(version(state, unit)) + 1)))


def _row_for(d: Discipline, unit: str) -> str:
    return "P" if d.rows == "root" else unit


# Operations. Each takes the snapshot and returns a Plan. ``unit`` is where the operation acts.

def add_market(state, d, new="M2") -> Plan:
    plan = Plan()
    if deleted(state, "P"):
        plan.refused = "deleted"
        return plan
    plan.adds |= {("P", "hasMarket", new), (new, "data", "x")}
    _bump(plan, state, _row_for(d, "P"))
    return plan


def add_binding(state, d, layer, new) -> Plan:
    """Add a binding under a layer. Checks the cross-level invariant against the snapshot."""
    plan = Plan()
    if deleted(state, layer):
        plan.refused = "deleted"
        return plan
    count = sum(1 for s, p, o in state if p == "hasBinding")
    if count >= BINDING_LIMIT:
        plan.refused = "invariant"
        return plan
    plan.adds |= {(layer, "hasBinding", new), (new, "data", "x")}
    _bump(plan, state, _row_for(d, layer))
    if d.writers_touch_ancestors:
        for a in ancestors(layer):
            _bump(plan, state, a)
    if d.invariant_row:
        _bump_invariant(plan, state)
    return plan


def add_share(state, d, binding_unit, new) -> Plan:
    plan = Plan()
    if deleted(state, binding_unit):
        plan.refused = "deleted"
        return plan
    plan.adds |= {(binding_unit, "hasShare", new), (new, "data", "x")}
    _bump(plan, state, _row_for(d, binding_unit))
    if d.writers_touch_ancestors:
        for a in ancestors(binding_unit):
            _bump(plan, state, a)
    return plan


def _bump_invariant(plan: Plan, state):
    current = next((o for s, p, o in state if s == "INV" and p == "v"), "0")
    plan.dels.add(("INV", "v", current))
    plan.adds.add(("INV", "v", str(int(current) + 1)))


def remove_subtree(state, d, unit) -> Plan:
    """Remove a unit and everything it owns, and the edge from its parent."""
    plan = Plan()
    if deleted(state, unit):
        plan.refused = "deleted"
        return plan
    gone = {unit} | closure(state, unit)
    plan.dels |= {t for t in state if t[0] in gone and t[1] != "v"}
    parent = UNITS[unit]
    plan.dels |= {t for t in state if t[2] == unit and t[1] in OWNED}
    _bump(plan, state, _row_for(d, parent or unit))
    if d.rows == "level":
        plan.adds.add((unit, "deleted", "true"))
        _bump(plan, state, unit)
    if d.removal_marks_descendants:
        for sub in descendants_units(state, unit):
            plan.adds.add((sub, "deleted", "true"))
            _bump(plan, state, sub)
    return plan


def delete_root(state, d) -> Plan:
    plan = remove_subtree(state, d, "P")
    return plan


# ------------------------------------------------------------------ running a pair

@dataclass
class Outcome:
    committed: tuple[bool, bool]
    refused: tuple[str, str]
    anomalies: list[str]

    def label(self) -> str:
        if self.anomalies:
            return "ANOMALY " + "+".join(self.anomalies)
        a, b = self.committed
        if a and b:
            return "both commit"
        if not a and not b:
            return "refused"
        return "one conflicts"


def _apply(state: frozenset, plan: Plan) -> frozenset:
    return frozenset((set(state) - plan.dels) | plan.adds)


def _anomalies(final: frozenset) -> list[str]:
    found = []
    live_roots = {n for n in ("P",) if not deleted(final, n) and any(s == n for s, _, _ in final)}
    reachable = set(live_roots)
    for r in live_roots:
        reachable |= closure(final, r)
    stray = {s for s, p, o in final if p not in {"v", "deleted"} and s not in reachable and s != "INV"}
    if stray:
        found.append("orphan")
    bindings = sum(1 for s, p, o in final if p == "hasBinding")
    if bindings > BINDING_LIMIT:
        found.append("invariant")
    return found


def overlap(initial: frozenset, first, second) -> Outcome:
    """Both transactions take their snapshot before either commits, then ``first`` commits, then ``second``."""
    plans = [first(initial), second(initial)]
    state = initial
    committed = [False, False]
    for i, plan in enumerate(plans):
        if plan.refused:
            continue
        if i == 1 and plans[0] and committed[0] and (plan.writes & plans[0].writes):
            continue  # first-committer-wins on a shared statement
        state = _apply(state, plan)
        committed[i] = True
    return Outcome((committed[0], committed[1]), (plans[0].refused, plans[1].refused), _anomalies(state) if all(committed) or any(committed) else [])


def run_pair(op_a, op_b, d: Discipline) -> Outcome:
    """The worse of the two commit orders."""
    state = initial_state()
    results = [overlap(state, lambda s: op_a(s, d), lambda s: op_b(s, d)), overlap(state, lambda s: op_b(s, d), lambda s: op_a(s, d))]
    for r in results:
        if r.anomalies:
            return r
    return results[0] if results[0].label() != "both commit" else results[1]


PAIRS = {
    "root edit  vs deep edit":              (lambda s, d: add_market(s, d), lambda s, d: add_share(s, d, "B1", "S2"), True),
    "deep edit  vs deep edit, other branch": (lambda s, d: add_share(s, d, "B1", "S2"), lambda s, d: add_binding(s, d, "L2", "B3"), True),
    "deep edit  vs deep edit, same unit":   (lambda s, d: add_share(s, d, "B1", "S2"), lambda s, d: add_share(s, d, "B1", "S3"), False),
    "root edit  vs root edit":              (lambda s, d: add_market(s, d, "M2"), lambda s, d: add_market(s, d, "M3"), False),
    "remove L1  vs deep edit below L1":     (lambda s, d: remove_subtree(s, d, "L1"), lambda s, d: add_share(s, d, "B1", "S2"), False),
    "remove L1  vs add binding under L1":   (lambda s, d: remove_subtree(s, d, "L1"), lambda s, d: add_binding(s, d, "L1", "B3"), False),
    "remove L1  vs edit in L2":             (lambda s, d: remove_subtree(s, d, "L1"), lambda s, d: add_binding(s, d, "L2", "B3"), True),
    "delete root vs deep edit":             (lambda s, d: delete_root(s, d), lambda s, d: add_share(s, d, "B1", "S2"), False),
    "delete root vs root edit":             (lambda s, d: delete_root(s, d), lambda s, d: add_market(s, d), False),
    "two bindings, limit of 3 (L1 / L2)":   (lambda s, d: add_binding(s, d, "L1", "B3"), lambda s, d: add_binding(s, d, "L2", "B4"), False),
}


def matrix() -> dict[str, dict[str, Outcome]]:
    return {name: {d.name: run_pair(a, b, d) for d in DISCIPLINES} for name, (a, b, _independent) in PAIRS.items()}


def independent(name: str) -> bool:
    return PAIRS[name][2]
