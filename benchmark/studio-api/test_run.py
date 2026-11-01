# SPDX-License-Identifier: MPL-2.0
"""The benchmark's own tests. They start no studio."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("studio_api_run", Path(__file__).with_name("run.py"))
run = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
spec.loader.exec_module(run)  # type: ignore[union-attr]


@pytest.mark.parametrize("size", run.SIZES)
def test_a_part_has_exactly_the_triples_asked_for(size: int) -> None:
    pytest.importorskip("rdflib")
    assert run.triples(run.part(size, "t")) == size


def test_a_part_is_deterministic_and_differs_by_its_tag_only() -> None:
    assert run.part(100, "a") == run.part(100, "a")
    assert run.part(100, "a").replace('"a"', '"b"') == run.part(100, "b")


def test_a_wrong_status_fails_the_run() -> None:
    with pytest.raises(run.WrongResult):
        run.expect("x", run.Reply(500, b"boom"), 200)
