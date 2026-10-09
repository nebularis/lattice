# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Witness coverage (formal-methods track H, slice H1.2).

A rule that no fixture can trigger is vacuous: it may be dead, or guard a
case that cannot arise, and nothing would notice. This module lists every
rule in four families and requires, for each, at least one fixture that
*triggers* it, not only one that satisfies it (review §7.4):

``refusal``
    a named hard failure of ``compile``. The key is a ``CrossAxisViolation``
    kind, or the class name of another raised exception.
``warning``
    a named ``Diagnostic`` of severity WARNING.
``shape``
    a ``sh:NodeShape`` in ``ontology/persistence/shapes/constraints.ttl``.
    It is witnessed when validating a fixture reports a result from it.
``audit``
    an always-on audit query template. It is witnessed by a dataset that
    makes it return at least one row, and a clean dataset that makes it
    return none, since a query that always fires detects nothing either.

A rule with no witness must be listed, with a reason, in
``tests/witnesses/known-gaps.txt``. An unlisted gap fails the check, and so
does a listed gap that has since gained a witness. The rule inventory is
read from the package's own source, so adding a rule without a witness
cannot pass unnoticed.
"""

from __future__ import annotations

import ast
import re
import warnings
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Iterator

import pyshacl
from rdflib import RDF, Dataset, Graph, Namespace, URIRef

from .compiler import CompileError, compile_targets, compile_to_graph
from .instantiate import instantiate_by_target

SH = Namespace("http://www.w3.org/ns/shacl#")

REFUSAL, WARNING, SHAPE, AUDIT = "refusal", "warning", "shape", "audit"
FAMILIES = (REFUSAL, WARNING, SHAPE, AUDIT)

PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_DIR.parents[3]
SPEC_TTL = REPO_ROOT / "ontology" / "persistence" / "spec" / "persistence.ttl"
SHAPES_TTL = REPO_ROOT / "ontology" / "persistence" / "shapes" / "constraints.ttl"
EXAMPLES_DIR = REPO_ROOT / "ontology" / "persistence" / "examples"
WITNESS_DIR = REPO_ROOT / "tools" / "persistence" / "tests" / "witnesses"
KNOWN_GAPS = WITNESS_DIR / "known-gaps.txt"
TEMPLATE_DIR = PACKAGE_DIR / "templates"

# Exceptions that are refusals in their own right, keyed by class name.
# ``CrossAxisViolation`` is keyed by its ``kind`` instead.
_NAMED_REFUSALS = ("ProfileAmbiguityError", "BoundaryConflict", "MissingBoundaryShapeError", "BoundaryCycleError")
# Calls whose first string argument is a CrossAxisViolation or warning kind.
_REFUSAL_CALLS = ("CrossAxisViolation", "fail")
_WARNING_CALLS = ("_warning", "Diagnostic")


@dataclass(frozen=True, order=True)
class Rule:
    family: str
    name: str

    def __str__(self) -> str:
        return f"{self.family}:{self.name}"


# --------------------------------------------------------------------------
# the inventory, read from the package's own source and ontology


def _call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def _kind_argument(node: ast.Call) -> str | None:
    for keyword in node.keywords:
        if keyword.arg == "kind" and isinstance(keyword.value, ast.Constant):
            return keyword.value.value
    if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
        return node.args[0].value
    return None


def source_rules(source_dir: Path = PACKAGE_DIR) -> set[Rule]:
    """Refusals and warnings found in the package's source by syntax alone.

    A ``CrossAxisViolation(kind, ...)`` or ``fail(kind, ...)`` call names a
    refusal. A ``_warning(kind, ...)`` or ``Diagnostic(kind=..., ...)`` call
    names a warning. A ``raise`` of one of the other named exceptions is a
    refusal keyed by the class name. A call whose kind is not a string
    literal is skipped here: it is a variable, such as the ``kind`` parameter
    of ``_warning`` itself."""
    rules: set[Rule] = set()
    for path in sorted(source_dir.glob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call):
                name, kind = _call_name(node), _kind_argument(node)
                if kind and name in _REFUSAL_CALLS:
                    rules.add(Rule(REFUSAL, kind))
                elif kind and name in _WARNING_CALLS:
                    rules.add(Rule(WARNING, kind))
            elif isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call):
                if _call_name(node.exc) in _NAMED_REFUSALS:
                    rules.add(Rule(REFUSAL, _call_name(node.exc)))
    return rules


def shape_rules(shapes: Graph) -> set[Rule]:
    return {Rule(SHAPE, _local(s)) for s in shapes.subjects(RDF.type, SH.NodeShape) if isinstance(s, URIRef)}


def audit_rules(template_dir: Path = TEMPLATE_DIR) -> set[Rule]:
    return {Rule(AUDIT, p.name.removesuffix(".mustache")) for p in sorted(template_dir.glob("*-audit.mustache"))}


def _local(iri) -> str:
    return str(iri).rsplit("#", 1)[-1]


def enumerate_rules() -> set[Rule]:
    shapes = Graph()
    shapes.parse(SHAPES_TTL, format="turtle")
    return source_rules() | shape_rules(shapes) | audit_rules()


# --------------------------------------------------------------------------
# observation: what do the fixtures actually trigger

Observed = dict[Rule, set[str]]


def _record(observed: Observed, rule: Rule, witness: str) -> None:
    observed.setdefault(rule, set()).add(witness)


def compile_fixtures(extra_dir: Path = WITNESS_DIR) -> Iterator[Path]:
    """Every shipped example and every file directly in the witness directory."""
    yield from sorted(EXAMPLES_DIR.glob("*.ttl"))
    if extra_dir.is_dir():
        yield from sorted(extra_dir.glob("*.ttl"))


def _load_fixture(path: Path) -> Graph:
    """The spec plus one fixture. ``capability-spec-example`` is a
    capability record only, so it is compiled against the baseline example,
    as ``build:persistence-execution`` does."""
    graph = Graph()
    graph.parse(SPEC_TTL, format="turtle")
    if path.name == "capability-spec-example.ttl":
        graph.parse(EXAMPLES_DIR / "baseline-single-class.ttl", format="turtle")
    graph.parse(path, format="turtle")
    return graph


def observe_compile(fixtures: Iterable[Path]) -> Observed:
    """Compile each fixture, recording the refusal it raises or the warnings
    it emits."""
    observed: Observed = {}
    for path in fixtures:
        try:
            compiled = compile_targets(_load_fixture(path))
        except CompileError as error:
            cause = error.cause
            _record(observed, Rule(REFUSAL, getattr(cause, "kind", None) or type(cause).__name__), path.name)
            continue
        for target in compiled:
            for diagnostic in target.diagnostics:
                if diagnostic.severity == "WARNING":
                    _record(observed, Rule(WARNING, diagnostic.kind), path.name)
    return observed


def _owning_shape(shapes: Graph, shape) -> URIRef | None:
    """The named node shape a result came from. A property shape is a blank
    node reached by ``sh:property``, so climb to its parent."""
    seen = set()
    while shape is not None and not isinstance(shape, URIRef) and shape not in seen:
        seen.add(shape)
        shape = next(iter(shapes.subjects(SH.property, shape)), None)
    return shape if isinstance(shape, URIRef) else None


def observe_shapes(fixtures: Iterable[Path]) -> Observed:
    """Validate each fixture against the shapes, recording every node shape
    that reports a result, of any severity."""
    shapes = Graph()
    shapes.parse(SHAPES_TTL, format="turtle")
    observed: Observed = {}
    for path in fixtures:
        _, results, _ = pyshacl.validate(
            _load_fixture(path), shacl_graph=shapes, inference="none", advanced=True, allow_warnings=True
        )
        for source in results.objects(None, SH.sourceShape):
            owner = _owning_shape(shapes, source)
            if owner is not None:
                _record(observed, Rule(SHAPE, _local(owner)), path.name)
    return observed


# --------------------------------------------------------------------------
# audits: a violating dataset must return rows, a clean one none

# The slots a caller fills at request time (``dal:registryGraph`` lists the
# buckets). They are not in the compiled bindings, so a witness supplies them.
_SLOT_PATTERN = re.compile(r"\{\{\{(\w+)\}\}\}")


@contextmanager
def _quiet_rdflib() -> Iterator[None]:
    """rdflib's own TriG parser and Dataset query use its deprecated
    ConjunctiveGraph internals, which is noise here and not ours to fix."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        yield


