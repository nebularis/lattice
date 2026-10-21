# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The grammar of a README in the layout of ADR-A126 (slices OD2 and OD3).
Validation Packs: docs/developer/validation/OD2.md and OD3.md. Test IDs are OD2-Tn and OD3-Tn."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS

sys.path.insert(0, str(Path(__file__).resolve().parent))

import literate_extract  # noqa: E402
import literate_grammar as lg  # noqa: E402
import ontology_releases  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FENCE = "```"
X = "https://example.org/x"
CARRY = "https://orcid.org/0000-0002-1825-0097"

HEADER_TABLE = f"""| Document | Ontology IRI | Version IRI | Imports |
|---|---|---|---|
| `spec/x.ttl` | <{X}> | <{X}/0.2.0> | <https://example.org/y/0.1.0> |"""
PREFIX_TABLE = f"""| Prefix | Namespace |
|---|---|
| `ex:` | <{X}#> |"""
PEOPLE_TABLE = f"""| Identifier | Role | Display name |
|---|---|---|
| {CARRY} | creator | Josiah Carberry |"""
ENTRY = f'{FENCE}toml repository-catalogue\n[module]\nkind = "substrate"\nroles = []\n{FENCE}'


INDEX_REGION = '<!-- start: {"generated": "axiom-index"} -->\n<!-- end -->'
DIAGRAM_REGION = '<!-- start: {"generated": "class-diagram"} -->\n<!-- end -->'
SUBSECTIONS = ("Classes", "Object Properties", "Datatype Properties", "Individuals", "Disjointness and Keys",
               "Other Axioms", "Axiom Index")


def six(classes: str = "None.", object_properties: str = "None.", datatype_properties: str = "None.",
        individuals: str = "None.", disjointness: str = "None.", other: str = "None.") -> str:
    """Section 6's seven subsections, each holding the given text."""
    texts = (classes, object_properties, datatype_properties, individuals, disjointness, other, INDEX_REGION)
    return "\n\n".join(f"### 6.{i} {title}\n\n{text}" for i, (title, text) in enumerate(zip(SUBSECTIONS, texts), 1))


def readme(purpose: str = "X models things.", section2: str | None = None, section3: str = ENTRY,
           section6: str | None = None, numbers: dict[int, int] | None = None) -> str:
    """A README in the layout, every section present, with the given contents."""
    body = {
        1: purpose,
        2: section2 if section2 is not None else "\n\n".join([HEADER_TABLE, PREFIX_TABLE, PEOPLE_TABLE]),
        3: section3,
        4: DIAGRAM_REGION,
        6: section6 if section6 is not None else six(),
    }
    parts = ["<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->", "", "# X", ""]
    for number, title in enumerate(literate_extract.LAYOUT, 1):
        parts += [f"## {(numbers or {}).get(number, number)}. {title}", "", body.get(number, "None."), ""]
    return "\n".join(parts)


def compile_readme(text: str, layer: str = "x") -> lg.Compiled:
    result = literate_extract.scan(text)
    return lg.compile_layout(text, result, layer)


def extract(text: str, layer: str = "x") -> dict[str, str]:
    result = literate_extract.scan(text)
    compiled = lg.compile_layout(text, result, layer)
    return literate_extract.plan(result.blocks, layer, [], preambles=compiled.documents, generated_shapes=compiled.shapes)


def graph(turtle: str) -> Graph:
    return Graph().parse(data=turtle, format="turtle")


# ---- OD2: sections 1 and 2 --------------------------------------------------------------------


def test_od2_t1_section_2_and_section_1_become_the_ontology_header() -> None:
    out = extract(readme())
    assert list(out) == ["ontology/x/spec/x.ttl"]
    text = out["ontology/x/spec/x.ttl"]
    g = graph(text)
    head = URIRef(X)
    assert (head, RDF.type, OWL.Ontology) in g
    assert (head, OWL.versionIRI, URIRef(f"{X}/0.2.0")) in g
    assert (head, OWL.imports, URIRef("https://example.org/y/0.1.0")) in g
    assert (head, DCTERMS.description, Literal("X models things.")) in g
    assert (head, DCTERMS.creator, URIRef(CARRY)) in g
    assert (DCTERMS.description, RDF.type, OWL.AnnotationProperty) in g
    assert (DCTERMS.creator, RDF.type, OWL.AnnotationProperty) in g
    assert "Josiah Carberry" not in text  # a display name is never written (ADR-A126 decision 10)
    for prefix in ("@prefix ex:", "@prefix owl:", "@prefix xsd:", "@prefix dct:"):
        assert prefix in text
    assert text.startswith(literate_extract.SPDX_TTL)


def test_od2_t2_section_1_becomes_plain_text_with_links_at_the_release_tag() -> None:
    purpose = "\n".join([
        "X models `ex:Thing` and **bold** and *emphasis*, and keeps snake_case_names.",
        "It continues on a second line.",
        "",
        "- one item, see [the policy](../../docs/architecture/ontology-versioning-policy.md)",
        "- another, see [section 4](#4-overview) and [SHACL](https://www.w3.org/TR/shacl/)",
        "",
        '<!-- start: {"exclude": true} -->',
        "This sentence stays in the README only.",
        "<!-- end -->",
    ])
    text = graph(extract(readme(purpose))["ontology/x/spec/x.ttl"]).value(URIRef(X), DCTERMS.description)
    blob = f"{lg.REPOSITORY_BLOB}x-v0.2.0/"
    assert str(text) == (
        "X models ex:Thing and bold and emphasis, and keeps snake_case_names. It continues on a second line.\n\n"
        f"- one item, see the policy ({blob}docs/architecture/ontology-versioning-policy.md)\n"
        f"- another, see section 4 ({blob}ontology/x/README.md#4-overview) and SHACL (https://www.w3.org/TR/shacl/)"
    )


@pytest.mark.parametrize("purpose,message", [
    ("| a | b |\n|---|---|\n| 1 | 2 |", "a table cannot be extracted"),
    ("Text.\n\n### A subheading", "a heading cannot be extracted"),
    ("See ![a figure](figure.png).", "an image cannot be extracted"),
    ("See [outside](../../../../elsewhere.md).", "leaves the repository"),
])
def test_od2_t3_what_section_1_cannot_hold_is_refused(purpose: str, message: str) -> None:
    with pytest.raises(lg.GrammarError, match=message):
        compile_readme(readme(purpose))


def test_od2_t4_the_release_tag_follows_the_versioning_policy_for_every_current_document() -> None:
    iris = set()
    for path in subprocess.run(["git", "ls-files", "ontology/**/spec/*.ttl", "ontology/**/vocab/*.ttl"],
                               cwd=ROOT, capture_output=True, text=True, check=True).stdout.split():
        iris.update(re.findall(r"owl:versionIRI\s+<([^>]+/\d+\.\d+\.\d+)>", (ROOT / path).read_text(encoding="utf-8")))
    assert len(iris) > 20
    for iri in iris:
        name, version = ontology_releases.release_name(iri)
        assert lg.release_tag(iri) == f"{name}-v{version}"


