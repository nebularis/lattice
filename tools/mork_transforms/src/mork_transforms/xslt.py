# SPDX-License-Identifier: MPL-2.0
"""The XSLT backend (ADR-A148 decision 3): a plan over an XML source as one XSLT 3.0 stylesheet, with no processor
extension, whose output is canonical N-Triples, each triple once and in code point order.

Names in a path are written as XPath 3.0's `Q{namespace}local`, so the stylesheet declares no prefix, and every text
from a mapping reaches it as an XPath string literal or an XML attribute value that ElementTree escapes."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Union

from rdflib import Literal, URIRef
from rdflib.namespace import RDF, XSD

from .paths import SourcePath
from .plan import Assertion, Constant, Datum, Plan, Positional, Ref, Table, Template

XSL = "http://www.w3.org/1999/XSL/Transform"
FN = "urn:lattice:mork-transforms"  # the namespace of the stylesheet's own functions
CODEPOINT = "http://www.w3.org/2005/xpath-functions/collation/codepoint"


def _s(text: str) -> str:
    """An XPath string literal."""
    return "'" + text.replace("'", "''") + "'"


def _nt_iri(iri: str) -> str:
    if any(c in iri for c in '<>"{}|^`\\') or any(ord(c) <= 0x20 for c in iri):
        raise ValueError(f"{iri!r} is not an IRI N-Triples can write")
    return f"<{iri}>"


def nt_term(term: Union[URIRef, Literal]) -> str:
    """An RDF term as N-Triples text."""
    if isinstance(term, URIRef):
        return _nt_iri(str(term))
    text = str(term).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r")
    if term.language:
        return f'"{text}"@{term.language}'
    if term.datatype is not None and term.datatype != XSD.string:
        return f'"{text}"^^{_nt_iri(str(term.datatype))}'
    return f'"{text}"'


def xpath(path: SourcePath) -> str:
    steps = []
    for step in path.steps:
        name = f"Q{{{step.namespace or ''}}}{step.name}"
        steps.append({"self": ".", "any": "*", "child": name, "attribute": "@" + name}[step.kind])
    return ("/" if path.absolute else "") + "/".join(steps)


# The position of the focus in its document: each element from the document's to it, by its local name and its 1-based
# place among its siblings of the same name, as XPath counts them, for example policies/1/policy/2/cover/1 (ADR-A148
# decision 5).
_POSITION = ("string-join(for $a in ancestor-or-self::* return encode-for-uri(local-name($a)) || '/' || "
             "(count($a/preceding-sibling::*[node-name(.) eq node-name($a)]) + 1), '/')")


class _Writer:
    def __init__(self, plan: Plan):
        self.plan = plan
        self._var = 0

    def var(self) -> str:
        self._var += 1
        return f"n{self._var}"

    def line(self, parent: ET.Element, subject: str, prop: str, obj: str) -> None:
        """A triple, each part an XPath expression whose value is N-Triples text."""
        ET.SubElement(parent, f"{{{XSL}}}sequence", select=f"{subject} || ' ' || {prop} || ' ' || {obj} || ' .'")

    def identity(self, parent: ET.Element, datum: Datum) -> tuple[ET.Element, str]:
        """Binds the datum's target, and returns the element its triples are written in and the variable's reference.
        A reference the identity reads must reach a node, else the datum is not made, as in the SPARQL backend."""
        name = self.var()
        identity, guard = datum.identity, []
        if isinstance(identity, Constant):
            select = _s(nt_term(identity.term))
        elif isinstance(identity, Positional):
            select = f"'<' || {_s(identity.prefix)} || {_POSITION} || '>'"
        else:
            pieces = []
            for piece in identity.pieces:
                if isinstance(piece, str):
                    pieces.append(_s(piece))
                else:
                    guard.append(f"exists({xpath(piece.path)})")
                    value = f"string(({xpath(piece.path)})[1])"
                    pieces.append(f"encode-for-uri({value})" if piece.encode else value)
            select = "'<' || " + " || ".join(pieces) + " || '>'"
        holder = ET.SubElement(parent, f"{{{XSL}}}if", test=" and ".join(guard)) if guard else parent
        ET.SubElement(holder, f"{{{XSL}}}variable", name=name, select=select, **{"as": "xs:string"})
        return holder, "$" + name

    def datum(self, parent: ET.Element, datum: Datum, outer: str | None) -> None:
        body = ET.SubElement(parent, f"{{{XSL}}}for-each", select=xpath(datum.path)) if datum.path is not None else parent
        holder, target = self.identity(body, datum)
        for t in datum.types:
            self.line(holder, target, _s(nt_term(RDF.type)), _s(nt_term(t)))
        if datum.glue is not None and outer is not None:
            prop, parent_is_subject = datum.glue
            if parent_is_subject:
                self.line(holder, outer, _s(nt_term(prop)), target)
            else:
                self.line(holder, target, _s(nt_term(prop)), outer)
        for assertion in datum.assertions:
            self.assertion(holder, assertion, target)
        for child in datum.children:
            self.datum(holder, child, target)

    def assertion(self, parent: ET.Element, assertion: Assertion, target: str) -> None:
        prop, value = _s(nt_term(assertion.prop)), assertion.value

        def write(at: ET.Element, obj: str) -> None:
            if assertion.inverse:
                self.line(at, obj, prop, target)
            else:
                self.line(at, target, prop, obj)

        if isinstance(value, Constant):
            write(parent, _s(nt_term(value.term)))
        elif isinstance(value, Ref):
            write(ET.SubElement(parent, f"{{{XSL}}}for-each", select=xpath(value.path)), f"{FN_PREFIX}:literal(string(.))")
        else:
            each = ET.SubElement(parent, f"{{{XSL}}}for-each", select=xpath(value.path))
            table = " else ".join(f"if (string(.) eq {_s(source)}) then {_s(nt_term(target_))}" for source, target_ in value.rows)
            mapped = ET.SubElement(each, f"{{{XSL}}}if", test=f"string(.) = ({', '.join(_s(s) for s, _ in value.rows)})")
            write(mapped, f"({table} else '')")

    def stylesheet(self) -> str:
        root = ET.Element(f"{{{XSL}}}stylesheet", {"version": "3.0", "exclude-result-prefixes": "#all"})
        ET.SubElement(root, f"{{{XSL}}}output", method="text", encoding="UTF-8")
        literal = ET.SubElement(root, f"{{{XSL}}}function", name=f"{FN_PREFIX}:literal", **{"as": "xs:string"})
        ET.SubElement(literal, f"{{{XSL}}}param", name="s", **{"as": "xs:string"})
        # N-Triples escapes \, ", line feed and carriage return in a string
        ET.SubElement(literal, f"{{{XSL}}}sequence", select="""'"' || replace(replace(replace(replace($s, '\\\\', '\\\\\\\\'), '"', '\\\\"'), codepoints-to-string(10), '\\\\n'), codepoints-to-string(13), '\\\\r') || '"'""")
        template = ET.SubElement(root, f"{{{XSL}}}template", match="/")
        lines = ET.SubElement(template, f"{{{XSL}}}variable", name="lines", **{"as": "xs:string*"})
        for datum in self.plan.roots:
            self.datum(lines, datum, None)
        each = ET.SubElement(template, f"{{{XSL}}}for-each", select=f"sort(distinct-values($lines), {_s(CODEPOINT)})")
        ET.SubElement(each, f"{{{XSL}}}value-of", select=". || codepoints-to-string(10)")
        text = ET.tostring(root, encoding="unicode")
        return text


FN_PREFIX = "fn0"


def compile_xslt(plan: Plan) -> str:
    """The stylesheet of a plan whose source is XML."""
    if plan.format != "xml":
        raise ValueError("the XSLT backend reads a plan over an XML source")
    ET.register_namespace("xsl", XSL)
    text = _Writer(plan).stylesheet()
    # ElementTree declares a namespace only where an element or attribute name uses it, and the function's prefix is
    # used only inside attribute values, so it is declared here, with the schema namespace that `as` names.
    return text.replace("<xsl:stylesheet ", f'<xsl:stylesheet xmlns:{FN_PREFIX}="{FN}" xmlns:xs="http://www.w3.org/2001/XMLSchema" ', 1)
