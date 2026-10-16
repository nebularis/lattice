# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Defects found by formal-methods track H that are not fixed yet, each
asserted as the behaviour it should have and marked as a strict expected
failure.

While the defect stands, the test is reported as xfail and the suite stays
green. When someone fixes the defect, the test starts to pass, strict mode
turns that into a failure, and the fixer removes the marker and the entry in
``docs/developer/plans/technical-debt.md``. Each reason names its register entry.
"""

from __future__ import annotations

import pytest
from rdflib import Graph

from persistence import witness
from persistence.compiler import compile_targets

PREFIXES = """
@prefix dal: <https://www.nebularis.org/neuro-semantic/lattice/persistence#> .
@prefix ex:  <https://example.org/lending#> .
"""


@pytest.mark.xfail(strict=True, reason="TD-23: a class named only by dal:coversClass is never compiled")
def test_a_class_covered_only_by_a_graph_pattern_scope_is_compiled():
    graph = witness._load_fixture(witness.EXAMPLES_DIR / "warning-mixed-receipt-model.ttl")
    compiled = {str(ct.target.cls).rsplit("#", 1)[-1] for ct in compile_targets(graph)}
    assert compiled == {"Widget", "Gadget"}