@pytest.mark.parametrize("section2,message", [
    (PREFIX_TABLE, "no header table"),
    (HEADER_TABLE + "\n\n| Colour | Shade |\n|---|---|\n| red | dark |", "only the header, prefix and contributor tables"),
    (HEADER_TABLE.replace("`spec/x.ttl`", "`shapes/x.ttl`"), "not a .ttl file under spec/ or vocab/"),
    (HEADER_TABLE + "\n\n" + PEOPLE_TABLE.replace("creator", "author"), "not creator or contributor"),
    (HEADER_TABLE + "\n\n" + PEOPLE_TABLE.replace(CARRY, "Josiah Carberry"), "not an absolute IRI"),
    (HEADER_TABLE + "\n\n| Prefix | Namespace |\n|---|---|\n| xsd: | <https://example.org/not-xsd#> |", "standard namespace"),
    (HEADER_TABLE + "\n\n" + PREFIX_TABLE + "\n| `ex:` | <https://example.org/other#> |", "not a new prefix"),
    (HEADER_TABLE.replace("/0.2.0>", "/latest>"), "does not end in a version"),
    (HEADER_TABLE + "\n\n" + HEADER_TABLE, "two documents tables"),
])
def test_od2_t5_a_malformed_section_2_is_refused(section2: str, message: str) -> None:
    with pytest.raises(lg.GrammarError, match=message):
        compile_readme(readme(section2=section2))


def _two_documents(version: str) -> str:
    rows = HEADER_TABLE + f"\n| `spec/x-runtime.ttl` | <{X}-runtime> | <{X}-runtime/{version}> | <{X}/0.2.0> |"
    return readme(section2=rows + "\n\n" + PREFIX_TABLE, section6=six(other="\n".join([
        f'{FENCE}turtle-spec\n# @output-file "spec/x-runtime.ttl"\nex:R a owl:Class .\n{FENCE}',
        "", f"{FENCE}turtle-spec\nex:A a owl:Class .\n{FENCE}",
    ])))


def test_od2_t6_each_document_opens_with_its_own_header_and_takes_its_blocks() -> None:
    out = extract(_two_documents("0.2.0"))
    main, runtime = out["ontology/x/spec/x.ttl"], out["ontology/x/spec/x-runtime.ttl"]
    assert "ex:A a owl:Class" in main and "ex:R" not in main
    assert runtime.index(f"<{X}-runtime> a owl:Ontology") < runtime.index("ex:R a owl:Class")
    assert "@output-file" not in runtime and "@prefix ex:" in runtime
    assert (URIRef(f"{X}-runtime"), OWL.imports, URIRef(f"{X}/0.2.0")) in graph(runtime)
    with pytest.raises(ValueError, match="in unison"):
        extract(_two_documents("0.3.0"))


def test_od2_t7_a_block_for_a_document_section_2_does_not_name_is_refused() -> None:
    text = readme(section6=six(other=f'{FENCE}turtle-spec\n# @output-file "spec/other.ttl"\nex:A a owl:Class .\n{FENCE}'))
    with pytest.raises(ValueError, match="section 2's header table does not name"):
        extract(text)


@pytest.mark.parametrize("section3,problem", [
    (ENTRY, None),
    ("No entry.", "found 0, 0 of them in section 3"),
    (ENTRY + "\n\n" + ENTRY, "found 2, 2 of them in section 3"),
])
def test_od2_t8_a_migrated_readme_holds_one_catalogue_entry_in_section_3(section3: str, problem: str | None) -> None:
    result = literate_extract.scan(readme(section3=section3))
    errors, _ = literate_extract.layout_problems(result.sections, result.catalogue_lines)
    assert errors == ([] if problem is None else [next(e for e in errors if problem in e)])


def test_od2_t8b_an_entry_outside_section_3_is_refused() -> None:
    text = readme(section3="No entry here.", section6=six(other=ENTRY))
    result = literate_extract.scan(text)
    errors, _ = literate_extract.layout_problems(result.sections, result.catalogue_lines)
    assert any("found 1, 0 of them in section 3" in e for e in errors)


def test_od2_t9_extraction_writes_the_document_and_then_finds_no_drift(tmp_path: Path) -> None:
    source = tmp_path / "README.md"
    source.write_text(readme(section6=six(other=f"{FENCE}turtle-spec\nex:A a owl:Class .\n{FENCE}")), encoding="utf-8")
    args = [str(source), "--layer", "x", "--root", str(tmp_path)]
    assert literate_extract.main(args) == 0
    written = (tmp_path / "ontology/x/spec/x.ttl").read_text(encoding="utf-8")
    assert "ex:A a owl:Class" in written
    assert literate_extract.main([*args, "--check"]) == 0


# ---- OD3: section 6 to OWL -------------------------------------------------------------------------

from rdflib import BNode  # noqa: E402
from rdflib.compare import isomorphic  # noqa: E402

PREFIXES_EX_FND = f"""| Prefix | Namespace |
|---|---|
| `ex:` | <{X}#> |
| `fnd:` | <https://www.nebularis.org/neuro-semantic/lattice/foundation#> |
| `skos:` | <http://www.w3.org/2004/02/skos/core#> |"""
TURTLE_PREFIXES = f"""@prefix ex: <{X}#> .
@prefix fnd: <https://www.nebularis.org/neuro-semantic/lattice/foundation#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
"""
DECISION = """#### `ex:Decision`

**Definition.** A recorded decision, about one `ex:Profile`.

**Utility.** Holds the evidence.

**Label.** "Decision"@en

**Subclass of.** `ex:Evidenced`, `ex:Thing`

**Key.** `ex:code`, `ex:issuer`

**Restrictions.**

| Property | Values | Asserted in | Message |
|---|---|---|---|
| `ex:forProfile` | exactly 1 | | |
| `ex:hasQuestion` | min 1 | OWL | |
| `ex:usesProfile` | exactly 1 | SHACL | |
| `ex:reliedOn` | only `ex:Closure` | SHACL | A decision relies only on closures. |"""
KIND = """#### `ex:Kind`

**Definition.** A kind.

**Equivalent to.** `ex:A or ex:B`"""


def section6_readme(**parts: str) -> str:
    return readme(section2=HEADER_TABLE + "\n\n" + PREFIXES_EX_FND, section6=six(**parts))


def body(turtle: str) -> Graph:
    """The generated statements, without the ontology header and the Dublin Core declarations."""
    g = graph(turtle)
    headers = set(g.subjects(RDF.type, OWL.Ontology))
    for s, p, o in list(g):
        if s in headers or str(s).startswith(str(DCTERMS)):
            g.remove((s, p, o))
    return g


def expected(turtle: str) -> Graph:
    return Graph().parse(data=TURTLE_PREFIXES + turtle, format="turtle")


