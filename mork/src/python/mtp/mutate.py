"""Seed MCN mutation operators and structural outcomes."""

from __future__ import annotations

from dataclasses import dataclass

from .mcnio import InProcessTool


@dataclass(frozen=True)
class Mutation:
    name: str
    text: str


@dataclass(frozen=True)
class MutantOutcome:
    mutation: str
    verdict: str
    codes: tuple[str, ...]


def seed_mutations(text: str) -> list[Mutation]:
    return [Mutation("drop:df", text.replace(" df ", " ", 1)), Mutation("drop:xr", text.replace(" xr ", " ", 1)), Mutation("swap:cb->ap", text.replace(" cb ", " ap ", 1)), Mutation("swap:df->dp", text.replace(" df ", " dp ", 1)), Mutation("retype:MU->M", text.replace(" MU", " M", 1)), Mutation("both:cb+cn", text.replace(" cb ", " cn ", 1))]


def evaluate(mutation: Mutation, tool: InProcessTool) -> MutantOutcome:
    decoded = tool.decode(mutation.text)
    if not decoded.ok:
        return MutantOutcome(mutation.name, "caught-decode", tuple(diagnostic.code for diagnostic in decoded.diagnostics))
    findings = tool.lint(decoded.graph)
    if findings:
        return MutantOutcome(mutation.name, "caught-lint", tuple(finding.code for finding in findings))
    return MutantOutcome(mutation.name, "silent", ())