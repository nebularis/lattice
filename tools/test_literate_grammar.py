# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The grammar of a README in the layout of ADR-A126 (slices OD2 and OD3).
Validation Packs: docs/developer/validation/OD2.md and OD3.md. Test IDs are OD2-Tn and OD3-Tn."""

from __future__ import annotations

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


SUBSECTIONS = ("Classes", "Object Properties", "Datatype Properties", "Individuals", "Disjointness and Keys",
               "Other Axioms", "Axiom Index")


def six(classes: str = "None.", object_properties: str = "None.", datatype_properties: str = "None.",
        individuals: str = "None.", disjointness: str = "None.", other: str = "None.") -> str:
    """Section 6's seven subsections, each holding the given text."""
    texts = (classes, object_properties, datatype_properties, individuals, disjointness, other, "None.")
    return "\n\n".join(f"### 6.{i} {title}\n\n{text}" for i, (title, text) in enumerate(zip(SUBSECTIONS, texts), 1))


def readme(purpose: str = "X models things.", section2: str | None = None, section3: str = ENTRY,
           section6: str | None = None, numbers: dict[int, int] | None = None) -> str:
    """A README in the layout, every section present, with the given contents."""
    body = {
        1: purpose,
        2: section2 if section2 is not None else "\n\n".join([HEADER_TABLE, PREFIX_TABLE, PEOPLE_TABLE]),
        3: section3,
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