def test_od3_t1_a_class_entry_becomes_its_axioms_and_shacl_only_rows_assert_no_owl() -> None:
    out = extract(section6_readme(classes=DECISION + "\n\n" + KIND))["ontology/x/spec/x.ttl"]
    assert isomorphic(body(out), expected("""
        ex:Decision a owl:Class ; rdfs:comment "A recorded decision, about one ex:Profile." ;
            fnd:utility "Holds the evidence." ; rdfs:label "Decision"@en ;
            rdfs:subClassOf ex:Evidenced, ex:Thing,
                [ a owl:Restriction ; owl:onProperty ex:forProfile ; owl:cardinality "1"^^xsd:nonNegativeInteger ],
                [ a owl:Restriction ; owl:onProperty ex:hasQuestion ; owl:minCardinality "1"^^xsd:nonNegativeInteger ] ;
            owl:hasKey ( ex:code ex:issuer ) .
        ex:Kind a owl:Class ; rdfs:comment "A kind." ; owl:equivalentClass [ a owl:Class ; owl:unionOf ( ex:A ex:B ) ] .
    """))


@pytest.mark.parametrize("expression,turtle", [
    ("ex:A or ex:B and ex:C", "[ a owl:Class ; owl:unionOf ( ex:A [ a owl:Class ; owl:intersectionOf ( ex:B ex:C ) ] ) ]"),
    ("(ex:A or ex:B) and ex:C", "[ a owl:Class ; owl:intersectionOf ( [ a owl:Class ; owl:unionOf ( ex:A ex:B ) ] ex:C ) ]"),
    ("not ex:A and ex:B", "[ a owl:Class ; owl:intersectionOf ( [ a owl:Class ; owl:complementOf ex:A ] ex:B ) ]"),
    ("ex:p some (ex:A and ex:q value ex:v)", "[ a owl:Restriction ; owl:onProperty ex:p ; owl:someValuesFrom "
     "[ a owl:Class ; owl:intersectionOf ( ex:A [ a owl:Restriction ; owl:onProperty ex:q ; owl:hasValue ex:v ] ) ] ]"),
    ("ex:p only xsd:string", "[ a owl:Restriction ; owl:onProperty ex:p ; owl:allValuesFrom xsd:string ]"),
    ("ex:p exactly 2 ex:C", "[ a owl:Restriction ; owl:onProperty ex:p ; owl:qualifiedCardinality \"2\"^^xsd:nonNegativeInteger ; owl:onClass ex:C ]"),
    ("ex:p max 1", "[ a owl:Restriction ; owl:onProperty ex:p ; owl:maxCardinality \"1\"^^xsd:nonNegativeInteger ]"),
    ('ex:p value "x"@en', '[ a owl:Restriction ; owl:onProperty ex:p ; owl:hasValue "x"@en ]'),
    ("ex:p value 5", "[ a owl:Restriction ; owl:onProperty ex:p ; owl:hasValue 5 ]"),
    ('ex:p value "1"^^xsd:integer', '[ a owl:Restriction ; owl:onProperty ex:p ; owl:hasValue "1"^^xsd:integer ]'),
])
def test_od3_t2_manchester_expressions_become_their_owl_structures(expression: str, turtle: str) -> None:
    prefixes = {"ex": X + "#", **lg.STANDARD_PREFIXES}
    term = lg.class_expression(expression, prefixes, "test")
    assert isomorphic(expected(f"ex:S rdfs:subClassOf {lg.render(term)} ."), expected(f"ex:S rdfs:subClassOf {turtle} ."))


@pytest.mark.parametrize("expression,message", [
    ("ex:A and", "expected a class"),
    ("(ex:A or ex:B", "parenthesis is not closed"),
    ("zz:A", "prefix zz: is not declared"),
    ("ex:p exactly ex:C", "needs a whole number"),
    ("ex:p some", "expected a class"),
    ("ex:A ex:B", "unexpected 'ex:B'"),
    ("ex:A & ex:B", "unexpected '&'"),
])
def test_od3_t3_a_malformed_expression_is_refused(expression: str, message: str) -> None:
    with pytest.raises(lg.GrammarError, match=message):
        lg.class_expression(expression, {"ex": X + "#", **lg.STANDARD_PREFIXES}, "test")


def test_od3_t4_property_entries_become_their_axioms() -> None:
    objects = """#### `ex:forProfile`

**Definition.** The profile a decision is for.

**Domain.** `ex:Decision`

**Range.** `ex:Profile or ex:Group`

**Characteristics.** functional, inverse functional

**Inverse of.** `ex:hasDecision`

**Subproperty of.** `ex:relatesTo`"""
    data = """#### `ex:code`

**Definition.** A code.

**Domain.** `ex:Decision`

**Range.** `xsd:string`

**Characteristics.** functional"""
    out = extract(section6_readme(object_properties=objects, datatype_properties=data))["ontology/x/spec/x.ttl"]
    assert isomorphic(body(out), expected("""
        ex:forProfile a owl:ObjectProperty, owl:FunctionalProperty, owl:InverseFunctionalProperty ;
            rdfs:comment "The profile a decision is for." ; rdfs:domain ex:Decision ;
            rdfs:range [ a owl:Class ; owl:unionOf ( ex:Profile ex:Group ) ] ;
            owl:inverseOf ex:hasDecision ; rdfs:subPropertyOf ex:relatesTo .
        ex:code a owl:DatatypeProperty, owl:FunctionalProperty ; rdfs:comment "A code." ;
            rdfs:domain ex:Decision ; rdfs:range xsd:string .
    """))


def test_od3_t5_individuals_go_to_the_vocab_document_and_a_region_sends_entries_to_its_file() -> None:
    rows = HEADER_TABLE + (f"\n| `spec/x-runtime.ttl` | <{X}-runtime> | <{X}-runtime/0.2.0> | |"
                           f"\n| `vocab/x-vocab.ttl` | <{X}-vocab> | <{X}-vocab/0.1.0> | |")
    individuals = """| Individual | Type | Preferred label | Definition |
|---|---|---|---|
| `ex:Permitted` | `owl:NamedIndividual`, `ex:Outcome` | "Permitted"@en | Admitted. |"""
    runtime = '<!-- start: {"output-file": "spec/x-runtime.ttl"} -->\n\n' + KIND + "\n\n<!-- end -->"
    text = readme(section2=rows + "\n\n" + PREFIXES_EX_FND, section6=six(classes=runtime, individuals=individuals))
    out = extract(text)
    assert isomorphic(body(out["ontology/x/vocab/x-vocab.ttl"]), expected(
        'ex:Permitted a owl:NamedIndividual, ex:Outcome ; skos:prefLabel "Permitted"@en ; rdfs:comment "Admitted." .'))
    assert "ex:Kind" in out["ontology/x/spec/x-runtime.ttl"] and "ex:Kind" not in out["ontology/x/spec/x.ttl"]


