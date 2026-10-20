# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""H2.6g: every NOT EXISTS reads the graph it means (formal-methods track H, plan 4.17, TSD-34). rdflib 7.6.0 can evaluate a `FILTER NOT EXISTS` that has no
`GRAPH` of its own, inside a `GRAPH` block, against the default graph once the block has yielded a solution, depending on `PYTHONHASHSEED`. These tests list the
builders and templates that had the shape, show on rdflib (over a sweep of hash seeds, each in a child process) and on Oxigraph what the defect could change in
each, and hold the builders and the templates to the rule that a `NOT EXISTS` inside a `GRAPH` block names its graph. Validation Pack:
docs/developer/validation/FMH-H2-6g.md. Test IDs are H2.6g-Tn."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from rdflib import Dataset

import engines
import tsd34_support as support
from persistence.builders import BUILDERS, build
from persistence.ir_render import render

from test_builders import _ported

TEMPLATES = Path(__file__).resolve().parents[1] / "src" / "persistence" / "templates"
SEEDS = range(16)


# ---- the shape, found in text -----------------------------------------------------------------------------------------------------------------------


def exposed_in(text: str) -> list[str]:
    """The `[NOT] EXISTS` bodies of `text` that sit inside a `GRAPH` block and do not begin with a `GRAPH` of their own. A small scan of braces, so it
    reads the rendered SPARQL and a Mustache template alike (a `{{{name}}}` tag is one token)."""
    text = re.sub(r"\{\{\{\w+\}\}\}", "TAG", text)
    text = re.sub(r"\{\{![^}]*\}\}", "", text, flags=re.S)  # a Mustache comment
    tokens = re.findall(r'"[^"\n]*"(?:\^\^\S+)?|<[^<>\s]*>|\{|\}|GRAPH|FILTER\s+(?:NOT\s+)?EXISTS|[^\s{}]+', text)
    stack: list[str] = []  # "graph", "exists" or "other", innermost last
    out: list[str] = []
    pending = None
    for i, tok in enumerate(tokens):
        if tok == "GRAPH":
            pending = "graph"
        elif re.fullmatch(r"FILTER\s+(?:NOT\s+)?EXISTS", tok):
            pending = "exists"
            if "graph" in stack and not (i + 3 < len(tokens) and tokens[i + 1] == "{" and tokens[i + 2] == "GRAPH"):
                out.append(" ".join(tokens[i:i + 8]))
        elif tok == "{":
            # a GRAPH is followed by its name and then the brace
            stack.append(pending or "other")
            pending = None
        elif tok == "}":
            stack.pop()
    return out


def test_h2_6g_t0_the_scan_finds_the_shape_and_passes_a_body_that_names_its_graph():
    bad = "SELECT * WHERE { GRAPH <urn:g> { ?s ?p ?o . FILTER NOT EXISTS { ?s <urn:d> true } } }"
    good = "SELECT * WHERE { GRAPH <urn:g> { ?s ?p ?o . FILTER NOT EXISTS { GRAPH <urn:g> { ?s <urn:d> true } } } }"
    top = "SELECT * WHERE { GRAPH <urn:g> { ?s ?p ?o } FILTER NOT EXISTS { ?s <urn:d> true } }"  # outside a GRAPH block it reads the default graph by design
    assert len(exposed_in(bad)) == 1 and exposed_in(good) == [] and exposed_in(top) == []
    assert len(exposed_in("GRAPH {{{g}}} { FILTER EXISTS { ?s ?p ?o } }")) == 1


def test_h2_6g_t1_no_rendered_operation_and_no_template_has_a_not_exists_without_its_own_graph_inside_a_graph_block():
    rendered = {stem: render(build(stem, context)) for _, _, stem, context in _ported()}
    assert set(rendered) == set(BUILDERS)
    assert {stem: found for stem, text in rendered.items() if (found := exposed_in(text))} == {}
    templates = sorted(TEMPLATES.glob("*.mustache"))
    assert len(templates) >= len(BUILDERS)
    assert {path.name: found for path in templates if (found := exposed_in(path.read_text(encoding="utf-8")))} == {}


