# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Where does the composite boundary's replace write the new payload? Runs the generated
``cas-replace-composite-property`` on rdflib with a one-triple payload and reports the graph
that holds it afterwards."""

from __future__ import annotations

import re
import warnings

from rdflib import Dataset, Literal, URIRef, Variable
from rdflib.namespace import XSD

from persistence import templatecheck, witness
from persistence.compiler import compile_to_graph

EX = "https://example.org/lending#"
PAT = "https://example.org/lattice/patterns#"


def payload_destination() -> dict[str, list[str]]:
    """Graph name -> the payload subjects found in it afterwards."""
    compiled, _ = compile_to_graph(witness._load_fixture(witness.EXAMPLES_DIR / "composite-property-boundary-shacl.ttl"))
    text = next(o for o in templatecheck.operations(compiled) if o.template == "cas-replace-composite-property").text
    text = text.replace("<urn:x-check:s> <urn:x-check:p> <urn:x-check:o>", "<urn:order:1> <%sstatus> \"paid\"" % EX)
    meta = re.search(r"GRAPH <(urn:g:meta/\d+)>", text).group(1)
    root = URIRef("urn:order:1")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        ds = Dataset()
        ds.graph(URIRef(meta)).add((root, URIRef(PAT + "epoch"), Literal(1)))
        ds.graph(URIRef(meta)).add((root, URIRef(PAT + "seq"), Literal(1, datatype=XSD.long)))
        ds.default_context.add((root, URIRef(EX + "status"), Literal("open")))
        values = {"root": root, "epoch": Literal(1), "expectedSeq": Literal(1, datatype=XSD.long), "nextSeq": Literal(2, datatype=XSD.long),
                  "newRev": URIRef("urn:rev:2"), "txnId": URIRef("urn:txn:a"), "requestDigest": Literal("d")}
        ds.update(text, initBindings={Variable(k): v for k, v in values.items()})
        found: dict[str, list[str]] = {}
        for s, p, o, g in ds.quads((None, URIRef(EX + "status"), None, None)):
            found.setdefault(str(g.identifier if hasattr(g, "identifier") else g), []).append(str(o))
        return found