def test_od3_t6_disjointness_keeps_the_order_of_its_members() -> None:
    disjointness = "**All disjoint.** `ex:C`, `ex:A`, `ex:B`\n\n**Disjoint.** `ex:Decision`, `ex:Profile`"
    out = extract(section6_readme(disjointness=disjointness))["ontology/x/spec/x.ttl"]
    assert isomorphic(body(out), expected(
        "[] a owl:AllDisjointClasses ; owl:members ( ex:C ex:A ex:B ) . ex:Decision owl:disjointWith ex:Profile ."))


def _closure(g: Graph, node) -> Graph:
    """The triples reachable from ``node`` through blank nodes."""
    out, todo = Graph(), [node]
    while todo:
        for s, p, o in g.triples((todo.pop(), None, None)):
            out.add((s, p, o))
            if isinstance(o, BNode):
                todo.append(o)
    return out


@pytest.mark.parametrize("subject,expression", [
    ("spc:EndBehaviour", "not (spc:hasContinuation some owl:Thing)"),
    ("spc:ConditionalBehaviour", "spc:hasGuardExpression some (spc:Expression and spc:hasExpressionSort value spc:bool_sort)"),
])
def test_od3_t7_the_grammar_states_two_of_spcs_axioms_as_spc_does(subject: str, expression: str) -> None:
    spc = Graph().parse(ROOT / "ontology/spc/spec/spc.ttl")
    ns = "http://example.org/spc#"
    term = lg.class_expression(expression, {"spc": ns, **lg.STANDARD_PREFIXES}, "test")
    ours = Graph().parse(data=f"@prefix spc: <{ns}> . @prefix owl: <http://www.w3.org/2002/07/owl#> . "
                              f"@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> . "
                              f"@prefix xsd: <http://www.w3.org/2001/XMLSchema#> . "
                              f"{subject} rdfs:subClassOf {lg.render(term)} .", format="turtle")
    named = URIRef(ns + subject.split(":")[1])
    mine = _closure(ours, next(ours.objects(named, RDFS.subClassOf)))
    theirs = [_closure(spc, o) for o in spc.objects(named, RDFS.subClassOf) if isinstance(o, BNode)]
    assert any(isomorphic(mine, candidate) for candidate in theirs)


def _entry(label_block: str, curie: str = "ex:Thing") -> str:
    return f"#### `{curie}`\n\n**Definition.** A thing.\n\n{label_block}"


@pytest.mark.parametrize("parts,message", [
    ({"classes": _entry("**Colour.** red")}, "unknown label"),
    ({"classes": _entry("**Domain.** `ex:A`")}, "does not apply to classes"),
    ({"object_properties": _entry("**Key.** `ex:a`", "ex:p")}, "does not apply to object properties"),
    ({"classes": "#### `ex:Thing`\n\n**Utility.** No definition."}, "has no \\*\\*Definition"),
    ({"classes": _entry("Some narrative without a label.")}, "starts with a label"),
    ({"classes": "#### Thing\n\n**Definition.** A thing."}, "holds one CURIE"),
    ({"classes": _entry("") + "\n\n" + _entry("")}, "has a second entry"),
    ({"classes": _entry("**Restrictions.**\n\n| Property | Cardinality |\n|---|---|\n| `ex:p` | 1 |")}, "restriction table's columns"),
    ({"classes": _entry("**Restrictions.**")}, "followed by its table"),
    ({"classes": _entry("**Restrictions.**\n\n| Property | Values | Asserted in |\n|---|---|---|\n| `ex:p` | min 1 | RDFS |")}, "blank, OWL or SHACL"),
    ({"classes": _entry("**Restrictions.**\n\n| Property | Values | Asserted in |\n|---|---|---|\n| `ex:p` | and ex:A | |")}, "do not make a restriction"),
    ({"classes": _entry("**Subclass of.** `zz:Other`")}, "prefix zz: is not declared"),
    ({"individuals": "| Individual | Colour |\n|---|---|\n| `ex:a` | red |"}, "individuals table's columns"),
    ({"disjointness": "**All disjoint.** `ex:A`"}, "two classes or more"),
    ({"disjointness": "**Disjoint.** `ex:A`, `ex:B`, `ex:C`"}, "exactly two classes"),
    ({"disjointness": "**Overlap.** `ex:A`, `ex:B`"}, "takes \\*\\*All disjoint"),
])
def test_od3_t8_a_malformed_section_6_is_refused(parts: dict, message: str) -> None:
    with pytest.raises(lg.GrammarError, match=message):
        compile_readme(section6_readme(**parts))


def test_od3_t9_section_6_needs_its_subsections_and_no_others() -> None:
    with pytest.raises(lg.GrammarError, match="missing its subsection"):
        compile_readme(readme(section2=HEADER_TABLE, section6="### 6.1 Classes\n\nNone."))
    with pytest.raises(lg.GrammarError, match="no subsection 'Appendices'"):
        compile_readme(readme(section2=HEADER_TABLE, section6=six() + "\n\n### 6.8 Appendices\n\nNone."))
    with pytest.raises(lg.GrammarError, match="needs the prefix fnd:"):
        compile_readme(readme(section2=HEADER_TABLE + "\n\n" + PREFIX_TABLE, section6=six(classes=_entry("**Utility.** Use."))))


def test_od3_t10_the_output_does_not_depend_on_the_order_of_entries() -> None:
    one = extract(section6_readme(classes=DECISION + "\n\n" + KIND))
    two = extract(section6_readme(classes=KIND + "\n\n" + DECISION))
    assert one == two


# ---- OD2-Q5 (b), 2026-10-18: blocks in a migrated README ---------------------------------------


def test_od2_t10_a_documents_blocks_are_ordered_by_their_text_not_their_place() -> None:
    first, second = f"{FENCE}turtle-spec\nex:B a owl:Class .\n{FENCE}", f"{FENCE}turtle-spec\nex:A a owl:Class .\n{FENCE}"
    one = extract(readme(section6=six(other=first + "\n\n" + second)))
    two = extract(readme(section6=six(other=second + "\n\n" + first)))
    assert one == two
    text = one["ontology/x/spec/x.ttl"]
    assert text.index("ex:A a owl:Class") < text.index("ex:B a owl:Class")


def test_od2_t11_a_block_of_a_migrated_readme_declares_no_prefix() -> None:
    block = f"{FENCE}turtle-spec\n@prefix zz: <https://example.org/zz#> .\nzz:A a owl:Class .\n{FENCE}"
    with pytest.raises(ValueError, match="section 2's prefix table is the one source of prefixes"):
        extract(readme(section6=six(other=block)))


# ---- OD4: section 6 to SHACL ----------------------------------------------------------------------

SH_PREFIX = "@prefix sh: <http://www.w3.org/ns/shacl#> .\n"
STRUCTURAL = "ontology/x/shapes/structural.ttl"


def _class_with(rows: str, curie: str = "ex:Thing") -> str:
    head = "| Property | Values | Asserted in | Message |\n|---|---|---|---|\n"
    return f"#### `{curie}`\n\n**Definition.** A thing.\n\n**Restrictions.**\n\n{head}{rows}"


