# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""
Surface/source parity — the discharge of law ``srf:R2``.

A surface is trustworthy only if asking it a question and asking the source the
same question give the same answer. Both sides of that comparison are already
required to exist under ADR-A15, so the check is cheap; what it needs is a
SPARQL engine, which is why it arrives with rdflib and not before.

The comparison runs per population member, per index form:

``MembershipAssertion``
    source — instances whose read path reaches the member;
    surface — instances typed into the member's generated class.

``ClosureRelation``
    source — instances whose read path reaches some value standing below the
    member in the reflexive-transitive closure of the declared basis, within
    the declared scope;
    surface — instances the generated relation carries to the member.

``DirectProperty``
    source — the values the read path reaches;
    surface — the values the generated property carries.

Where the two disagree the surface is wrong by construction: the source is
authoritative and the surface is a restatement of it.

**What cannot be checked here.** A ``DefinitionOnly`` surface asserts nothing;
its memberships are entailments under the profile's declared entailment regime,
and rdflib is not a reasoner. Those forms are reported as skipped, with the
regime named, rather than silently passed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF

from .compile import (
    CLOSURE,
    DIRECT,
    MEMBERSHIP,
    NOMINAL,
    CompiledSurface,
    ancestors,
    carrier_instances,
    enumerate_population,
    evaluate_path,
)
from .namespaces import RDF, SRF
from .naming import Minter

CONFORMANCE = Namespace("https://example.org/lattice/test/conformance/")


@dataclass
class ParityFinding:
    form: str
    subject: str
    only_in_source: List[str] = field(default_factory=list)
    only_in_surface: List[str] = field(default_factory=list)

    def ok(self) -> bool:
        return not self.only_in_source and not self.only_in_surface

    def describe(self) -> str:
        parts = [f"{self.form} for {self.subject}"]
        if self.only_in_source:
            parts.append("  source only:  " + ", ".join(sorted(self.only_in_source)))
        if self.only_in_surface:
            parts.append("  surface only: " + ", ".join(sorted(self.only_in_surface)))
        return "\n".join(parts)


@dataclass
class ParityReport:
    contract: str
    checked: int = 0
    findings: List[ParityFinding] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)

    @property
    def failures(self) -> List[ParityFinding]:
        return [f for f in self.findings if not f.ok()]

    def holds(self) -> bool:
        return not self.failures

    def describe(self) -> str:
        lines = [f"{self.contract}: {self.checked} comparison(s)"]
        for skip in self.skipped:
            lines.append(f"  skipped: {skip}")
        for failure in self.failures:
            lines.append(failure.describe())
        if self.holds():
            lines.append("  parity holds")
        return "\n".join(lines)


def _surface_graph(compiled: CompiledSurface) -> Graph:
    """The union of the emitted content modules, which is what a consumer would load."""
    union = Graph()
    for module in compiled.content_modules():
        for triple in module:
            union.add(triple)
    return union