@dataclass(frozen=True)
class AuditWitness:
    audit: str
    kind: str  # "violation" or "clean"
    path: Path
    bindings: dict[str, str]
    dataset: Dataset


def _read_directives(text: str) -> dict[str, str]:
    """``# bind: name = <iri> <iri>`` comment lines at the top of a witness."""
    bindings: dict[str, str] = {}
    for line in text.splitlines():
        match = re.match(r"#\s*bind:\s*(\w+)\s*=\s*(.+)$", line)
        if match:
            bindings[match.group(1)] = match.group(2).strip()
    return bindings


def audit_witnesses(witness_dir: Path = WITNESS_DIR) -> list[AuditWitness]:
    """``audits/<audit-name>.violation.trig`` and ``.clean.trig`` files.

    Each carries ``# bind: slot = value`` lines for the template's slots."""
    out: list[AuditWitness] = []
    for path in sorted((witness_dir / "audits").glob("*.trig")) if (witness_dir / "audits").is_dir() else []:
        stem = path.name.removesuffix(".trig")
        audit, _, kind = stem.rpartition(".")
        text = path.read_text(encoding="utf-8")
        dataset = Dataset()
        with _quiet_rdflib():
            dataset.parse(data=text, format="trig")
        out.append(AuditWitness(audit, kind, path, _read_directives(text), dataset))
    return out