def shapes_of(**parts: str) -> Graph:
    return Graph().parse(data=extract(section6_readme(**parts))[STRUCTURAL], format="turtle")


def test_od4_t1_each_flat_form_maps_to_its_shacl_and_owl_only_rows_to_none() -> None:
    rows = "\n".join([
        "| `ex:a` | exactly 1 | | |", "| `ex:b` | min 2 | | |", "| `ex:c` | max 3 | | |",
        "| `ex:d` | exactly 1 `ex:C` | | |", "| `ex:e` | only `ex:C` | | |", "| `ex:f` | only `xsd:string` | | |",
        "| `ex:g` | some `ex:C` | | |", "| `ex:h` | value `ex:v` | SHACL | Must be v. |", "| `ex:i` | min 1 | OWL | |",
    ])
    assert isomorphic(shapes_of(classes=_class_with(rows)), expected(SH_PREFIX + """
        ex:ThingShape a sh:NodeShape ; sh:targetClass ex:Thing ;
            sh:property [ sh:path ex:a ; sh:minCount 1 ; sh:maxCount 1 ],
                [ sh:path ex:b ; sh:minCount 2 ], [ sh:path ex:c ; sh:maxCount 3 ],
                [ sh:path ex:d ; sh:qualifiedValueShape [ sh:class ex:C ] ; sh:qualifiedMinCount 1 ; sh:qualifiedMaxCount 1 ],
                [ sh:path ex:e ; sh:class ex:C ], [ sh:path ex:f ; sh:datatype xsd:string ],
                [ sh:path ex:g ; sh:qualifiedValueShape [ sh:class ex:C ] ; sh:qualifiedMinCount 1 ],
                [ sh:path ex:h ; sh:hasValue ex:v ; sh:message "Must be v." ] .
    """))


def test_od4_t2_rows_for_one_property_and_message_share_a_property_shape() -> None:
    rows = "\n".join(["| `ex:n` | max 1 | | |", "| `ex:n` | only `xsd:boolean` | | |", "| `ex:n` | min 1 | SHACL | Needed. |"])
    assert isomorphic(shapes_of(classes=_class_with(rows)), expected(SH_PREFIX + """
        ex:ThingShape a sh:NodeShape ; sh:targetClass ex:Thing ;
            sh:property [ sh:path ex:n ; sh:maxCount 1 ; sh:datatype xsd:boolean ],
                [ sh:path ex:n ; sh:minCount 1 ; sh:message "Needed." ] .
    """))
    with pytest.raises(lg.GrammarError, match="state sh:maxCount twice"):
        compile_readme(section6_readme(classes=_class_with("| `ex:n` | max 1 | | |\n| `ex:n` | max 2 | | |")))


@pytest.mark.parametrize("values", ["some (`ex:A` and `ex:B`)", "only (`ex:A` or `ex:B`)", "exactly 1 (not `ex:A`)"])
def test_od4_t3_a_nested_expression_is_refused_in_shacl_and_accepted_as_owl_only(values: str) -> None:
    with pytest.raises(lg.GrammarError, match="nested expression is not checked in SHACL"):
        compile_readme(section6_readme(classes=_class_with(f"| `ex:p` | {values} | | |")))
    compiled = compile_readme(section6_readme(classes=_class_with(f"| `ex:p` | {values} | OWL | |")))
    assert compiled.shapes == {}


def test_od4_t4_hand_written_shape_blocks_name_their_file_and_never_the_generated_one() -> None:
    rows = _class_with("| `ex:a` | exactly 1 | | |")
    named = f'{FENCE}turtle-shapes\n# @output-file "shapes/constraints.ttl"\nex:S a sh:NodeShape .\n{FENCE}'
    out = extract(section6_readme(classes=rows, other=named))
    assert "ex:S a sh:NodeShape" in out["ontology/x/shapes/constraints.ttl"] and "ex:ThingShape" in out[STRUCTURAL]
    unnamed = f"{FENCE}turtle-shapes\nex:S a sh:NodeShape .\n{FENCE}"
    with pytest.raises(ValueError, match="every shape block names its file"):
        extract(section6_readme(classes=rows, other=unnamed))
    clash = f'{FENCE}turtle-shapes\n# @output-file "shapes/structural.ttl"\nex:S a sh:NodeShape .\n{FENCE}'
    with pytest.raises(ValueError, match="generated from section 6"):
        extract(section6_readme(classes=rows, other=clash))


def test_od4_t5_no_row_in_shacl_generates_no_structural_file() -> None:
    assert compile_readme(section6_readme(classes=_class_with("| `ex:a` | exactly 1 | OWL | |"))).shapes == {}
    assert STRUCTURAL not in extract(section6_readme())


def test_od4_t6_the_shapes_do_not_depend_on_the_order_of_entries_or_rows() -> None:
    a, b = _class_with("| `ex:a` | exactly 1 | | |\n| `ex:b` | min 1 | | |", "ex:A"), _class_with("| `ex:c` | max 1 | | |", "ex:B")
    b_first = _class_with("| `ex:b` | min 1 | | |\n| `ex:a` | exactly 1 | | |", "ex:A")
    assert extract(section6_readme(classes=a + "\n\n" + b))[STRUCTURAL] == extract(section6_readme(classes=b + "\n\n" + b_first))[STRUCTURAL]


def test_od4_t7_the_grammar_states_eligibilitys_decision_shape_as_its_file_does() -> None:
    elg = "https://www.nebularis.org/neuro-semantic/lattice/eligibility#"
    rows = "\n".join([
        "| `elg:forProfile` | exactly 1 | | |", "| `elg:hasQuestion` | min 1 | | |",
        "| `elg:decisionValue` | exactly 1 | | |", "| `elg:usesOperationalProfile` | exactly 1 | SHACL | |",
        "| `elg:closureReliedOn` | only `elg:Closure` | SHACL | A decision relies only on closures (ADR-A105). |",
    ])
    prefixes = PREFIXES_EX_FND + f"\n| `elg:` | <{elg}> |"
    text = readme(section2=HEADER_TABLE + "\n\n" + prefixes, section6=six(classes=_class_with(rows, "elg:EligibilityDecision")))
    ours = Graph().parse(data=extract(text)[STRUCTURAL], format="turtle")
    theirs = Graph().parse(ROOT / "ontology/eligibility/shapes/structural.ttl")
    shape = URIRef(elg + "EligibilityDecisionShape")
    assert isomorphic(_closure(ours, shape), _closure(theirs, shape))


# ---- OD5: the generated regions ---------------------------------------------------------------------

PROFILE = "#### `ex:Profile`\n\n**Definition.** A profile.\n\n**Subclass of.** `fnd:Version`"
OBJECTS = ("#### `ex:forProfile`\n\n**Definition.** The profile.\n\n**Domain.** `ex:Decision`\n\n**Range.** `ex:Profile`\n\n"
           "**Characteristics.** functional\n\n#### `ex:relatesTo`\n\n**Definition.** Relates.")
