# SPDX-License-Identifier: MPL-2.0
"""The library against the independently verified anchors and the vectors
generated from the compiler's recipes (identity-minting-specification.md §10)."""

from __future__ import annotations

import json

import pytest

from conftest import ANCHORS, RECIPE_FILES, VECTOR_FILES, load
from lattice_minting import Recipe, verify
from lattice_minting.__main__ import main
from lattice_minting.vectors import generate


def test_anchors_pass():
    report = verify(ANCHORS)
    assert report.failures == []
    assert report.passed >= 70


def test_testdata_present():
    assert len(RECIPE_FILES) == len(VECTOR_FILES) == 7


@pytest.mark.parametrize("path", VECTOR_FILES, ids=lambda p: p.name.split("-")[0])
def test_generated_vectors_pass(path):
    report = verify(path)
    assert report.failures == []
    assert report.passed > 0


@pytest.mark.parametrize("path", VECTOR_FILES, ids=lambda p: p.name.split("-")[0])
def test_generated_vectors_are_current(path):
    """The committed vectors are what this library generates today. A
    failure means a behaviour change: rerun ``mise run build:minting-vectors``
    and review the diff before committing it."""
    committed = load(path)
    assert generate(committed["recipe"]) == committed


@pytest.mark.parametrize("path", RECIPE_FILES, ids=lambda p: p.name.split("-")[0])
def test_recipe_files_match_vectors(path):
    vectors = load(path.with_name(path.name.replace(".recipe.json", ".vectors.json")))
    assert load(path) == vectors["recipe"]
    Recipe.parse(path.read_text(encoding="utf-8"))


def test_anchor_recipes_equal_compiled_recipes(anchors):
    """The compiler reproduces every anchor recipe byte for byte (M1), so the
    generated vectors and the anchors test the same recipes."""
    compiled = {load(p)["recipeDigest"] for p in RECIPE_FILES}
    assert {s["recipe"]["recipeDigest"] for s in anchors["sets"]} == compiled


def test_default_ignorable_only_depends_on_pipeline():
    by_pipeline = {}
    for path in VECTOR_FILES:
        doc = load(path)
        key = doc["recipe"].get("key") or (doc["recipe"].get("claims") or [{}])[0].get("key")
        if key is None:
            continue
        ids = {v["id"] for v in doc["positive"]} | {v["id"] for v in doc["negative"]}
        by_pipeline.setdefault(key["pipeline"]["id"], set()).update(ids)
    assert "neg-default-ignorable-only" in by_pipeline["NfkcTrimCasefold"]
    assert "key-default-ignorable-only-survives" in by_pipeline["NfkcTrimUppercase"]


def test_a_changed_expectation_is_reported(tmp_path):
    doc = load(VECTOR_FILES[0])
    doc["positive"][0]["iri"] += "x"
    bad = tmp_path / "bad.vectors.json"
    bad.write_text(json.dumps(doc), encoding="utf-8")
    report = verify(bad)
    assert len(report.failures) == 1
    assert "iri" in report.failures[0]


def test_a_changed_trace_step_names_the_step():
    doc = load(next(p for p in VECTOR_FILES if p.name.startswith("Product")))
    vec = doc["positive"][0]
    tuple_ix = next(i for i, s in enumerate(vec["trace"]) if s["step"] == "tuple")
    vec["trace"][tuple_ix]["hex"] = "00"
    report = verify(doc)
    assert any(f"step {tuple_ix} (tuple)" in f for f in report.failures)


def test_cli(tmp_path, capsys):
    assert main(["verify", str(ANCHORS), *map(str, VECTOR_FILES)]) == 0
    assert main([]) == 2
    doc = load(VECTOR_FILES[0])
    doc["negative"][0]["error"] = "PatternMismatch" if doc["negative"][0]["error"] != "PatternMismatch" else "MissingSecret"
    bad = tmp_path / "bad.vectors.json"
    bad.write_text(json.dumps(doc), encoding="utf-8")
    assert main(["verify", str(bad)]) == 1
    assert "FAIL" in capsys.readouterr().out
