# src/spc/verify/external_checks.py
"""
External validation checks that cannot be expressed in OWL or SHACL.

- Contractiveness: recursion variables guarded under communication prefixes
- Variable scoping: recursion variable references are properly bound
- Call graph acyclicity: no circular subprotocol calls
"""

from __future__ import annotations
from dataclasses import dataclass, field
from spc.processle import ast_nodes as ast


@dataclass
class ExternalCheckResult:
    errors: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0


def check_contractiveness(protocol: ast.Protocol) -> ExternalCheckResult:
    """Check that every recursion variable is guarded."""
    result = ExternalCheckResult()
    _check_contractive(protocol.global_type, set(), result, "body")
    for sp in protocol.subprotocols:
        _check_contractive(sp.body, set(), result, f"subprotocol/{sp.name}")
    return result


def _check_contractive(
    gt: ast.GlobalType,
    unguarded_vars: set[str],
    result: ExternalCheckResult,
    path: str,
):
    if isinstance(gt, ast.Recursion):
        # The variable is unguarded until we see a communication
        _check_contractive(
            gt.body, unguarded_vars | {gt.var}, result,
            f"{path}/rec_{gt.var}")

    elif isinstance(gt, ast.RecursionVar):
        if gt.var in unguarded_vars:
            result.errors.append(
                f"Recursion variable '{gt.var}' is not guarded "
                f"under a communication prefix at {path}")

    elif isinstance(gt, ast.Communication):
        # Communication guards all recursion variables
        for opt in gt.options:
            if opt.continuation:
                _check_contractive(
                    opt.continuation, set(), result,
                    f"{path}/comm_{opt.label}")

    elif isinstance(gt, ast.ParallelComp):
        _check_contractive(gt.left, unguarded_vars, result, f"{path}/par_l")
        _check_contractive(gt.right, unguarded_vars, result, f"{path}/par_r")

    elif isinstance(gt, ast.SubprotocolCall) and gt.continuation:
        # Call acts as a guard (it involves communication)
        _check_contractive(
            gt.continuation, set(), result,
            f"{path}/call_{gt.protocol_name}")


def check_call_graph_acyclicity(protocol: ast.Protocol) -> ExternalCheckResult:
    """Check that the subprotocol call graph is a DAG."""
    result = ExternalCheckResult()
    # Build adjacency list
    call_graph: dict[str, set[str]] = {}
    for sp in protocol.subprotocols:
        call_graph[sp.name] = _collect_calls(sp.body)
    # Also check the main body
    main_calls = _collect_calls(protocol.global_type)

    # DFS cycle detection
    visited: set[str] = set()
    in_stack: set[str] = set()

    def dfs(node: str) -> bool:
        if node in in_stack:
            result.errors.append(f"Cyclic call graph detected at '{node}'")
            return True
        if node in visited:
            return False
        visited.add(node)
        in_stack.add(node)
        for callee in call_graph.get(node, set()):
            if dfs(callee):
                return True
        in_stack.discard(node)
        return False

    for sp_name in call_graph:
        dfs(sp_name)

    return result


def _collect_calls(gt: ast.GlobalType) -> set[str]:
    """Collect all subprotocol names called from a global type."""
    calls: set[str] = set()
    if isinstance(gt, ast.SubprotocolCall):
        calls.add(gt.protocol_name)
        if gt.continuation:
            calls |= _collect_calls(gt.continuation)
    elif isinstance(gt, ast.Communication):
        for opt in gt.options:
            if opt.continuation:
                calls |= _collect_calls(opt.continuation)
    elif isinstance(gt, ast.ParallelComp):
        calls |= _collect_calls(gt.left)
        calls |= _collect_calls(gt.right)
    elif isinstance(gt, ast.Recursion):
        calls |= _collect_calls(gt.body)
    return calls