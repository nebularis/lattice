# SPDX-License-Identifier: MPL-2.0
from datetime import datetime, timezone
from pathlib import Path

import pytest
from rdflib import BNode, Graph, URIRef
from rdflib.compare import isomorphic

from mork_rdf.paths import PathError
from mork_transforms import compile_xslt, plan
from mork_transforms.engine import available, run
from mork_transforms.jolt import compile_jolt
from mork_transforms.paths import parse_json, parse_xml

EXAMPLES = Path(__file__).parent / "examples"
BASE = "urn:example:base/"
AT = datetime(2026, 1, 1, tzinfo=timezone.utc)
engines = pytest.mark.skipif(not available(), reason="run mise run bootstrap:mork-transforms for the engines")


def _plan(name: str, fmt: str, ttl: str | None = None):
    g = Graph().parse(EXAMPLES / name / f"{fmt}.mork.ttl")
    if ttl:
        g.parse(data=ttl, format="turtle")
    return plan(g, f"urn:example:mapping/{fmt}#Scheme", fmt, base=BASE, at=AT)


def _positional_as_blank(g: Graph) -> Graph:
    """The graph with each positional identity a blank node, since those differ between XML and JSON (ADR-A148)."""
    def term(t):
        return BNode(str(t)) if isinstance(t, URIRef) and str(t).startswith(BASE + "cover/") else t
    return Graph().__iadd__({(term(s), p, term(o)) for s, p, o in g})


def test_the_path_subsets():
    xml = parse_xml("/p:a/*/@q:b", {"p": "urn:p", "q": "urn:q"})
    assert xml.absolute and [(s.kind, s.namespace, s.name) for s in xml.steps] == [("child", "urn:p", "a"), ("any", None, None), ("attribute", "urn:q", "b")]
    assert parse_json("$.policies[*].covers").steps[1].kind == "each" and not parse_json("covers[*]").absolute
    for bad in ("//a", "@a/b", "x:a", "a/./b", "a[1]"):
        with pytest.raises(PathError):
            parse_xml(bad, {})
    for bad in ("$..a", "a[0]", "$['a']", ""):
        with pytest.raises(PathError):
            parse_json(bad)


def test_the_plan_reports_a_positional_identity_and_refuses_what_a_transform_cannot_carry():
    found = {(f.code, f.mapping.rsplit("#", 1)[1]) for f in _plan("policies", "xml").findings}
    assert ("PositionalIdentity", "Cover") in found
    refused = _plan("policies", "xml", """
        @prefix mork: <http://www.nebularis.org/ontologies/Mork#> . @prefix m: <urn:example:mapping/xml#> . @prefix tgt: <urn:example:target#> .
        m:Branch a mork:Lookup ; mork:mappingScheme m:Scheme ; mork:compositeBroaderMapping m:Policy ;
            mork:exactRBoxMatch tgt:branch ; mork:exactTBoxMatch tgt:Branch ; mork:dataRef "p:branch" .
        m:Note a mork:DataMapping ; mork:mappingScheme m:Scheme ; mork:compositeBroaderMapping m:Policy ;
            mork:broadRBoxCategoryMatch tgt:note ; mork:conceptName "remark" ; mork:dataRef "p:note" .
    """)
    assert {(f.code, f.mapping.rsplit("#", 1)[1]) for f in refused.errors} == {("LookupNotCarried", "Branch"), ("CreationNotCarried", "Note")}
    assert not _plan("policies", "json").errors


@engines
@pytest.mark.parametrize("name", sorted(p.name for p in EXAMPLES.iterdir()))
def test_each_example_gives_its_graph_on_saxon_and_on_jolt(name):
    expected = Graph().parse(EXAMPLES / name / "expected.nt", format="nt")
    written = run("xslt", compile_xslt(_plan(name, "xml")), (EXAMPLES / name / "source.xml").read_text(encoding="utf-8"))
    assert written.splitlines() == sorted(set(written.splitlines()))  # canonical: each triple once, in code point order
    from_xml = Graph().parse(data=written, format="nt")
    chain, findings = compile_jolt(_plan(name, "json"))
    assert not [f for f in findings if f.severity.value == "error"]
    from_json = Graph().parse(data=run("jolt", chain, (EXAMPLES / name / "source.json").read_text(encoding="utf-8")), format="json-ld")
    assert isomorphic(_positional_as_blank(from_xml), expected)
    assert isomorphic(_positional_as_blank(from_json), expected)


@engines
def test_positions_are_counted_as_each_format_counts_them_and_a_key_is_encoded_in_xslt():
    xml = run("xslt", compile_xslt(_plan("policies", "xml")), '<p:policies xmlns:p="urn:example:policy"><p:policy number="A B"><p:cover/></p:policy></p:policies>')
    assert "<urn:example:base/cover/policies/1/policy/1/cover/1> <urn:example:target#coverOf> <urn:example:base/policy/A%20B> ." in xml
    chain, findings = compile_jolt(_plan("policies", "json"))
    assert "KeyNotEncoded" in {f.code for f in findings}
    out = Graph().parse(data=run("jolt", chain, '{"policies": [{"number": "P-9", "covers": [{}, {"code": "FIRE"}]}]}'), format="json-ld")
    assert (URIRef(BASE + "cover/policies/0/covers/1"), URIRef("urn:example:target#coverOf"), URIRef(BASE + "policy/P-9")) in out
