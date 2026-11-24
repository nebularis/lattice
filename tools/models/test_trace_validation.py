# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI
"""Tests of the trace validation's reading of TLC's dump, its counts and its tree of IR commands (tools/models/trace_validation.py). They
need neither Java, TLC nor Isabelle."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import trace_validation as tv  # noqa: E402


def test_values_tlc_prints_are_read():
    assert tv.tla_value("<<>>") == ()
    assert tv.tla_value("<<1, \"a\">>") == (1, "a")
    assert tv.tla_value("{w1, w2}") == frozenset({"w1", "w2"})
    assert tv.tla_value("{}") == frozenset()
    assert tv.tla_value("[epoch |-> 1, seq |-> 0]") == {"epoch": 1, "seq": 0}
    assert tv.tla_value("(w1 :> FALSE @@ w2 :> TRUE)") == {"w1": False, "w2": True}
    assert tv.tla_value("<<[w |-> w1, pos |-> 1, epoch |-> 1, at |-> 2]>>") == ({"w": "w1", "pos": 1, "epoch": 1, "at": 2},)
    assert tv.tla_value("[out |-> \"none\", dels |-> {<<\"seq\", 0>>}, ins |-> {}]") == {
        "out": "none", "dels": frozenset({("seq", 0)}), "ins": frozenset()}


def test_a_state_is_read_conjunct_by_conjunct_over_several_lines():
    state = tv.tla_state("/\\ seq = 0\n/\\ pc = (w1 :> \"start\" @@\n   w2 :> \"issue\")\n/\\ log = <<>>")
    assert state == {"seq": 0, "pc": {"w1": "start", "w2": "issue"}, "log": ()}


DOT = "\n".join([
    "strict digraph DiskGraph {",
    '1 [label="/\\\\ x = 0",style = filled]',
    '1 -> 2 [label="A",color="black",fontcolor="black"];',
    '2 [label="/\\\\ x = 1"];',
    '1 -> 3 [label="B",color="black",fontcolor="black"];',
    '3 [label="/\\\\ x = 2"];',
    '2 -> 4 [label="C",color="black",fontcolor="black"];',
    '4 [label="/\\\\ x = 3"];',
    '3 -> 4 [label="C",color="black",fontcolor="black"];',
    '3 -> 4 [label="C",color="black",fontcolor="black"];',
    "}",
])


def test_the_dump_gives_the_states_the_initial_state_and_each_step_once():
    graph = tv.read_dot(DOT)
    assert graph.inits == ["1"]
    assert {n: s["x"] for n, s in graph.states.items()} == {"1": 0, "2": 1, "3": 2, "4": 3}
    assert graph.edges == [("1", "2", "A"), ("1", "3", "B"), ("2", "4", "C"), ("3", "4", "C")]


def test_behaviours_and_their_steps_are_counted_once_in_each_behaviour():
    graph = tv.read_dot(DOT)
    count, steps, weighted = tv.behaviours(graph, lambda e: 1 if graph.edges[e][2] == "C" else 0)
    assert (count, steps, weighted) == (2, 4, 2)


def test_the_trace_configuration_keeps_typeok_alone():
    cfg = "SPECIFICATION Spec\nCONSTANTS\n    K = 3\n    Mode = \"Atomic\"\nINVARIANTS\n    TypeOK\n    OneOwner\nPROPERTIES\n    Live\n"
    assert tv.trace_cfg(cfg) == "SPECIFICATION Spec\nCONSTANTS\n    K = 3\n    Mode = \"Atomic\"\nINVARIANT\n    TypeOK\n"
    assert tv.constants(cfg) == {"K": "3", "Mode": "Atomic"}


def test_the_tree_shares_a_prefix_and_writes_a_parent_before_its_child():
    tree = tv.Tree()
    root = tree.root((("SV", "stream", "1", "0", ""), ("SD", "1")))
    a = tree.child(root, ("C", "claim", "k1", (("PA", "ClaimP", "c"), ("PA", "OwnerP", "o1"))))
    assert tree.child(root, ("C", "claim", "k1", (("PA", "ClaimP", "c"), ("PA", "OwnerP", "o1")))) == a
    b = tree.child(a, ("X", "depoch", "2"))
    assert (root, a, b) == (1, 2, 3)
    assert tree.records == ["R\t1", "SV\tstream\t1\t0\t", "SD\t1", "N\t2\t1\tC\tclaim\tk1", "PA\tClaimP\tc", "PA\tOwnerP\to1",
                            "N\t3\t2\tX\tdepoch\t2"]


def _b_state(**changes) -> dict:
    state = {"dEpoch": 1, "row": {"epoch": 1, "seq": 0}, "log": (), "txns": frozenset(), "pc": {"w1": "ready", "w2": "ready"},
             "epochOf": {"w1": 1, "w2": 1}, "reply": {"w1": "none", "w2": "none"}}
    state.update(changes)
    return state


def test_model_b_reads_an_append_as_the_ir_command_and_a_bump_as_a_step_it_has_no_command_for():
    mapping = tv.ModelB({})
    before = _b_state()
    after = _b_state(row={"epoch": 1, "seq": 1}, log=({"w": "w1", "pos": 1, "epoch": 1, "at": 1},), txns=frozenset({"w1"}),
                     pc={"w1": "replied", "w2": "ready"}, reply={"w1": "Applied", "w2": "none"})
    step = mapping.step(before, after, "Exec")
    assert step.kind == "ir" and step.outcome == "Applied"
    assert step.key[:3] == ("C", "append", "-") and ("PN", "EpochP", "1") in step.key[3] and ("PA", "TxnId", "txn-w1") in step.key[3]
    assert mapping.step(before, _b_state(dEpoch=2), "BumpStep") == tv.Step("ext", ("X", "depoch", "2"))
    assert mapping.step(before, _b_state(pc={"w1": "evaluated", "w2": "ready"}), "Eval").kind == "none"
    assert mapping.model_lines(after) == ["depoch=1", "evt 1 ev-w1", "rcpt 1 1 txn-w1", "row epoch=1 seq=1", "txn txn-w1"]


def test_the_ir_state_is_read_into_the_same_lines():
    dump = ["depoch\t1", "evrow\tstream\t1\tev-w1", "rcpt\tstream\t1\t1\trev=rev/0000000000000000001\tprev=-\ttxn=txn-w1",
            "txn\ttxn-w1\trev=rev/0000000000000000001\tdigest=digest-w1",
            "vrow\tstream\tepoch=1\tseq=1\thead=rev/0000000000000000001\tdeleted=false"]
    assert tv.ModelB({}).ir_lines(dump) == ["depoch=1", "evt 1 ev-w1", "rcpt 1 1 txn-w1", "row epoch=1 seq=1", "txn txn-w1"]
    assert tv.ModelD({}).ir_lines(["claim\tclaim-1\tconstraint=k1\towner=o1"]) == ["claim constraint=k1", "owner o1"]