DATA = "#### `ex:code`\n\n**Definition.** A code.\n\n**Domain.** `ex:Decision`\n\n**Range.** `xsd:string`"
OUTCOMES = "| Individual | Type | Definition |\n|---|---|---|\n| `ex:Permitted` | `ex:Outcome` | Admitted. |"


def views_readme(classes: str = DECISION + "\n\n" + KIND + "\n\n" + PROFILE) -> str:
    rows = HEADER_TABLE + f"\n| `vocab/x-vocab.ttl` | <{X}-vocab> | <{X}-vocab/0.1.0> | |"
    return readme(section2=rows + "\n\n" + PREFIXES_EX_FND, section6=six(
        classes=classes, object_properties=OBJECTS, datatype_properties=DATA, individuals=OUTCOMES,
        disjointness="**Disjoint.** `ex:Decision`, `ex:Profile`"))


def region(text: str, name: str) -> str:
    start = text.index(f'<!-- start: {{"generated": "{name}"}} -->')
    return text[text.index("\n", start) + 1:text.index("<!-- end -->", start)].strip()


def test_od5_t1_the_axiom_index_summarises_every_term() -> None:
    assert region(compile_readme(views_readme()).readme, "axiom-index") == "\n".join([
        "| Term | Kind | Summary |",
        "|---|---|---|",
        "| `ex:Decision` | Class | Subclass of `ex:Evidenced`, `ex:Thing`. Key `ex:code`, `ex:issuer`. Disjoint with "
        "`ex:Profile`. Restrictions `ex:forProfile` exactly 1, `ex:hasQuestion` min 1 (OWL only), `ex:reliedOn` only "
        "`ex:Closure` (SHACL only), `ex:usesProfile` exactly 1 (SHACL only). |",
        "| `ex:Kind` | Class | Equivalent to `ex:A` or `ex:B`. |",
        "| `ex:Profile` | Class | Subclass of `fnd:Version`. Disjoint with `ex:Decision`. |",
        "| `ex:forProfile` | Object property | Domain `ex:Decision`. Range `ex:Profile`. Functional. |",
        "| `ex:relatesTo` | Object property |  |",
        "| `ex:code` | Datatype property | Domain `ex:Decision`. Range `xsd:string`. |",
        "| `ex:Permitted` | Individual | Type `ex:Outcome`. |",
    ])


def test_od5_t2_the_class_diagram_draws_classes_subclassing_associations_and_lone_properties() -> None:
    assert region(compile_readme(views_readme()).readme, "class-diagram") == "\n".join([
        "```mermaid", "classDiagram",
        "    class Decision {", "        code (xsd:string)", "        forProfile, exactly one",
        "        hasQuestion, at least one", "        reliedOn, only Closure", "        usesProfile, exactly one", "    }",
        "    class Evidenced", "    class Kind", "    class Profile", "    class Thing", "    class Version",
        "    Decision --> Profile : forProfile", "    Evidenced <|-- Decision", "    Thing <|-- Decision",
        "    Version <|-- Profile",
        '    class ObjectProperty_relatesTo["Object Property - relatesTo"]',
        "```",
    ])


def test_od5_t3_two_classes_with_one_local_name_are_qualified_by_prefix() -> None:
    clash = "#### `ex:Version`\n\n**Definition.** A version of ours.\n\n**Subclass of.** `fnd:Version`"
    diagram = region(compile_readme(views_readme(clash)).readme, "class-diagram")
    assert "fnd_Version <|-- ex_Version" in diagram


def test_od5_t4_extraction_writes_the_regions_and_a_hand_edit_is_drift(tmp_path: Path, capsys) -> None:
    source = tmp_path / "README.md"
    source.write_text(views_readme(), encoding="utf-8")
    args = [str(source), "--layer", "x", "--root", str(tmp_path)]
    assert literate_extract.main(args) == 0
    assert "| `ex:Kind` | Class |" in source.read_text(encoding="utf-8")
    assert literate_extract.main([*args, "--check"]) == 0
    source.write_text(source.read_text(encoding="utf-8").replace("| `ex:Kind` | Class |", "| `ex:Kind` | Thing |"), encoding="utf-8")
    capsys.readouterr()
    assert literate_extract.main([*args, "--check"]) == 1
    assert "its generated regions" in capsys.readouterr().err


def test_od5_t5_regions_are_not_read_as_section_6_and_refreshing_twice_changes_nothing() -> None:
    once = compile_readme(views_readme())
    twice = compile_readme(once.readme)
    assert twice.readme == once.readme and twice.documents == once.documents and twice.shapes == once.shapes


@pytest.mark.parametrize("change,message", [
    (lambda t: t.replace(INDEX_REGION, "None."), "one generated region 'axiom-index'"),
    (lambda t: t.replace(DIAGRAM_REGION, "None.").replace("## 5. Detailed Design\n\nNone.", "## 5. Detailed Design\n\n" + DIAGRAM_REGION),
     "one generated region 'class-diagram'"),
    (lambda t: t.replace(DIAGRAM_REGION, DIAGRAM_REGION + "\n\n" + DIAGRAM_REGION), "one generated region 'class-diagram'"),
    (lambda t: t.replace(INDEX_REGION, INDEX_REGION + '\n\n<!-- start: {"generated": "glossary"} -->\n<!-- end -->'), "no generated region is named 'glossary'"),
])
def test_od5_t6_each_region_is_required_once_in_its_place(change, message: str) -> None:
    with pytest.raises(lg.GrammarError, match=message):
        compile_readme(change(views_readme()))


def test_od5_t7_the_views_do_not_depend_on_the_order_of_entries() -> None:
    one = compile_readme(views_readme(DECISION + "\n\n" + KIND + "\n\n" + PROFILE)).readme
    two = compile_readme(views_readme(PROFILE + "\n\n" + KIND + "\n\n" + DECISION)).readme
    assert region(one, "axiom-index") == region(two, "axiom-index")
    assert region(one, "class-diagram") == region(two, "class-diagram")


# ---- OD6: enumeration (OD-D34) ----------------------------------------------------------------------


def test_od6_t1_an_enumerated_class_is_stated_with_braces() -> None:
    enumerated = "#### `ex:MyEnumeratedClass`\n\n**Definition.** One of two.\n\n**Equivalent to.** { `ex:MyEnum_1`, `ex:MyEnum_2` }"
    out = extract(section6_readme(classes=enumerated))["ontology/x/spec/x.ttl"]
    assert isomorphic(body(out), expected("""
        ex:MyEnumeratedClass a owl:Class ; rdfs:comment "One of two." ;
            owl:equivalentClass [ a owl:Class ; owl:oneOf ( ex:MyEnum_1 ex:MyEnum_2 ) ] .
    """))


