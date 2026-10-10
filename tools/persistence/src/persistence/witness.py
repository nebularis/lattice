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
import os
import re
import warnings
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Iterator, Mapping

import pyshacl
from rdflib import RDF, RDFS, Dataset, Graph, Literal, Namespace, URIRef

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
_NAMED_REFUSALS = ("ProfileAmbiguityError", "BoundaryConflict", "MissingBoundaryShapeError")
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


def _kind_node(node: ast.Call) -> ast.expr | None:
    """The expression naming the kind in a refusal or warning call."""
    for keyword in node.keywords:
        if keyword.arg == "kind":
            return keyword.value
    return node.args[0] if node.args else None


class _Source:
    """Every function and call in the package, enough to follow a kind that
    reaches a refusal through a helper's parameter (``self.constraint(...,
    "KeyConstraintRequired")`` passes it to ``fail`` as ``missing_kind``)."""

    def __init__(self, source_dir: Path):
        self.calls: list[tuple[str, ast.Call, ast.FunctionDef | None]] = []
        self.functions: dict[str, ast.FunctionDef] = {}
        for path in sorted(source_dir.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            owners: dict[int, ast.FunctionDef | None] = {}
            for fn in (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)):
                self.functions[fn.name] = fn
                for inner in ast.walk(fn):
                    owners[id(inner)] = fn  # the innermost function wins, as walk is breadth-first
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    self.calls.append((path.name, node, owners.get(id(node))))

    def kinds(self, expr: ast.expr | None, owner: ast.FunctionDef | None, seen: frozenset = frozenset()) -> set[str] | None:
        """The string constants ``expr`` can be, or ``None`` if it cannot be
        determined. A parameter is resolved from the arguments at its
        function's call sites."""
        if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
            return {expr.value}
        if not (isinstance(expr, ast.Name) and owner is not None and expr.id not in seen):
            return None
        params = [a.arg for a in owner.args.args]
        if expr.id not in params:
            return None
        found: set[str] = set()
        sites = 0
        offset = 1 if params and params[0] == "self" else 0
        for _, call, caller in self.calls:
            if _call_name(call) != owner.name:
                continue
            sites += 1
            index = params.index(expr.id) - (offset if isinstance(call.func, ast.Attribute) else 0)
            argument = next((k.value for k in call.keywords if k.arg == expr.id), None)
            if argument is None and 0 <= index < len(call.args):
                argument = call.args[index]
            resolved = self.kinds(argument, caller, seen | {expr.id})
            if resolved is None:
                return None
            found |= resolved
        return found if sites else None


def scan_source(source_dir: Path = PACKAGE_DIR) -> tuple[set[Rule], list[str]]:
    """Refusals and warnings found in the package's source, and the call sites
    whose kind could not be determined.

    A ``CrossAxisViolation(kind, ...)`` or ``fail(kind, ...)`` call names a
    refusal. A ``_warning(kind, ...)`` or ``Diagnostic(kind=..., ...)`` call
    names a warning. A ``raise`` of one of the other named exceptions is a
    refusal keyed by the class name. A kind that is a parameter is followed
    back to the constants passed for it. A call whose kind cannot be
    determined is returned as a problem, never skipped, so the inventory
    cannot silently miss a rule."""
    source = _Source(source_dir)
    rules: set[Rule] = set()
    problems: list[str] = []
    for filename, call, owner in source.calls:
        name = _call_name(call)
        if name in _NAMED_REFUSALS:
            rules.add(Rule(REFUSAL, name))
            continue
        if name not in _REFUSAL_CALLS and name not in _WARNING_CALLS:
            continue
        family = REFUSAL if name in _REFUSAL_CALLS else WARNING
        kinds = source.kinds(_kind_node(call), owner)
        if kinds is None:
            problems.append(f"{filename}:{call.lineno}: cannot determine the kind passed to {name}()")
        else:
            rules.update(Rule(family, kind) for kind in kinds)
    return rules, problems


