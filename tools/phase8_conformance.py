# SPDX-License-Identifier: MPL-2.0

"""Phase 8 shared conformance and validation gate."""

from __future__ import annotations

from pathlib import Path

from pyshacl import validate
from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF

from mork_compilers.common import mint
from mork_compilers.eligibility_ir import compile_condition, compile_profile
from mork_compilers.namespaces import ELG, SH
from mork_compilers.shacl_backend import compile_shapes
from mork_compilers.sparql_backend import render_profile_query
from surface.parity import run_shared_surface_parity

CORPUS = Namespace("https://example.org/lattice/test/conformance/")

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


def _sparql_decisions(case: Graph, plan) -> dict:
    return {row.record: ELG[str(row.decision)] for row in case.query(render_profile_query(plan))}


def _shacl_decisions(case: Graph, plan) -> dict:
    """Read the profile shapes' report: Undetermined or Denied when reported, else Permitted."""
    _, report, _ = validate(case, shacl_graph=compile_shapes(plan), advanced=True, inference="none")
    outcome = {
        mint(plan.profile, "profile-undetermined-shape"): ELG.Undetermined,
        mint(plan.profile, "profile-denied-shape"): ELG.Denied,
    }
    reported = {
        report.value(result, SH.focusNode): outcome[report.value(result, SH.sourceShape)]
        for result in report.subjects(RDF.type, SH.ValidationResult)
    }
    return {record: reported.get(record, ELG.Permitted) for record in case.subjects(ELG.forProfile, plan.profile)}


def run_eligibility_cases(manifest_path: Path, root: Path) -> int:
    """Compile every admission profile in each Eligibility case and require both
    its SPARQL and SHACL artefacts to reach the expected decision for every
    record (ADR-A28 parity, conformance corpus README). Returns the case count."""
    manifest = Graph().parse(manifest_path)
    cases = 0
    failures = []
    for case_node in sorted(manifest.subjects(RDF.type, CORPUS.ConformanceCase)):
        if not str(manifest.value(case_node, CORPUS.usesProfile)).startswith(str(ELG)):
            continue  # not an Eligibility case
        case = Graph().parse(manifest_path.parent / str(manifest.value(case_node, CORPUS.caseFile)))
        profiles = sorted(case.subjects(RDF.type, ELG.AdmissionProfile))
        cases += 1
        expected_graph = Graph().parse(manifest_path.parent / str(manifest.value(case_node, CORPUS.expectedFile)))
        expected = {record: value for record, _, value in expected_graph.triples((None, ELG.decisionValue, None))}
        for backend in (_sparql_decisions, _shacl_decisions):
            actual = {}
            for profile in profiles:
                actual.update(backend(case, compile_profile(case, profile)))
            if actual != expected:
                failures.append(f"{case_node} ({backend.__name__}): expected {expected}, got {actual}")
    if failures:
        raise RuntimeError("Eligibility conformance failed:\n" + "\n".join(failures))
    return cases


def main() -> int:
    governance_data = Graph().parse(
        ROOT / "ontology/mork/examples/Governance/GovernanceAndVersioning.ttl",
        format="turtle",
    )
    governance_shapes = Graph().parse(
        ROOT / "ontology/mork/shapes/constraints.ttl",
        format="turtle",
    )
    require_conforms(governance_data, governance_shapes, "MORK governance")

    eligibility_data = Graph().parse(
        ROOT / "ontology/eligibility/examples/interval-containment.ttl",
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

    eligibility_cases = run_eligibility_cases(ROOT / "test/conformance/manifest.ttl", ROOT)
    if not eligibility_cases:
        raise RuntimeError("shared conformance manifest contains no Eligibility cases")

    print(
        f"Phase 8 conformance passed: {len(reports)} Surface parity cases, "
        f"{eligibility_cases} Eligibility cases (SPARQL and SHACL)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