@pytest.mark.parametrize("expression,turtle", [
    ('ex:p only {"low", "high"}', '[ a owl:Restriction ; owl:onProperty ex:p ; owl:allValuesFrom [ a rdfs:Datatype ; owl:oneOf ( "low" "high" ) ] ]'),
    ("{ex:a, ex:b} or ex:C", "[ a owl:Class ; owl:unionOf ( [ a owl:Class ; owl:oneOf ( ex:a ex:b ) ] ex:C ) ]"),
])
def test_od6_t2_enumerations_of_literals_and_inside_expressions(expression: str, turtle: str) -> None:
    term = lg.class_expression(expression, {"ex": X + "#", **lg.STANDARD_PREFIXES}, "test")
    assert isomorphic(expected(f"ex:S rdfs:subClassOf {lg.render(term)} ."), expected(f"ex:S rdfs:subClassOf {turtle} ."))


@pytest.mark.parametrize("expression,message", [
    ("{}", "holds names or literals, found '}'"),
    ('{ex:a, "b"}', "names or literals, not both"),
    ("{ex:a ex:b}", "separates its members with commas"),
    ("{ex:a, ex:b", "separates its members with commas"),
])
def test_od6_t3_a_malformed_enumeration_is_refused(expression: str, message: str) -> None:
    with pytest.raises(lg.GrammarError, match=message):
        lg.class_expression(expression, {"ex": X + "#", **lg.STANDARD_PREFIXES}, "test")


def test_od6_t4_only_an_enumeration_checked_in_shacl_is_sh_in_and_shows_in_the_views() -> None:
    row = _class_with("| `ex:direction` | only { `ex:Forward`, `ex:Inverse` } | SHACL | |")
    compiled = compile_readme(section6_readme(classes=row))
    shapes = Graph().parse(data=compiled.shapes[STRUCTURAL], format="turtle")
    assert isomorphic(shapes, expected(SH_PREFIX + """
        ex:ThingShape a sh:NodeShape ; sh:targetClass ex:Thing ;
            sh:property [ sh:path ex:direction ; sh:in ( ex:Forward ex:Inverse ) ] .
    """))
    assert "owl:oneOf" not in compiled.documents["ontology/x/spec/x.ttl"]
    assert "ex:direction` only {`ex:Forward`, `ex:Inverse`} (SHACL only)" in region(compiled.readme, "axiom-index")
    assert "direction, only one of Forward, Inverse" in region(compiled.readme, "class-diagram")


def test_od6_t5_a_comma_list_label_splits_outside_braces_only() -> None:
    entry = "#### `ex:Thing`\n\n**Definition.** A thing.\n\n**Subclass of.** { `ex:a`, `ex:b` }, `ex:C`"
    out = extract(section6_readme(classes=entry))["ontology/x/spec/x.ttl"]
    assert isomorphic(body(out), expected(
        'ex:Thing a owl:Class ; rdfs:comment "A thing." ; rdfs:subClassOf [ a owl:Class ; owl:oneOf ( ex:a ex:b ) ], ex:C .'))


# ---- D-59: the class diagram in parts, and All different -----------------------------------------------

AIM = ("#### `ex:aboutProfile`\n\n**Definition.** About a profile.\n\n**Range.** `ex:Profile`\n\n"
       "#### `ex:linksKind`\n\n**Definition.** Links.\n\n**Domain.** `ex:Profile`\n\n**Range.** `ex:Kind`")


def part_region(title: str, classes: list[str], **more) -> str:
    marker = {"generated": "class-diagram", "part": title, "classes": classes, **more}
    return f"<!-- start: {json.dumps(marker)} -->\n<!-- end -->"


def parted_readme(*regions: str, detail: bool = False) -> str:
    text = views_readme().replace("#### `ex:forProfile`", AIM + "\n\n#### `ex:forProfile`", 1)
    if detail:
        return text.replace("## 5. Detailed Design\n\nNone.", "## 5. Detailed Design\n\n" + "\n\n".join(regions)).replace(DIAGRAM_REGION, "None.")
    return text.replace(DIAGRAM_REGION, "\n\n".join(regions))


def regions_of(text: str, name: str = "class-diagram") -> list[str]:
    return re.findall(rf'<!-- start: \{{"generated": "{name}".*?-->\n(.*?)<!-- end -->', text, re.S)


THREE = [part_region("The decision", ["ex:Decision"]), part_region("Kinds and profiles", ["ex:Kind", "ex:Profile"])]


def test_d59_t1_a_part_draws_its_classes_and_a_bare_box_for_what_they_point_to() -> None:
    first, second = regions_of(compile_readme(parted_readme(*THREE)).readme)
    assert first.strip().splitlines()[0] == "**The decision**"
    assert "    class Decision {" in first and "        code (xsd:string)" in first
    for bare in ("    class Profile", "    class Evidenced", "    class Thing"):
        assert bare in first.splitlines()
    assert "    Decision --> Profile : forProfile" in first and "Kind" not in first
    assert "ObjectProperty_relatesTo" not in first and "aboutProfile" not in first
    assert "    class Profile" in second and "    Version <|-- Profile" in second and "    Profile --> Kind : linksKind" in second
    assert "    class Version" in second.splitlines() and "Decision" not in second and "forProfile" not in second


def test_d59_t2_a_property_with_no_domain_is_drawn_in_a_part_only_when_its_range_is_listed() -> None:
    first, second = regions_of(compile_readme(parted_readme(*THREE)).readme)
    assert "relatesTo" not in first + second  # no domain and no range
    assert 'class ObjectProperty_aboutProfile["Object Property - aboutProfile"]' in second
    assert "aboutProfile" not in first


def test_d59_t3_a_class_no_part_draws_is_reported() -> None:
    with pytest.raises(lg.GrammarError, match="no class-diagram part draws ex:Kind"):
        compile_readme(parted_readme(part_region("Only some", ["ex:Decision", "ex:Profile"])))


@pytest.mark.parametrize("regions,message", [
    ([part_region("A", ["ex:Decision", "ex:Kind", "ex:Profile"]), DIAGRAM_REGION], "whole or in parts, not both"),
    ([part_region("A", ["ex:Decision", "ex:Kind", "ex:Profile"]), part_region("A", ["ex:Kind"])], "two class-diagram parts are titled 'A'"),
    ([part_region("A", ["ex:Decision", "ex:Kind", "ex:Profile", "ex:Nothing"])], "ex:Nothing is not a class of section 6"),
    ([part_region("A", ["ex:Decision", "ex:Kind", "ex:Profile", "ex:forProfile"])], "ex:forProfile is not a class of section 6"),
    ([part_region(" ", ["ex:Decision", "ex:Kind", "ex:Profile"])], "needs a \"part\" title"),
    ([part_region("A", [])], "lists at least one class"),
    (['<!-- start: {"generated": "class-diagram", "part": "A"} -->\n<!-- end -->'], "without \"classes\""),
    ([part_region("A", ["ex:Decision", "ex:Kind", "ex:Profile"], enumerations="list")], "takes \"table\""),
])
def test_d59_t4_malformed_parts_are_refused(regions: list[str], message: str) -> None:
    with pytest.raises(lg.GrammarError, match=message):
        compile_readme(parted_readme(*regions))