@lru_cache(maxsize=1)
def compiled_audit_texts() -> dict[str, str]:
    """Each audit as the compiler and ``instantiate`` produce it for the
    baseline example, keyed by template stem. Compiler-known parameters are
    already filled in, so a witness exercises what ships and not the bare
    template. Request-time slots, such as ``logGraphs``, are left in place."""
    compiled_graph, _ = compile_to_graph(_load_fixture(EXAMPLES_DIR / "baseline-single-class.ttl"))
    texts: dict[str, str] = {}
    for operations in instantiate_by_target(compiled_graph).values():
        for operation, text in operations.items():
            stem = re.split(r"[:_/]", operation, maxsplit=1)[0]
            if stem.endswith("-audit"):
                texts[stem] = text
    return texts


def run_audit(witness: AuditWitness) -> int:
    """Complete the audit's request-time slots from the witness's ``# bind:``
    lines and return the number of rows it yields over the witness's dataset."""
    text = compiled_audit_texts()[witness.audit]
    missing = sorted(set(_SLOT_PATTERN.findall(text)) - set(witness.bindings))
    if missing:
        raise ValueError(f"{witness.path.name}: no '# bind:' line for slot(s) {', '.join(missing)}")
    # The caller's own step (render.REQUEST_TIME_SLOTS). A slot is a literal
    # triple-brace tag with no escaping, so plain substitution is equivalent to
    # a Mustache library, and keeps persistence.render the only chevron user.
    query = text
    for name, value in witness.bindings.items():
        query = query.replace("{{{" + name + "}}}", value)
    with _quiet_rdflib():
        return len(list(witness.dataset.query(query)))


def observe_audits(witnesses: Iterable[AuditWitness]) -> tuple[Observed, list[str]]:
    """An audit is witnessed only when a violation file yields rows *and* a
    clean file for it yields none. Returns the observation and the problems
    found."""
    by_audit: dict[str, dict[str, list[AuditWitness]]] = {}
    for witness in witnesses:
        by_audit.setdefault(witness.audit, {}).setdefault(witness.kind, []).append(witness)
    observed: Observed = {}
    problems: list[str] = []
    for audit, kinds in sorted(by_audit.items()):
        fired = [w for w in kinds.get("violation", []) if run_audit(w) > 0]
        silent = [w for w in kinds.get("clean", []) if run_audit(w) == 0]
        for w in kinds.get("violation", []):
            if w not in fired:
                problems.append(f"{w.path.name}: the violation dataset returns no rows")
        for w in kinds.get("clean", []):
            if w not in silent:
                problems.append(f"{w.path.name}: the clean dataset returns rows")
        if fired and silent:
            for w in fired + silent:
                _record(observed, Rule(AUDIT, audit), w.path.name)
        elif kinds:
            problems.append(f"{audit}: needs both a violating and a clean witness that behave as named")
    return observed, problems