# ---- what the defect could change -------------------------------------------------------------------------------------------------------------------

WRITES = sorted(
    stem for stem in BUILDERS
    if stem.startswith(("append-version", "cas-replace-composite", "cas-replace-named", "tombstone-delete"))
)


@pytest.fixture(scope="module")
def tombstoned():
    return {stem: support.scenario(stem) for stem in WRITES}, {stem: support.scenario(stem, deleted=False) for stem in WRITES}


@engines.each_engine
def test_h2_6g_t2_a_write_to_a_tombstoned_row_changes_nothing_on_any_of_sixteen_hash_seeds_and_on_oxigraph_and_a_live_row_is_written(tombstoned):
    """The guard of every in-place write and of the version appends is `FILTER NOT EXISTS { $root pat:deleted true }` in the row's `GRAPH` block, which holds
    several solutions here (the row has three heads and three current versions, so up to nine). The solutions of that block share one context (T3), so on
    rdflib the test of every solution after the first kept one is made against the default graph. That cannot change an outcome. The body mentions
    only `$root`, a parameter with one value in every solution, so every solution passes or every solution fails. The first solution of a tombstoned row
    fails, nothing is yielded, and `evalGraph` has nothing to reset. A solution can only be kept wrongly after another was kept rightly, and that needs
    a body that depends on a solution variable. The sweep is the evidence, and the control (a live row, which is written) shows the scenario is sound.
    rdflib runs the sweep in child processes, and Oxigraph, which has no such defect, runs each scenario once."""
    dead, live = tombstoned
    if engines.CURRENT == "rdflib":
        dead_outcomes, live_outcomes = support.sweep(dead, SEEDS), support.sweep(live, SEEDS)
    else:
        dead_outcomes = {stem: {support.run_scenario(sc, engines.dataset())} for stem, sc in dead.items()}
        live_outcomes = {stem: {support.run_scenario(sc, engines.dataset())} for stem, sc in live.items()}
    assert {stem for stem, o in dead_outcomes.items() if o != {False}} == set(), "written to a tombstoned row"
    assert {stem for stem, o in live_outcomes.items() if o != {True}} == set(), "not written to a live row"


def test_h2_6g_t3_the_solutions_of_a_row_block_share_one_context_on_rdflib_so_the_precondition_of_the_defect_holds(tombstoned):
    """Why T2 needs its argument: the defect's precondition holds in these blocks. If rdflib stops sharing a context here, this fails, and TSD-34 and the
    comment of T2 are revisited."""
    import collections

    import rdflib.plugins.sparql.evaluate as evaluate

    seen = collections.Counter()
    original = evaluate.evalGraph

    def counting(ctx, part):
        for x in original(ctx, part):
            seen[id(x.ctx)] += 1
            yield x

    evaluate.evalGraph = counting
    try:
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            assert support.run_scenario(tombstoned[1]["cas-replace-composite-property"], Dataset())
    finally:
        evaluate.evalGraph = original
    assert max(seen.values()) >= 3, dict(seen)


def test_h2_6g_t4_the_members_read_is_right_at_every_version_on_sixteen_hash_seeds():
    """`members` had two `NOT EXISTS` bodies with no `GRAPH`, in its one block, and they depend on `?cp`, `?w` and `?member`, so unlike the guards of T2 a
    wrong test could keep a stray member. No history we built exposed it on the original text (the solutions of its block do not share a context, which
    the version of rdflib may change), and this holds the text that names its graph to the reference on the same sweep."""
    assert support.sweep_members(SEEDS) == {"[]"}


@engines.each_engine
def test_h2_6g_t4o_members_is_right_on_each_engine():
    assert support.members_probe() == []