def test_d59_t5_parts_may_sit_in_detailed_design_and_nowhere_else_outside_overview() -> None:
    compiled = compile_readme(parted_readme(*THREE, detail=True))
    assert len(regions_of(compiled.readme)) == 2
    elsewhere = parted_readme(*THREE).replace("## 8. Examples\n\nNone.", "## 8. Examples\n\n" + THREE[0])
    elsewhere = elsewhere.replace(THREE[0], "None.", 1)
    with pytest.raises(lg.GrammarError, match="sits in Overview or Detailed Design"):
        compile_readme(elsewhere)


def test_d59_t6_a_part_is_regenerated_and_drift_is_reported_per_region() -> None:
    once = compile_readme(parted_readme(*THREE))
    assert [s.split(" at ")[0] for s in once.stale] == ["class-diagram 'The decision'", "class-diagram 'Kinds and profiles'", "axiom-index"]
    again = compile_readme(once.readme)
    assert again.readme == once.readme and again.stale == ()
    edited = once.readme.replace("        code (xsd:string)", "        code (xsd:token)")
    stale = compile_readme(edited).stale
    assert stale == ("class-diagram 'The decision' at line " + str(edited[:edited.index('"part": "The decision"')].count("\n") + 1),)


def test_d59_t7_the_views_of_parts_do_not_depend_on_the_order_of_entries() -> None:
    one = compile_readme(parted_readme(*THREE)).readme
    swapped = compile_readme(parted_readme(*reversed(THREE))).readme
    assert sorted(regions_of(one)) == sorted(regions_of(swapped))


def test_d59_t8_a_region_without_classes_is_unchanged_and_enumerations_can_be_drawn_as_tables() -> None:
    plain = compile_readme(views_readme())
    assert "<<enumeration>>" not in plain.readme
    enumerated = "#### `ex:Dir`\n\n**Definition.** A direction.\n\n**Equivalent to.** { `ex:Forward`, `ex:Inverse` }"
    table = DIAGRAM_REGION.replace('"class-diagram"', '"class-diagram", "enumerations": "table"')
    text = views_readme(DECISION + "\n\n" + enumerated).replace(DIAGRAM_REGION, table)
    diagram = regions_of(compile_readme(text).readme)[0]
    assert "    class Dir {\n        <<enumeration>>\n        Forward\n        Inverse\n    }" in diagram
    # in a part the option applies to the listed classes, and a bare box has no members
    both = part_region("Dir", ["ex:Dir"], enumerations="table")
    rest = part_region("Rest", ["ex:Decision"])
    parts = compile_readme(views_readme(DECISION + "\n\n" + enumerated).replace(DIAGRAM_REGION, both + "\n\n" + rest))
    assert "<<enumeration>>" in regions_of(parts.readme)[0] and "<<enumeration>>" not in regions_of(parts.readme)[1]


@pytest.mark.parametrize("marker,message", [
    ('{"generated": "class-diagram", "colour": "red"}', "unknown key 'colour' in a generated region"),
    ('{"generated": "class-diagram", "classes": "ex:A"}', "key 'classes' of a generated region takes a list"),
    ('{"generated": "class-diagram", "classes": [1], "part": "A"}', "takes a list of CURIEs"),
    ('{"exclude": true, "part": "A"}', "a marker holds exactly one key"),
])
def test_d59_t9_a_marker_takes_the_keys_of_its_kind(marker: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        literate_extract.scan(f"<!-- start: {marker} -->\n<!-- end -->\n")


PERMITTED_AND_DENIED = ("| Individual | Type | Definition |\n|---|---|---|\n| `ex:Permitted` | `ex:Outcome` | Admitted. |\n"
                        "| `ex:Denied` | `ex:Outcome` | Refused. |\n| `ex:Open` | `ex:Outcome` | Undecided. |")


def different_readme(disjointness: str, other: str = "None.") -> str:
    rows = HEADER_TABLE + f"\n| `vocab/x-vocab.ttl` | <{X}-vocab> | <{X}-vocab/0.1.0> | |"
    return readme(section2=rows + "\n\n" + PREFIXES_EX_FND, section6=six(
        individuals=PERMITTED_AND_DENIED, disjointness=disjointness, other=other))


def test_d59_t10_all_different_is_one_owl_alldifferent_in_the_order_written() -> None:
    out = extract(different_readme("**All different.** `ex:Permitted`, `ex:Open`, `ex:Denied`"))
    assert isomorphic(body(out["ontology/x/spec/x.ttl"]), expected(
        "[] a owl:AllDifferent ; owl:distinctMembers ( ex:Permitted ex:Open ex:Denied ) ."))


def test_d59_t11_all_different_goes_where_its_region_sends_it_and_shows_in_the_index() -> None:
    sent = ('<!-- start: {"output-file": "vocab/x-vocab.ttl"} -->\n\n'
            "**All different.** `ex:Permitted`, `ex:Denied`\n\n<!-- end -->")
    compiled = compile_readme(different_readme(sent))
    out = extract(different_readme(sent))
    assert "owl:AllDifferent" in out["ontology/x/vocab/x-vocab.ttl"] and "owl:AllDifferent" not in out["ontology/x/spec/x.ttl"]
    index = region(compiled.readme, "axiom-index")
    assert "| `ex:Denied` | Individual | Type `ex:Outcome`. Different from `ex:Permitted`. |" in index
    assert "| `ex:Open` | Individual | Type `ex:Outcome`. |" in index


@pytest.mark.parametrize("paragraph,message", [
    ("**All different.** `ex:Permitted`", "two individuals or more"),
    ("**Different.** `ex:Permitted`, `ex:Denied`", "takes \\*\\*All disjoint.\\*\\*, \\*\\*Disjoint.\\*\\* or \\*\\*All different"),
])
def test_d59_t12_a_malformed_all_different_is_refused(paragraph: str, message: str) -> None:
    with pytest.raises(lg.GrammarError, match=message):
        compile_readme(different_readme(paragraph))


@pytest.mark.parametrize("fence,document", [("turtle-vocab", "vocab/x-vocab.ttl"), ("turtle-spec", "spec/x.ttl")])
def test_d59_t13_a_block_in_6_6_may_add_statements_about_an_individual_a_6_4_table_lists(fence: str, document: str) -> None:
    block = f'{FENCE}{fence}\nex:Permitted ex:logicalKey "root" .\n{FENCE}'
    out = extract(different_readme("None.", block))["ontology/x/" + document]
    g = graph(out)
    assert (URIRef(X + "#Permitted"), URIRef(X + "#logicalKey"), Literal("root")) in g
    if fence == "turtle-vocab":
        assert (URIRef(X + "#Permitted"), RDF.type, URIRef(X + "#Outcome")) in g