# --------------------------------------------------------------------------
# the report


def read_known_gaps(path: Path = KNOWN_GAPS) -> dict[Rule, str]:
    """``family:name | reason`` lines. Blank lines and ``#`` comments are ignored."""
    gaps: dict[Rule, str] = {}
    if not path.is_file():
        return gaps
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        rule_text, _, reason = line.partition("|")
        family, _, name = rule_text.strip().partition(":")
        gaps[Rule(family, name)] = reason.strip()
    return gaps


@dataclass
class Report:
    covered: dict[Rule, set[str]] = field(default_factory=dict)
    uncovered: list[Rule] = field(default_factory=list)  # no witness and not a listed gap
    listed_gaps: dict[Rule, str] = field(default_factory=dict)
    stale_gaps: list[Rule] = field(default_factory=list)  # listed, but witnessed
    unknown_gaps: list[Rule] = field(default_factory=list)  # listed, but not a rule
    problems: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not (self.uncovered or self.stale_gaps or self.unknown_gaps or self.problems)

    def lines(self, verbose: bool = False) -> list[str]:
        out = []
        total = len(self.covered) + len(self.listed_gaps) + len(self.uncovered)
        out.append(
            f"witness coverage: {len(self.covered)} of {total} rule(s) witnessed, "
            f"{len(self.listed_gaps)} listed gap(s), {len(self.uncovered)} unlisted gap(s)"
        )
        for family in FAMILIES:
            have = sum(1 for r in self.covered if r.family == family)
            want = have + sum(1 for r in [*self.listed_gaps, *self.uncovered] if r.family == family)
            out.append(f"  {family:8} {have}/{want}")
        out += [f"UNWITNESSED {rule}" for rule in self.uncovered]
        out += [f"STALE GAP {rule}: it now has a witness, remove it from known-gaps.txt" for rule in self.stale_gaps]
        out += [f"UNKNOWN GAP {rule}: no such rule" for rule in self.unknown_gaps]
        out += [f"PROBLEM {problem}" for problem in self.problems]
        if verbose:
            out += [f"WITNESSED {rule} <- {', '.join(sorted(files))}" for rule, files in self.covered.items()]
            out += [f"GAP {rule} | {reason}" for rule, reason in self.listed_gaps.items()]
        return out


def build_report(
    rules: set[Rule],
    observed: Observed,
    gaps: dict[Rule, str],
    problems: Iterable[str] = (),
) -> Report:
    covered = {rule: observed[rule] for rule in sorted(rules) if rule in observed}
    report = Report(covered=covered, problems=list(problems))
    for rule in sorted(rules):
        if rule in observed:
            if rule in gaps:
                report.stale_gaps.append(rule)
        elif rule in gaps:
            report.listed_gaps[rule] = gaps[rule]
        else:
            report.uncovered.append(rule)
    report.unknown_gaps = sorted(rule for rule in gaps if rule not in rules)
    return report


@lru_cache(maxsize=1)
def _observations() -> tuple[Observed, tuple[str, ...]]:
    """The slow part, run once per process: compile and validate every
    fixture, and run every audit witness."""
    fixtures = list(compile_fixtures())
    observed = observe_compile(fixtures)
    for rule, witnesses in observe_shapes(fixtures).items():
        observed.setdefault(rule, set()).update(witnesses)
    audit_observed, problems = observe_audits(audit_witnesses())
    observed.update(audit_observed)
    return observed, tuple(problems)


def check_witness_coverage() -> Report:
    observed, problems = _observations()
    return build_report(enumerate_rules(), observed, read_known_gaps(), problems)


__all__ = [
    "AUDIT",
    "AuditWitness",
    "REFUSAL",
    "Report",
    "Rule",
    "SHAPE",
    "WARNING",
    "audit_witnesses",
    "build_report",
    "check_witness_coverage",
    "compile_fixtures",
    "enumerate_rules",
    "observe_audits",
    "observe_compile",
    "observe_shapes",
    "read_known_gaps",
    "run_audit",
    "source_rules",
]