def source_rules(source_dir: Path = PACKAGE_DIR) -> set[Rule]:
    return scan_source(source_dir)[0]


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
    """Every shipped example and every witness file directly in the witness
    directory."""
    yield from sorted(EXAMPLES_DIR.glob("*.ttl"))
    if extra_dir.is_dir():
        # a file whose name starts with "_" is a shared base, not a witness
        yield from sorted(p for p in extra_dir.glob("*.ttl") if not p.name.startswith("_"))


_DIRECTIVE = re.compile(r"^#\s*(base|remove):\s*(.+?)\s*$")


def _term(graph: Graph, text: str):
    """A term in a ``# remove:`` line: ``<iri>``, a CURIE using the fixture's
    own prefixes, a quoted string, or an integer."""
    if text.startswith("<") and text.endswith(">"):
        return URIRef(text[1:-1])
    if text.startswith('"') and text.endswith('"'):
        return Literal(text[1:-1])
    if re.fullmatch(r"-?\d+", text):
        return Literal(int(text))
    return URIRef(graph.namespace_manager.expand_curie(text))


def _load_fixture(path: Path) -> Graph:
    """The spec plus one fixture.

    A fixture is Turtle, optionally preceded by directives that patch a
    shipped example, so a witness is a small difference from it and follows
    the example when it changes::

        # base: identity-minting-anchors.ttl
        # remove: ex:ProductIdentity dal:mintedIriTemplate
        # remove: ex:ProductIdentity dal:digestScheme ex:ProductDigest

    The base is parsed first and each ``remove`` deletes every matching
    triple (the object is optional). The Turtle that follows is then added.
    A ``remove`` that matches nothing is an error, so a patch cannot quietly
    do nothing.

    ``capability-spec-example`` is a capability record only, so it is
    compiled against the baseline example, as ``build:persistence-execution``
    does."""
    text = path.read_text(encoding="utf-8")
    directives = [m.groups() for line in text.splitlines() if (m := _DIRECTIVE.match(line))]
    bases = [value for kind, value in directives if kind == "base"]
    graph = Graph()
    graph.parse(SPEC_TTL, format="turtle")
    if path.name == "capability-spec-example.ttl":
        bases = ["baseline-single-class.ttl"]
    for base in bases:
        graph.parse(next(d / base for d in (EXAMPLES_DIR, WITNESS_DIR) if (d / base).is_file()), format="turtle")
    body = Graph()
    body.parse(data=text, format="turtle")
    for kind, value in directives:
        if kind != "remove":
            continue
        parts = value.split(None, 2)
        if len(parts) < 2:
            raise ValueError(f"{path.name}: 'remove:' needs a subject and a predicate, got {value!r}")
        pattern = (_term(body, parts[0]), _term(body, parts[1]), _term(body, parts[2]) if len(parts) == 3 else None)
        matched = list(graph.triples(pattern))
        if not matched:
            raise ValueError(f"{path.name}: 'remove: {value}' matches nothing in the base")
        for triple in matched:
            graph.remove(triple)
    graph += body
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


def _focus_nodes(data: Graph, shapes: Graph, shape: URIRef) -> set:
    """The nodes a shape's ``sh:targetClass`` or ``sh:targetSubjectsOf`` selects
    in ``data``, counting subclasses by the asserted ``rdfs:subClassOf``
    triples (SHACL's rule)."""
    focus: set = set()
    for target_class in shapes.objects(shape, SH.targetClass):
        for cls in data.transitive_subjects(RDFS.subClassOf, target_class):
            focus.update(data.subjects(RDF.type, cls))
    for predicate in shapes.objects(shape, SH.targetSubjectsOf):
        focus.update(data.subjects(predicate, None))
    return focus


