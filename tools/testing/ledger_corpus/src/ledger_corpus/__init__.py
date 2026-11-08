# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Generated account trees and passes under the ledger's terms, for its tests and benchmarks (ADR-A125). Each function returns the
data alone, and the caller adds the model graphs it validates against. The trees are shallow and wide, a root, its sections and
their sublimits or leaves, as real account trees are, never a deep chain, which recurses past rdflib's property-path evaluator."""

from __future__ import annotations

from rdflib import Graph, Namespace

LATTICE = "https://www.nebularis.org/neuro-semantic/lattice/"
LDG = Namespace(LATTICE + "ledger#")
QNT = Namespace(LATTICE + "quantification#")
XSD = "http://www.w3.org/2001/XMLSchema#"


def _turtle(lines: list[str]) -> Graph:
    g = Graph()
    g.parse(data="\n".join(lines), format="turtle")
    return g


def account_tree(definitions: int = 10_000, sections: int = 99) -> Graph:
    """`definitions` account definitions in a wide tree: a root, `sections` sections each part of it, and the rest sublimits spread
    across the sections. Every definition states the same amount on one extensive value space and refuses to merge."""
    lines = [f"@prefix ldg: <{LDG}> .", f"@prefix qnt: <{QNT}> .", "@prefix ex: <https://example.org/lattice/ledger/scale/> .",
             "ex:space a qnt:ValueSpace ; qnt:spaceKey \"scale\" ; qnt:orderKind qnt:TotalOrder ; "
             "qnt:densityKind qnt:Discrete ; qnt:spaceHash \"scale-v1\" ; qnt:additivity qnt:Extensive ; "
             "qnt:hasOperationCapability ex:sum , ex:diff .",
             "ex:sum a qnt:OperationCapability ; qnt:operationKind qnt:Sum ; qnt:resultSpace ex:space .",
             "ex:diff a qnt:OperationCapability ; qnt:operationKind qnt:Difference ; qnt:resultSpace ex:space .",
             f"ex:amount a qnt:Quantity ; qnt:onSpace ex:space ; qnt:numericValue \"100\"^^<{XSD}decimal> .",
             "ex:root a ldg:AccountDefinition ; ldg:statedAmount ex:amount ; ldg:unitOfAccount ex:space ; "
             "ldg:admitsOwnerKind qnt:ValueSpace ; ldg:mergeRule ldg:Refuse ."]
    for s in range(sections):
        lines.append(f"ex:section{s} a ldg:AccountDefinition ; ldg:statedAmount ex:amount ; ldg:unitOfAccount ex:space ; "
                     f"ldg:admitsOwnerKind qnt:ValueSpace ; ldg:mergeRule ldg:Refuse ; ldg:partOf ex:root .")
    for i in range(definitions - 1 - sections):
        lines.append(f"ex:sublimit{i} a ldg:AccountDefinition ; ldg:statedAmount ex:amount ; ldg:unitOfAccount ex:space ; "
                     f"ldg:admitsOwnerKind qnt:ValueSpace ; ldg:mergeRule ldg:Refuse ; ldg:partOf ex:section{i % sections} .")
    return _turtle(lines)


