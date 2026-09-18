# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The MORK backend compiler family (ADR-A23, ADR-A24, delivery-plan Phase 5).

Compiles ``elg:IntervalCondition`` declarations into SPARQL, SHACL, and SWRL
artefacts through a shared executable IR. See ``eligibility_ir.py``'s module
docstring for what is, and is not, in scope. There is no "native" backend —
see ``namespaces.py``'s module docstring for why.
"""

from .eligibility_ir import (
    IntervalPlan,
    IRCompileError,
    ProfilePlan,
    RequiredInterval,
    compile_condition,
    compile_profile,
)
from .shacl_backend import compile_shapes
from .sparql_backend import compile_query_template
from .swrl_backend import compile_rules

__all__ = [
    "IntervalPlan",
    "IRCompileError",
    "ProfilePlan",
    "RequiredInterval",
    "compile_condition",
    "compile_profile",
    "compile_query_template",
    "compile_rules",
    "compile_shapes",
]