def observe_shapes(fixtures: Iterable[Path]) -> tuple[Observed, Observed]:
    """Validate each fixture against the shapes. Returns two observations.

    The first records every node shape that reports a result, of any
    severity. The second records every shape that has focus nodes in the
    fixture and reports nothing for them, a fixture that conforms. A shape
    that fires everywhere detects nothing, so it is witnessed only when both
    exist, as an audit needs a violating and a clean dataset."""
    shapes = Graph()
    shapes.parse(SHAPES_TTL, format="turtle")
    named = [s for s in shapes.subjects(RDF.type, SH.NodeShape) if isinstance(s, URIRef)]
    fired: Observed = {}
    conforming: Observed = {}
    for path in fixtures:
        data = _load_fixture(path)
        _, results, _ = pyshacl.validate(data, shacl_graph=shapes, inference="none", advanced=True, allow_warnings=True)
        reporting = set()
        for source in results.objects(None, SH.sourceShape):
            owner = _owning_shape(shapes, source)
            if owner is not None:
                reporting.add(owner)
                _record(fired, Rule(SHAPE, _local(owner)), path.name)
        for shape in named:
            if shape not in reporting and _focus_nodes(data, shapes, shape):
                _record(conforming, Rule(SHAPE, _local(shape)), path.name)
    return fired, conforming


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


_GREEN, _RED, _RESET = "\033[32m", "\033[31m", "\033[0m"


def _paint(text: str, code: str, enabled: bool) -> str:
    return f"{code}{text}{_RESET}" if enabled else text


def use_color(stream, environ: Mapping[str, str] | None = None) -> bool:
    """Whether to colour output on ``stream``. ``NO_COLOR`` (any value) turns
    colour off and ``FORCE_COLOR`` (any value but ``0``) turns it on, per the
    usual conventions. Otherwise colour is used on a terminal that is not
    ``TERM=dumb``."""
    env = os.environ if environ is None else environ
    if env.get("NO_COLOR"):
        return False
    if env.get("FORCE_COLOR", "0") != "0":
        return True
    return bool(getattr(stream, "isatty", lambda: False)()) and env.get("TERM") != "dumb"


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

    def lines(self, verbose: bool = False, color: bool = False) -> list[str]:
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
            out += [
                _paint(f"WITNESSED {rule} <- {', '.join(sorted(files))}", _GREEN, color)
                for rule, files in self.covered.items()
            ]
            out += [_paint(f"GAP {rule} | {reason}", _RED, color) for rule, reason in self.listed_gaps.items()]
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


def named_witness_problems(observed: Observed, witness_dir: Path = WITNESS_DIR) -> list[str]:
    """A file in the witness directory called ``refusal-X.ttl``,
    ``warning-X.ttl`` or ``shape-X.ttl`` must witness ``X``. Otherwise it has drifted onto a
    different rule, usually because an earlier check now refuses it first."""
    problems: list[str] = []
    if not witness_dir.is_dir():
        return problems
    for path in sorted(witness_dir.glob("*.ttl")):
        family, _, name = path.name.removesuffix(".ttl").partition("-")
        if family not in (REFUSAL, WARNING, SHAPE) or not name:
            continue
        if path.name not in observed.get(Rule(family, name), set()):
            seen = sorted(str(r) for r, files in observed.items() if path.name in files)
            problems.append(f"{path.name}: does not trigger {family}:{name}, it triggers {', '.join(seen) or 'nothing'}")
    return problems


@lru_cache(maxsize=1)
def _observations() -> tuple[Observed, tuple[str, ...]]:
    """The slow part, run once per process: compile and validate every
    fixture, and run every audit witness."""
    fixtures = list(compile_fixtures())
    observed = observe_compile(fixtures)
    fired, conforming = observe_shapes(fixtures)
    problems_shapes: list[str] = []
    for rule, witnesses in fired.items():
        if rule in conforming:
            observed.setdefault(rule, set()).update(witnesses)
        else:
            problems_shapes.append(f"{rule.name}: reports a result on every fixture it applies to, so it detects nothing")
    audit_observed, problems = observe_audits(audit_witnesses())
    observed.update(audit_observed)
    return observed, (*problems_shapes, *problems, *named_witness_problems(observed))


def check_witness_coverage() -> Report:
    observed, problems = _observations()
    return build_report(enumerate_rules(), observed, read_known_gaps(), [*scan_source()[1], *problems])


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
    "named_witness_problems",
    "observe_audits",
    "observe_compile",
    "observe_shapes",
    "read_known_gaps",
    "use_color",
    "run_audit",
    "scan_source",
    "source_rules",
]
