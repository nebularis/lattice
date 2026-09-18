# SPDX-License-Identifier: MPL-2.0

"""Phase 8 shared conformance and validation gate."""

from __future__ import annotations

from pathlib import Path

from pyshacl import validate
from rdflib import Graph, URIRef

from tools.mork_compilers.eligibility_ir import compile_condition
from tools.mork_compilers.shacl_backend import compile_shapes
from tools.surface.parity import run_shared_surface_parity

ROOT = Path(__file__).resolve().parents[1]
CONDITION = URIRef(
    "https://example.org/lattice/eligibility/minimum-credit-condition"
)


def require_conforms(data: Graph, shapes: Graph, label: str) -> None:
    conforms, _, report = validate(
        data_graph=data,
        shacl_graph=shapes,
        advanced=True,
        inference="none",
    )
    if not conforms:
        raise RuntimeError(f"{label} failed SHACL validation:\n{report}")


def main() -> int:
    governance_data = Graph().parse(
        ROOT / "mork/examples/Governance/GovernanceAndVersioning.ttl",
        format="turtle",
    )
    governance_shapes = Graph().parse(
        ROOT / "mork/shapes/constraints.ttl",
        format="turtle",
    )
    require_conforms(governance_data, governance_shapes, "MORK governance")

    eligibility_data = Graph().parse(
        ROOT / "eligibility/examples/interval-containment.ttl",
        format="turtle",
    )
    eligibility_shapes = compile_shapes(
        compile_condition(eligibility_data, CONDITION)
    )
    require_conforms(
        eligibility_data,
        eligibility_shapes,
        "generated Eligibility shapes",
    )

    reports = run_shared_surface_parity(
        ROOT / "test/conformance/manifest.ttl",
        ROOT,
        "2026-09-18T00:00:00Z",
    )
    if not reports:
        raise RuntimeError("shared conformance manifest contains no Surface cases")
    failures = [case for case, report in reports if not report.holds()]
    if failures:
        raise RuntimeError("Surface parity failed: " + ", ".join(failures))

    print(f"Phase 8 conformance passed: {len(reports)} Surface parity cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
