# src/spc/verify/shacl_verifier.py
"""
SHACL validation via Jena's command-line SHACL tool or pySHACL.

Validates the protocol A-Box against the SPC well-formedness shapes.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import subprocess
import json

from spc.verify.jena_client import JenaClient


@dataclass
class SHACLViolation:
    focus_node: str
    path: str
    message: str
    severity: str = "Violation"


@dataclass
class SHACLVerificationResult:
    conforms: bool = True
    violations: list[SHACLViolation] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return self.conforms


def verify_shacl(
    data_path: Path,
    shapes_dir: Path,
    jena_shacl_cmd: str = "shacl",
) -> SHACLVerificationResult:
    """
    Run SHACL validation using the Jena SHACL command-line tool.

    Alternatively, use pySHACL for pure-Python validation:
        from pyshacl import validate
        conforms, results_graph, results_text = validate(
            data_graph, shacl_graph=shapes_graph)
    """
    result = SHACLVerificationResult()

    # Collect all shape files
    shape_files = list(shapes_dir.glob("*.ttl"))
    if not shape_files:
        return result

    for shape_file in shape_files:
        try:
            # Jena SHACL CLI: shacl validate --data data.ttl --shapes shapes.ttl
            proc = subprocess.run(
                [
                    jena_shacl_cmd, "validate",
                    "--data", str(data_path),
                    "--shapes", str(shape_file),
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )

            if proc.returncode != 0:
                # Parse validation report from stdout (Turtle format)
                violations = _parse_validation_report(proc.stdout)
                if violations:
                    result.conforms = False
                    result.violations.extend(violations)

        except FileNotFoundError:
            # Jena SHACL not installed — fall back to pySHACL
            result = _verify_with_pyshacl(data_path, shape_file, result)

        except subprocess.TimeoutExpired:
            result.violations.append(SHACLViolation(
                focus_node="",
                path="",
                message=f"SHACL validation timed out for {shape_file.name}",
                severity="Error",
            ))

    return result


def _verify_with_pyshacl(
    data_path: Path, shapes_path: Path, result: SHACLVerificationResult
) -> SHACLVerificationResult:
    """Fallback: use pySHACL for validation."""
    try:
        from pyshacl import validate

        conforms, results_graph, results_text = validate(
            str(data_path),
            shacl_graph=str(shapes_path),
            inference="none",
        )
        if not conforms:
            result.conforms = False
            # Parse results_text for violations
            for line in results_text.split("\n"):
                if "Constraint Violation" in line or "Result" in line:
                    result.violations.append(SHACLViolation(
                        focus_node="", path="",
                        message=line.strip(),
                    ))
    except ImportError:
        result.violations.append(SHACLViolation(
            focus_node="", path="",
            message="Neither Jena SHACL nor pySHACL available",
            severity="Error",
        ))
    return result


def _parse_validation_report(turtle_output: str) -> list[SHACLViolation]:
    """Parse a SHACL validation report in Turtle format."""
    from rdflib import Graph, Namespace
    SH = Namespace("http://www.w3.org/ns/shacl#")

    g = Graph()
    try:
        g.parse(data=turtle_output, format="turtle")
    except Exception:
        return []

    violations = []
    for report in g.subjects(SH.result):
        for result_node in g.objects(report, SH.result):
            focus = str(g.value(result_node, SH.focusNode) or "")
            path = str(g.value(result_node, SH.resultPath) or "")
            msg = str(g.value(result_node, SH.resultMessage) or "")
            sev = str(g.value(result_node, SH.resultSeverity) or "Violation")
            violations.append(SHACLViolation(
                focus_node=focus, path=path, message=msg,
                severity=sev.split("#")[-1],
            ))

    return violations