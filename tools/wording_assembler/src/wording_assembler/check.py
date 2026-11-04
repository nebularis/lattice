# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Stage `validate`: a form against Wording's laws (W1 to W6 and W8 hold of a form, ADR-A139 decision 6)."""

from __future__ import annotations

from typing import Iterable, Optional

from pyshacl import validate
from rdflib import Graph, URIRef
from rdflib.namespace import RDF, SH

from . import findings as fx
from .layer import Layer, load_layer
from .model import WRD, is_a


def run_shapes(data: Graph, layer: Layer, stage: str, into: Graph, focus_in: Optional[Iterable] = None) -> None:
    """Runs Wording's shapes over `data` with the specification in the data graph, and adds each result to
    `into` under `stage`. With `focus_in`, only results about those nodes are kept."""
    _, results, _ = validate(data + layer.spec, shacl_graph=layer.shapes, inference="none", advanced=True)
    keep = None if focus_in is None else set(focus_in)
    for result in sorted(results.subjects(RDF.type, SH.ValidationResult), key=lambda r: str(results.value(r, SH.resultMessage))):
        focus = results.value(result, SH.focusNode)
        if keep is not None and focus not in keep:
            continue
        fx.add(into, stage, str(results.value(result, SH.resultMessage)), focus, results.value(result, SH.value),
               results.value(result, SH.resultSeverity) or SH.Violation)


def check(form: Graph, form_iri: URIRef, *, layer: Optional[Layer] = None) -> Graph:
    """The findings of a form, as an `sh:ValidationReport`. Empty of violations when the form is sound."""
    layer = layer or load_layer()
    out = fx.report()
    if not is_a(form + layer.spec, form_iri, WRD.Wording):
        fx.add(out, "load", f"{form_iri} is not a wrd:Wording in the graph given.", form_iri)
    elif (form_iri, RDF.type, WRD.AssembledWording) in form:
        fx.add(out, "load", f"{form_iri} is an assembled wording, not a form.", form_iri)
    else:
        run_shapes(form, layer, "validate", out)
    return fx.seal(out)
