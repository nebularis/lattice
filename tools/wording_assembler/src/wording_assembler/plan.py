# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""A checked form compiled once into its inclusion decisions and the questions they pose (ADR-A140
decision 3). The plan is a derived artefact of the form version and the model version, with its digest
(ADR-A92), and is reusable for every assembly of that form version."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional, Tuple

from rdflib import Graph, URIRef

from . import findings as fx
from .check import check
from .layer import Layer, load_layer
from .model import BASELINE_MODEL, WRD, digest_of, digest_text


@dataclass(frozen=True)
class Inclusion:
    """One element's compiled inclusion condition."""

    element: URIRef
    profile: URIRef
    query: str                                  # compiled SPARQL, one row per decision record of the profile
    conditions: Tuple[Tuple[URIRef, URIRef, str], ...]   # (condition, governing variable, "interval" or "concept")


@dataclass(frozen=True)
class Plan:
    form_iri: URIRef
    graph: Graph                                # the form with the layer's specification, for the later stages
    inclusions: Mapping[URIRef, Inclusion]
    findings: Graph                             # the form's findings and any condition that did not compile
    digest: str                                 # of the form version and the model version

    @property
    def questions(self) -> Tuple[Tuple[URIRef, URIRef], ...]:
        """The governing variables each element's condition reads, as (element, variable), sorted."""
        return tuple(sorted(
            ((i.element, variable) for i in self.inclusions.values() for _, variable, _ in i.conditions), key=str))

    @property
    def ok(self) -> bool:
        return fx.conforms(self.findings)


def plan(form: Graph, form_iri: URIRef, *, layer: Optional[Layer] = None, context=None) -> Plan:
    """Checks `form` and compiles each `wrd:includedWhen` profile with `tools/mork_compilers`. A condition
    that needs a resolution instant or scope (a scheme with bindings) takes `context`, a
    `mork_compilers.ResolutionContext`."""
    from mork_compilers import IRCompileError, compile_profile
    from mork_compilers.eligibility_ir import ConceptPlan
    from mork_compilers.sparql_backend import PREFIXES, profile_select

    layer = layer or load_layer()
    report = check(form, form_iri, layer=layer)
    working = form + layer.spec
    inclusions = {}
    if fx.conforms(report):
        for element in sorted(set(form.subjects(WRD.includedWhen, None)), key=str):
            profile = form.value(element, WRD.includedWhen)
            try:
                compiled = compile_profile(working, profile, context)
            except IRCompileError as error:
                fx.add(report, "validate", f"The inclusion condition of {element} does not compile: {error}", element, profile)
                continue
            inclusions[element] = Inclusion(
                element, profile, PREFIXES + profile_select(compiled),
                tuple((c.condition, working.value(c.condition, WRD.readsVariable),
                       "concept" if isinstance(c, ConceptPlan) else "interval") for c in compiled.conditions))
    fx.seal(report)
    return Plan(form_iri, working, inclusions, report, digest_text([digest_of(form), str(BASELINE_MODEL)]))
