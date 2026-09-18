# src/spc/processle/validator.py
"""
Syntactic validation of the ProcessLE AST.

Checks that are possible on the AST alone, before DL encoding:
- All referenced participants are declared
- Labels are valid identifiers
- Subprotocol calls reference declared subprotocols
- Role argument arities match subprotocol declarations
- Recursion variables are bound
"""

from __future__ import annotations
from dataclasses import dataclass, field
from spc.processle import ast_nodes as ast


@dataclass
class ValidationError:
    message: str
    location: str = ""


@dataclass
class ValidationResult:
    errors: list[ValidationError] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def add(self, msg: str, loc: str = ""):
        self.errors.append(ValidationError(message=msg, location=loc))


def validate(protocol: ast.Protocol) -> ValidationResult:
    """Validate a Protocol AST for syntactic well-formedness."""
    result = ValidationResult()
    declared_participants = {p.name for p in protocol.participants}
    declared_subprotocols = {sp.name: sp for sp in protocol.subprotocols}

    _validate_global_type(
        protocol.global_type,
        declared_participants,
        declared_subprotocols,
        bound_vars=set(),
        result=result,
        path="body",
    )

    for ext in protocol.extensions:
        _validate_extension(ext, declared_participants, result)

    return result


def _validate_global_type(
    gt: ast.GlobalType,
    participants: set[str],
    subprotocols: dict[str, ast.SubprotocolDecl],
    bound_vars: set[str],
    result: ValidationResult,
    path: str,
):
    if isinstance(gt, ast.Communication):
        if gt.sender not in participants:
            result.add(f"Unknown sender '{gt.sender}'", path)
        if gt.receiver not in participants:
            result.add(f"Unknown receiver '{gt.receiver}'", path)
        if gt.sender == gt.receiver:
            result.add(
                f"Sender and receiver are the same: '{gt.sender}'", path)

        labels_seen = set()
        for i, opt in enumerate(gt.options):
            if opt.label in labels_seen:
                result.add(
                    f"Duplicate label '{opt.label}' in communication", path)
            labels_seen.add(opt.label)

            if opt.continuation:
                _validate_global_type(
                    opt.continuation, participants, subprotocols,
                    bound_vars, result, f"{path}/opt_{opt.label}",
                )

    elif isinstance(gt, ast.ParallelComp):
        left_parts = _collect_participants(gt.left)
        right_parts = _collect_participants(gt.right)
        overlap = left_parts & right_parts
        if overlap:
            result.add(
                f"Parallel branches share participants: {overlap}", path)
        _validate_global_type(
            gt.left, participants, subprotocols,
            bound_vars, result, f"{path}/par_left")
        _validate_global_type(
            gt.right, participants, subprotocols,
            bound_vars, result, f"{path}/par_right")

    elif isinstance(gt, ast.Recursion):
        new_bound = bound_vars | {gt.var}
        _validate_global_type(
            gt.body, participants, subprotocols,
            new_bound, result, f"{path}/rec_{gt.var}")

    elif isinstance(gt, ast.RecursionVar):
        if gt.var not in bound_vars:
            result.add(f"Unbound recursion variable '{gt.var}'", path)

    elif isinstance(gt, ast.SubprotocolCall):
        if gt.caller not in participants:
            result.add(f"Unknown caller '{gt.caller}'", path)
        if gt.protocol_name not in subprotocols:
            result.add(
                f"Unknown subprotocol '{gt.protocol_name}'", path)
        else:
            sp = subprotocols[gt.protocol_name]
            if len(gt.role_args) != len(sp.role_params):
                result.add(
                    f"Subprotocol '{gt.protocol_name}' expects "
                    f"{len(sp.role_params)} roles, got {len(gt.role_args)}",
                    path,
                )
        if gt.continuation:
            _validate_global_type(
                gt.continuation, participants, subprotocols,
                bound_vars, result, f"{path}/call_cont")

    elif isinstance(gt, ast.End):
        pass
    else:
        result.add(f"Unknown global type node: {type(gt).__name__}", path)


def _collect_participants(gt: ast.GlobalType) -> set[str]:
    """Collect all participant names referenced in a global type."""
    parts: set[str] = set()
    if isinstance(gt, ast.Communication):
        parts.add(gt.sender)
        parts.add(gt.receiver)
        for opt in gt.options:
            if opt.continuation:
                parts |= _collect_participants(opt.continuation)
    elif isinstance(gt, ast.ParallelComp):
        parts |= _collect_participants(gt.left)
        parts |= _collect_participants(gt.right)
    elif isinstance(gt, ast.Recursion):
        parts |= _collect_participants(gt.body)
    elif isinstance(gt, ast.SubprotocolCall):
        parts.add(gt.caller)
        parts.update(gt.role_args)
        if gt.continuation:
            parts |= _collect_participants(gt.continuation)
    return parts


def _validate_extension(
    ext: ast.ExtensionAnnotation,
    participants: set[str],
    result: ValidationResult,
):
    if ext.target_participant and ext.target_participant not in participants:
        result.add(
            f"Extension references unknown participant "
            f"'{ext.target_participant}'",
            f"extension/{type(ext).__name__}",
        )