def check_parity(compiled: CompiledSurface, source: Graph) -> ParityReport:
    """Compare every question the surface claims to answer against the source."""
    contract = compiled.contract
    report = ParityReport(contract=str(contract.iri))

    if not contract.is_index:
        return _promotion_parity(compiled, source, report)

    surface = _surface_graph(compiled)
    minter = Minter(
        target_namespace=contract.target_namespace,
        contract_key=contract.key,
        carrier=str(contract.carrier),
        normalisation=contract.profile.naming_normalisation,
        naming_policy=contract.naming_policy or "",
        naming_prefix=contract.naming_prefix,
    )
    instances = carrier_instances(source, contract.carrier)
    population, _ = enumerate_population(source, contract.population, at=compiled.produced_at)

    reached: Dict[str, Set[str]] = {
        str(instance): {
            str(value)
            for value in evaluate_path(source, instance, contract)
            if isinstance(value, URIRef)
        }
        for instance in instances
    }

    if contract.has_form(MEMBERSHIP):
        for member in population:
            expected = {i for i, values in reached.items() if str(member) in values}
            symbol = minter.nominal_class(str(member))
            actual = {str(s) for s in surface.subjects(RDF.type, symbol)}
            report.checked += 1
            report.findings.append(
                ParityFinding(
                    form="MembershipAssertion",
                    subject=str(member),
                    only_in_source=sorted(expected - actual),
                    only_in_surface=sorted(actual - expected),
                )
            )
    elif contract.has_form(NOMINAL):
        report.skipped.append(
            f"NominalClass is definition-only under {contract.profile.entailment_regime}; "
            f"membership is entailed, not asserted, and no reasoner is in the loop"
        )

    if contract.has_form(CLOSURE):
        scope: Optional[Set[str]] = None
        if contract.closure_scope is not None:
            scope_members, _ = enumerate_population(
                source, contract.closure_scope, at=compiled.produced_at
            )
            scope = {str(m) for m in scope_members}
        relation = minter.closure_relation()
        if contract.emits_assertions:
            for member in population:
                expected = {
                    instance
                    for instance, values in reached.items()
                    if any(
                        str(member) in {str(a) for a in ancestors(source, URIRef(v), contract.closure_basis, scope)}
                        for v in values
                    )
                }
                actual = {str(s) for s in surface.subjects(relation, member)}
                report.checked += 1
                report.findings.append(
                    ParityFinding(
                        form="ClosureRelation",
                        subject=str(member),
                        only_in_source=sorted(expected - actual),
                        only_in_surface=sorted(actual - expected),
                    )
                )
        else:
            report.skipped.append(
                "ClosureRelation ships a SHACL rule rather than assertions; parity needs "
                "the rule to have been executed against the current read set"
            )

    if contract.has_form(DIRECT) and contract.emits_assertions:
        direct = minter.direct_property()
        for instance in instances:
            expected = reached[str(instance)]
            actual = {str(o) for o in surface.objects(instance, direct)}
            report.checked += 1
            report.findings.append(
                ParityFinding(
                    form="DirectProperty",
                    subject=str(instance),
                    only_in_source=sorted(expected - actual),
                    only_in_surface=sorted(actual - expected),
                )
            )
    return report


def _promotion_parity(
    compiled: CompiledSurface, source: Graph, report: ParityReport
) -> ParityReport:
    contract = compiled.contract
    if not contract.emits_assertions:
        report.skipped.append(
            "definition-only promotion emits a property chain; parity needs a reasoner "
            f"supporting {contract.profile.entailment_regime}"
        )
        return report

    surface = _surface_graph(compiled)
    for instance in carrier_instances(source, contract.carrier):
        expected = {str(v) for v in evaluate_path(source, instance, contract)}
        actual = {str(o) for o in surface.objects(instance, contract.promotes_to)}
        report.checked += 1
        report.findings.append(
            ParityFinding(
                form="Promotion",
                subject=str(instance),
                only_in_source=sorted(expected - actual),
                only_in_surface=sorted(actual - expected),
            )
        )
    return report


def run_shared_surface_parity(
    manifest_path: str | Path,
    root: str | Path = ".",
    produced_at: str = "2026-09-18T00:00:00Z",
) -> List[Tuple[str, ParityReport]]:
    """Run Surface parity for explicit Surface cases in the shared corpus.

    A shared-corpus case opts into this runner with ``ex:surfaceContractFile``
    and ``ex:surfaceContractKey``. Existing Eligibility and Behaviour cases
    remain untouched because they do not declare those fields.
    """
    from .model import read_contracts
    from .serialise import parse_files
    from .compile import SurfaceCompiler

    root_path = Path(root)
    manifest = Graph().parse(str(manifest_path), format="turtle")
    reports: List[Tuple[str, ParityReport]] = []
    for case in sorted(manifest.subjects(RDF.type, CONFORMANCE.ConformanceCase), key=str):
        contract_file = manifest.value(case, CONFORMANCE.surfaceContractFile)
        contract_key = manifest.value(case, CONFORMANCE.surfaceContractKey)
        if contract_file is None or contract_key is None:
            continue
        declarations = parse_files([str(root_path / str(contract_file))])
        source = declarations
        contracts = [contract for contract in read_contracts(declarations)
                     if contract.key == str(contract_key)]
        if not contracts:
            raise ValueError(f"shared Surface case {case} names no contract {contract_key}")
        compiled = SurfaceCompiler(contracts[0], source, produced_at).compile()
        reports.append((str(case), check_parity(compiled, source)))
    return reports
