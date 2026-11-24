# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""
The closed vocabulary of a derivation's expression, and the typing rules its law checks (``srf:P6`` to ``srf:P9``).

``model.SurfaceGraphAnalyser`` transcribes an expression with these rules, and ``lowering`` carries it across to MORK.
The same rules are the SHACL shapes of ``ontology/surface/README.md`` section 10, which check a declaration graph
without this code. Nothing here evaluates an expression. Evaluation is a compiled backend's.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

from rdflib import URIRef

from .namespaces import SRF, XSD

SUM = SRF.SumExpression
DIFFERENCE = SRF.DifferenceExpression
PRODUCT = SRF.ProductExpression
QUOTIENT = SRF.QuotientExpression
TYPED_LITERAL = SRF.TypedLiteralExpression
ROUNDING = SRF.RoundingExpression
CHOICE = SRF.ChoiceExpression

ARITHMETIC_KINDS: Tuple[URIRef, ...] = (SUM, DIFFERENCE, PRODUCT, QUOTIENT)

#: Every kind of expression node, in the order the vocabulary lists them.
EXPRESSION_KINDS: Tuple[URIRef, ...] = ARITHMETIC_KINDS + (TYPED_LITERAL, ROUNDING, CHOICE)

#: The operand properties of each kind, in the order its operands are written. A typed literal has none.
OPERAND_SLOTS: Dict[URIRef, Tuple[URIRef, ...]] = {
    SUM: (SRF.leftOperand, SRF.rightOperand),
    DIFFERENCE: (SRF.leftOperand, SRF.rightOperand),
    PRODUCT: (SRF.leftOperand, SRF.rightOperand),
    QUOTIENT: (SRF.leftOperand, SRF.rightOperand),
    TYPED_LITERAL: (),
    ROUNDING: (SRF.roundedOperand,),
    CHOICE: (SRF.comparedLeft, SRF.comparedRight, SRF.whenTrue, SRF.whenFalse),
}

#: The numeric datatypes, widest last, as numeric promotion orders them.
NUMERIC_RANK: Dict[str, int] = {
    str(XSD.integer): 1,
    str(XSD.decimal): 2,
    str(XSD.float): 3,
    str(XSD.double): 4,
}
_BY_RANK = {rank: datatype for datatype, rank in NUMERIC_RANK.items()}

ORDERING_OPERATORS: Tuple[URIRef, ...] = (
    SRF.LessThan,
    SRF.LessThanOrEqual,
    SRF.GreaterThanOrEqual,
    SRF.GreaterThan,
)
COMPARISON_OPERATORS: Tuple[URIRef, ...] = ORDERING_OPERATORS + (SRF.EqualTo, SRF.NotEqualTo)


def is_numeric(datatype: Optional[URIRef]) -> bool:
    return datatype is not None and str(datatype) in NUMERIC_RANK


def promoted(left: URIRef, right: URIRef, *, at_least_decimal: bool = False) -> URIRef:
    """The datatype numeric promotion gives for two numeric operands. A quotient is at least decimal."""
    rank = max(NUMERIC_RANK[str(left)], NUMERIC_RANK[str(right)])
    if at_least_decimal:
        rank = max(rank, NUMERIC_RANK[str(XSD.decimal)])
    return URIRef(_BY_RANK[rank])


def comparable(left: URIRef, right: URIRef) -> bool:
    """Whether two compared operands share a datatype, or are both numeric."""
    return str(left) == str(right) or (is_numeric(left) and is_numeric(right))