def one_pass(leaves: int = 5_000) -> Graph:
    """One pass over a root, `leaves - 1` sections and `leaves` leaves, each leaf its own definition and account. Each leaf takes
    one debit of 1 in the pass, and every account moved has a balance record, `2 * leaves` in all, whose remaining and available
    values are what the postings give."""
    sections = leaves - 1
    lines = [f"@prefix ldg: <{LDG}> .", f"@prefix qnt: <{QNT}> .", f"@prefix xsd: <{XSD}> .",
             "@prefix ex: <https://example.org/lattice/ledger/runtime-scale/> .",
             "ex:space a qnt:ValueSpace ; qnt:spaceKey \"runtime-scale\" ; qnt:orderKind qnt:TotalOrder ; "
             "qnt:densityKind qnt:Discrete ; qnt:spaceHash \"runtime-scale-v1\" ; qnt:additivity qnt:Extensive ; "
             "qnt:hasOperationCapability ex:sum , ex:diff .",
             "ex:sum a qnt:OperationCapability ; qnt:operationKind qnt:Sum ; qnt:resultSpace ex:space .",
             "ex:diff a qnt:OperationCapability ; qnt:operationKind qnt:Difference ; qnt:resultSpace ex:space .",
             "ex:big a qnt:Quantity ; qnt:onSpace ex:space ; qnt:numericValue \"10000\"^^xsd:decimal .",
             "ex:small a qnt:Quantity ; qnt:onSpace ex:space ; qnt:numericValue \"10\"^^xsd:decimal .",
             "ex:Owner a <http://www.w3.org/2002/07/owl#Class> . ex:owner a ex:Owner .",
             "ex:pass a ldg:Pass ; ldg:passPosition \"1\"^^xsd:integer .",
             "ex:root a ldg:AccountDefinition ; ldg:statedAmount ex:big ; ldg:unitOfAccount ex:space ; "
             "ldg:admitsOwnerKind ex:Owner ; ldg:mergeRule ldg:Refuse .",
             "ex:account-root a ldg:Account ; ldg:ofDefinition ex:root ; ldg:forOwner ex:owner .",
             f"ex:balance-root a ldg:BalanceRecord ; ldg:onAccount ex:account-root ; ldg:inPass ex:pass ; "
             f"ldg:remainingValue \"{10_000 - leaves}\"^^xsd:decimal ; ldg:availableValue \"{10_000 - leaves}\"^^xsd:decimal ."]
    drawn: dict[int, int] = {}
    for i in range(leaves):
        drawn[i % sections] = drawn.get(i % sections, 0) + 1
    for s in range(sections):
        remaining = 10 - drawn[s]
        lines += [f"ex:section{s} a ldg:AccountDefinition ; ldg:statedAmount ex:small ; ldg:unitOfAccount ex:space ; "
                  f"ldg:admitsOwnerKind ex:Owner ; ldg:mergeRule ldg:Refuse ; ldg:partOf ex:root .",
                  f"ex:account-section{s} a ldg:Account ; ldg:ofDefinition ex:section{s} ; ldg:forOwner ex:owner ; "
                  f"ldg:partOfAccount ex:account-root .",
                  f"ex:balance-section{s} a ldg:BalanceRecord ; ldg:onAccount ex:account-section{s} ; ldg:inPass ex:pass ; "
                  f"ldg:remainingValue \"{remaining}\"^^xsd:decimal ; ldg:availableValue \"{remaining}\"^^xsd:decimal ."]
    for i in range(leaves):
        lines += [f"ex:leaf{i} a ldg:AccountDefinition ; ldg:statedAmount ex:small ; ldg:unitOfAccount ex:space ; "
                  f"ldg:admitsOwnerKind ex:Owner ; ldg:mergeRule ldg:Refuse ; ldg:partOf ex:section{i % sections} .",
                  f"ex:account-leaf{i} a ldg:Account ; ldg:ofDefinition ex:leaf{i} ; ldg:forOwner ex:owner ; "
                  f"ldg:partOfAccount ex:account-section{i % sections} .",
                  f"ex:posting{i} a ldg:Posting ; ldg:onAccount ex:account-leaf{i} ; ldg:inPass ex:pass ; "
                  f"ldg:effectivePosition \"1\"^^xsd:integer ; ldg:recordedPosition \"1\"^^xsd:integer ; "
                  f"ldg:microPosition \"0\"^^xsd:integer ; ldg:direction ldg:Debit ; ldg:amountValue \"1\"^^xsd:decimal .",
                  f"ex:balance-leaf{i} a ldg:BalanceRecord ; ldg:onAccount ex:account-leaf{i} ; ldg:inPass ex:pass ; "
                  f"ldg:remainingValue \"9\"^^xsd:decimal ; ldg:availableValue \"{min(9, 10 - drawn[i % sections])}\"^^xsd:decimal ."]
    return _turtle(lines)
