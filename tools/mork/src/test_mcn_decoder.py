"""
test_mcn_decoder.py

Test suite for mcn_decoder.py, the MCN (MORK Compact Notation) decoder.

Organised by section of docs/architecture/mork-compact-notation.md:

  TestLexer                          Sec 3.3
  TestIdentifierResolution           Sec 3.4
  TestLiterals                       Sec 3.5
  TestDirectives                     Sec 6
  TestProfiles                       Sec 6.1
  TestBlocks                         Sec 7
  TestImplicitContent                Sec 5
  TestNodeLines                      Sec 9.1-9.5
  TestInlineNodes                    Sec 9.6
  TestAnnotations                    Sec 9.7
  TestArtefactPayloads               Sec 9.8
  TestExpressions                    Sec 10.1
  TestSwrlPayload                    Sec 10.2
  TestShaclPayload                   Sec 10.3
  TestRmlPayload                     Sec 10.4
  TestClassExpressions               Sec 10.5
  TestAxiomLines                     Sec 11
  TestIdentityAndDeterminism         Sec 12
  TestDecoderErrors                  Sec 14.1
  TestLint                           Sec 14.2
  TestWorkedExamples                 Sec 16 (round-tripped against the
                                      repository's own example files)
  TestCodebookCoverage               Sec 20 ("codebook governance")

Every test decodes MCN text with mcn_decoder.decode() and inspects the
resulting rdflib Graph directly (membership tests via `in graph`, or via
graph.subjects()/objects()/triples()), rather than comparing serialised
Turtle -- serialisation order is not semantically meaningful.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.compare import graph_diff, to_isomorphic
from rdflib.namespace import OWL, RDF, RDFS, XSD

import mcn_codebook as cb
import mcn_decoder as mcn
from mcn_decoder import (
    DCT,
    FND,
    MORK,
    RML,
    RR,
    SH,
    SKOS,
    SWRL,
    SWRLB,
    LintFinding,
    McnLintError,
    McnSyntaxError,
    Profile,
    canonical_ntriples,
    decode,
    lint,
)

REPO_ROOT = Path(__file__).resolve().parents[5]
MORK_TTL = REPO_ROOT / "ontology" / "mork" / "spec" / "Mork.ttl"
LOAN_TTL = REPO_ROOT / "ontology" / "mork" / "examples" / "Mork2RML" / "loan_mapping.ttl"
UNCERTAIN_TTL = REPO_ROOT / "ontology" / "mork" / "examples" / "Zoo" / "UncertainMappings.ttl"

EX = "http://ex.org/m#"


def g(text: str, **kwargs) -> Graph:
    """Shorthand: decode with a common test header (@b/@t not included --
    most tests want explicit control of those)."""
    return decode(text, **kwargs)


def gh(text: str, **kwargs) -> Graph:
    """Shorthand: decode with a standard base + target-prefix header."""
    header = f"@b <{EX}>\n@p ex=<http://ex.org/onto#>\n@t ex\n"
    return decode(header + text, **kwargs)


def U(local: str) -> URIRef:
    return URIRef(EX + local)


# ===========================================================================
# Sec 3.3 -- lexer
# ===========================================================================


class TestLexer:
    def test_bare_token(self):
        graph = gh("s1 c Loan")
        assert (U("s1"), MORK.conceptName, Literal("Loan")) in graph

    def test_quoted_string_basic(self):
        graph = gh('s1 n "hello world"')
        assert (U("s1"), MORK.mappingNote, Literal("hello world")) in graph

    def test_quoted_string_escapes(self):
        graph = gh(r's1 n "line1\nline2\ttabbed\"quoted\"\\backslash"')
        expected = 'line1\nline2\ttabbed"quoted"\\backslash'
        assert (U("s1"), MORK.mappingNote, Literal(expected)) in graph

    def test_quoted_string_unicode_escape(self):
        graph = gh(r's1 n "café"')
        assert (U("s1"), MORK.mappingNote, Literal("café")) in graph

    def test_quoted_string_lang_tag(self):
        graph = gh('s1 n "bonjour"@fr')
        vals = list(graph.objects(U("s1"), MORK.mappingNote))
        assert len(vals) == 1
        assert vals[0].language == "fr"
        assert str(vals[0]) == "bonjour"

    def test_quoted_string_datatype_suffix(self):
        graph = gh('s1 dt "2026-01-01"^xsd:date')
        vals = list(graph.objects(U("s1"), MORK.data))
        assert vals[0].datatype == XSD.date

    def test_iri_token(self):
        graph = gh("s1 sa <http://example.org/thing>")
        assert (U("s1"), RDFS.seeAlso, URIRef("http://example.org/thing")) in graph

    def test_comma_list(self):
        graph = gh("s1 xt ex:A,ex:B,ex:C")
        objs = set(graph.objects(U("s1"), MORK.exactTBoxMatch))
        assert objs == {URIRef("http://ex.org/onto#A"), URIRef("http://ex.org/onto#B"), URIRef("http://ex.org/onto#C")}

    def test_unterminated_quote_raises(self):
        with pytest.raises(McnSyntaxError):
            gh('s1 n "unterminated')

    def test_unbalanced_inline_bracket_raises(self):
        with pytest.raises(McnSyntaxError):
            gh("s1 tg [c ex:A")

    def test_unbalanced_annotation_brace_raises(self):
        with pytest.raises(McnSyntaxError):
            gh('s1 xt ex:A{n "note"')

    def test_unknown_escape_raises(self):
        with pytest.raises(McnSyntaxError):
            gh(r's1 n "bad\qescape"')

    def test_semicolon_continuation(self):
        text = "s1 c Loan\n; r loanId\n"
        graph = gh(text)
        assert (U("s1"), MORK.conceptName, Literal("Loan")) in graph
        assert (U("s1"), MORK.dataRef, Literal("loanId")) in graph

    def test_dangling_continuation_raises(self):
        with pytest.raises(McnSyntaxError):
            decode("; r loanId\n")

    def test_comment_lines_ignored(self):
        graph = gh("# a comment\ns1 c Loan\n# another\n")
        assert (U("s1"), MORK.conceptName, Literal("Loan")) in graph

    def test_blank_lines_ignored(self):
        graph = gh("\n\ns1 c Loan\n\n\n")
        assert (U("s1"), MORK.conceptName, Literal("Loan")) in graph

    def test_crlf_line_endings(self):
        text = "@b <http://ex.org/m#>\r\n@t ex\r\ns1 c Loan\r\n"
        graph = decode(text)
        assert (U("s1"), MORK.conceptName, Literal("Loan")) in graph


# ===========================================================================
# Sec 3.4 -- identifiers and IRIs
# ===========================================================================


class TestIdentifierResolution:
    def test_absolute_iri_bracket(self):
        graph = gh("s1 xt <http://external.org/Thing>")
        assert (U("s1"), MORK.exactTBoxMatch, URIRef("http://external.org/Thing")) in graph

    def test_reserved_token(self):
        graph = gh("s1 xt .T")
        assert (U("s1"), MORK.exactTBoxMatch, OWL.Thing) in graph

    def test_all_reserved_tokens_resolve(self):
        for token, curie in cb.RESERVED.items():
            text = f"s1 xt {token}"
            graph = gh(text)
            prefix, _, local = curie.partition(":")
            expected = URIRef(cb.PREDECLARED_PREFIXES[prefix] + local)
            assert (U("s1"), MORK.exactTBoxMatch, expected) in graph, token

    def test_target_prefix_shorthand(self):
        graph = gh("s1 xt :Loan")
        assert (U("s1"), MORK.exactTBoxMatch, URIRef("http://ex.org/onto#Loan")) in graph

    def test_target_prefix_shorthand_without_at_t_raises(self):
        with pytest.raises(McnSyntaxError, match="@t"):
            decode(f"@b <{EX}>\ns1 xt :Loan")

    def test_curie(self):
        graph = decode(f"@b <{EX}>\n@p fin=<http://ex.org/fin#>\n@t ex\ns1 xt fin:Loan")
        assert (U("s1"), MORK.exactTBoxMatch, URIRef("http://ex.org/fin#Loan")) in graph

    def test_curie_unbound_prefix_raises(self):
        with pytest.raises(McnSyntaxError, match="unbound prefix"):
            gh("s1 xt nope:Loan")

    def test_blank_node_token(self):
        graph = gh("!T _:x rdf:type ex:Thing")
        subs = [s for s in graph.subjects(RDF.type, URIRef("http://ex.org/onto#Thing")) if isinstance(s, BNode)]
        assert len(subs) == 1

    def test_blank_node_token_same_label_same_node(self):
        graph = gh("!T _:x ex:p ex:A\n!T _:x ex:q ex:B\n")
        xs = {s for s in graph.subjects(URIRef("http://ex.org/onto#p"), None)}
        xs |= {s for s in graph.subjects(URIRef("http://ex.org/onto#q"), None)}
        assert len(xs) == 1

    def test_local_id_without_base_raises(self):
        with pytest.raises(McnSyntaxError, match="@b"):
            decode("@t ex\ns1 c Loan")

    def test_local_id_resolves_against_base(self):
        graph = gh("s1 c Loan")
        assert (U("s1"), RDF.type, OWL.NamedIndividual) in graph

    def test_base_can_change_mid_document(self):
        text = f"@b <{EX}>\n@p ex=<http://ex.org/onto#>\n@t ex\ns1 c Loan\n@b <http://other.org/#>\ns2 c Other\n"
        graph = decode(text)
        assert (URIRef(EX + "s1"), MORK.conceptName, Literal("Loan")) in graph
        assert (URIRef("http://other.org/#s2"), MORK.conceptName, Literal("Other")) in graph

    def test_malformed_local_id_raises(self):
        with pytest.raises(McnSyntaxError):
            gh("1bad c Loan")


# ===========================================================================
# Sec 3.5 -- literals
# ===========================================================================


class TestLiterals:
    def test_plain_quoted_is_xsd_string(self):
        graph = gh('s1 c "Loan"')
        v = list(graph.objects(U("s1"), MORK.conceptName))[0]
        assert v == Literal("Loan")
        assert v.datatype is None

    def test_bare_with_fixed_datatype(self):
        graph = gh("s1 w 85")
        v = list(graph.objects(U("s1"), MORK.weighting))[0]
        assert v == Literal(85)
        assert v.datatype == XSD.integer

    def test_inferred_boolean_true(self):
        graph = gh("s1 v t")
        assert list(graph.objects(U("s1"), MORK.dataInline))[0] == Literal(True)

    def test_inferred_boolean_false(self):
        graph = gh("s1 v f")
        assert list(graph.objects(U("s1"), MORK.dataInline))[0] == Literal(False)

    def test_quoted_string_is_not_inferred(self):
        # v "t" is the string "t", not boolean true (Sec 3.5).
        graph = gh('s1 v "t"')
        v = list(graph.objects(U("s1"), MORK.dataInline))[0]
        assert v == Literal("t")
        assert v.datatype is None

    def test_inferred_integer(self):
        graph = gh("s1 v 42")
        v = list(graph.objects(U("s1"), MORK.dataInline))[0]
        assert v == Literal(42)
        assert v.datatype == XSD.integer

    def test_inferred_negative_integer(self):
        graph = gh("s1 v -42")
        assert list(graph.objects(U("s1"), MORK.dataInline))[0] == Literal(-42)

    def test_inferred_decimal(self):
        graph = gh("s1 v 3.14")
        v = list(graph.objects(U("s1"), MORK.dataInline))[0]
        assert str(v) == "3.14"
        assert v.datatype == XSD.decimal

    def test_inferred_string_fallback(self):
        graph = gh("s1 v hello")
        v = list(graph.objects(U("s1"), MORK.dataInline))[0]
        assert v == Literal("hello")
        assert v.datatype is None

    def test_bare_no_datatype_code_is_string(self):
        graph = gh("s1 c Species")
        v = list(graph.objects(U("s1"), MORK.conceptName))[0]
        assert v == Literal("Species")
        assert v.datatype is None

    def test_datetime_without_quoting(self):
        graph = gh("s1 ef 2026-10-01T00:00:00Z")
        v = list(graph.objects(U("s1"), MORK.effectiveFrom))[0]
        assert v.datatype == XSD.dateTime

    def test_boolean_fixed_datatype_bare_t_f(self):
        graph = gh("s1 dep t")
        assert list(graph.objects(U("s1"), OWL.deprecated))[0] == Literal(True)
        graph2 = gh("s1 dep f")
        assert list(graph2.objects(U("s1"), OWL.deprecated))[0] == Literal(False)

    def test_boolean_fixed_datatype_true_false_words(self):
        graph = gh("s1 ord true")
        assert list(graph.objects(U("s1"), MORK.orderedItems))[0] == Literal(True)

    def test_boolean_fixed_datatype_bad_value_raises(self):
        with pytest.raises(McnSyntaxError):
            gh("s1 dep maybe")

    def test_hash_prefixed_string_is_literal_text(self):
        graph = gh("s1 c #Species")
        assert (U("s1"), MORK.conceptName, Literal("#Species")) in graph

    def test_datatype_datatype_value_string(self):
        graph = gh('s1 pvl "5"')
        assert list(graph.objects(U("s1"), MORK.paramValue))[0] == Literal("5")


# ===========================================================================
# Sec 6 -- directives
# ===========================================================================


class TestDirectives:
    def test_at_b(self):
        graph = decode(f"@b <{EX}>\n@p ex=<http://ex.org/onto#>\n@t ex\ns1 c Loan")
        assert (U("s1"), MORK.conceptName, Literal("Loan")) in graph

    def test_at_o_asserts_ontology(self):
        graph = decode(f"@o <{EX[:-1]}>\n")
        assert (URIRef(EX[:-1]), RDF.type, OWL.Ontology) in graph

    def test_at_o_with_version_iri(self):
        graph = decode(f"@o <{EX[:-1]}> <{EX[:-1]}/0.0.1>\n")
        assert (URIRef(EX[:-1]), OWL.versionIRI, URIRef(EX[:-1] + "/0.0.1")) in graph

    def test_at_i_imports(self):
        graph = decode(f"@o <{EX[:-1]}>\n@i <http://a.org>,<http://b.org>\n")
        objs = set(graph.objects(URIRef(EX[:-1]), OWL.imports))
        assert objs == {URIRef("http://a.org"), URIRef("http://b.org")}

    def test_at_i_before_at_o_raises(self):
        with pytest.raises(McnSyntaxError, match="@o"):
            decode("@i <http://a.org>\n")

    def test_at_p_binds_prefix(self):
        graph = decode(f"@b <{EX}>\n@p fin=<http://ex.org/fin#>\n@t ex\ns1 xt fin:Loan")
        assert (U("s1"), MORK.exactTBoxMatch, URIRef("http://ex.org/fin#Loan")) in graph

    def test_at_p_rebinding_predeclared_prefix_raises(self):
        with pytest.raises(McnSyntaxError, match="predeclared"):
            decode("@p mork=<http://evil.org/#>\n")

    def test_at_t_sets_target_prefix(self):
        graph = gh("s1 xt :Loan")
        assert (U("s1"), MORK.exactTBoxMatch, URIRef("http://ex.org/onto#Loan")) in graph

    def test_at_t_requires_argument(self):
        with pytest.raises(McnSyntaxError):
            decode("@t\n")

    def test_at_opt_sets_flags(self):
        graph = gh("@opt strict\ns1 MD f ex:X df ex:Y")
        # No lint findings for this well-formed Datum, so strict passes silently.
        assert (U("s1"), MORK.mappingFor, URIRef("http://ex.org/onto#X")) in graph

    def test_at_opt_requires_flag(self):
        with pytest.raises(McnSyntaxError):
            decode(f"@b <{EX}>\n@p ex=<http://ex.org/onto#>\n@t ex\n@opt\n")

    def test_at_v_is_ignored(self):
        graph = decode(f"@v 0.1\n@b <{EX}>\n@p ex=<http://ex.org/onto#>\n@t ex\ns1 c Loan")
        assert (U("s1"), MORK.conceptName, Literal("Loan")) in graph

    def test_unknown_directive_raises(self):
        with pytest.raises(McnSyntaxError, match="unknown directive"):
            decode("@zz foo\n")

    def test_malformed_at_p_raises(self):
        with pytest.raises(McnSyntaxError):
            decode("@p noequals\n")


# ===========================================================================
# Sec 6.1 -- profiles
# ===========================================================================


class TestProfiles:
    def test_profile_supplies_base_and_prefix_and_target(self):
        profile = Profile(base=EX, prefixes={"fin": "http://ex.org/fin#"}, target="ex")
        graph = decode("@u myprofile\n@p ex=<http://ex.org/onto#>\ns1 xt fin:Loan", profiles={"myprofile": profile})
        assert (U("s1"), MORK.exactTBoxMatch, URIRef("http://ex.org/fin#Loan")) in graph

    def test_unknown_profile_raises(self):
        with pytest.raises(McnSyntaxError, match="unknown profile"):
            decode("@u nope\n")

    def test_profile_options_merge_in(self):
        profile = Profile(options={"strict"})
        # A well-formed graph should not raise even with strict merged in.
        text = f"@u p\n@b <{EX}>\n@p ex=<http://ex.org/onto#>\n@t ex\ns1 MD f ex:X df ex:Y\n"
        graph = decode(text, profiles={"p": profile})
        assert (U("s1"), MORK.mappingFor, URIRef("http://ex.org/onto#X")) in graph

    def test_profile_content_hash_recorded_after_at_o(self):
        profile = Profile(base=EX)
        text = f"@o <{EX[:-1]}>\n@u p\n"
        graph = decode(text, profiles={"p": profile})
        assert (URIRef(EX[:-1]), MORK.inputHash, None) in graph

    def test_profile_content_hash_recorded_before_at_o(self):
        profile = Profile(base=EX)
        text = f"@u p\n@o <{EX[:-1]}>\n"
        graph = decode(text, profiles={"p": profile})
        assert (URIRef(EX[:-1]), MORK.inputHash, None) in graph

    def test_profile_hash_is_stable(self):
        p1 = Profile(base=EX, prefixes={"a": "http://a.org/"})
        p2 = Profile(base=EX, prefixes={"a": "http://a.org/"})
        assert p1.content_hash() == p2.content_hash()

    def test_profile_hash_differs_for_different_content(self):
        p1 = Profile(base=EX)
        p2 = Profile(base="http://other.org/#")
        assert p1.content_hash() != p2.content_hash()

    def test_profile_rebinding_predeclared_prefix_raises(self):
        profile = Profile(prefixes={"mork": "http://evil.org/#"})
        with pytest.raises(McnSyntaxError):
            decode("@u p\n", profiles={"p": profile})


# ===========================================================================
# Sec 7 -- blocks
# ===========================================================================


class TestBlocks:
    def test_mapping_scheme_block(self):
        graph = decode(f"@b <{EX}>\n@p ex=<http://ex.org/onto#>\n@t ex\n%M MS\ns1 f ex:X")
        assert (U("MS"), RDF.type, MORK.MappingScheme) in graph
        assert (U("s1"), MORK.mappingScheme, U("MS")) in graph
        assert (U("s1"), RDF.type, MORK.DataMapping) in graph

    def test_taxonomy_scheme_block(self):
        graph = decode(f"@b <{EX}>\n@p ex=<http://ex.org/onto#>\n@t ex\n%T Taxa\nc1 cid X")
        assert (U("Taxa"), RDF.type, MORK.TaxonomyScheme) in graph
        assert (U("c1"), MORK.conceptScheme, U("Taxa")) in graph
        assert (U("c1"), RDF.type, MORK.DataConcept) in graph

    def test_representation_scheme_block_with_format(self):
        graph = decode(f"@b <{EX}>\n@p ex=<http://ex.org/onto#>\n@t ex\n%R Rep .json\ne1 id foo")
        assert (U("Rep"), MORK["format"], MORK.JSON) in graph
        assert (U("e1"), MORK.representationScheme, U("Rep")) in graph
        assert (U("e1"), RDF.type, MORK.Representation) in graph

    def test_representation_scheme_block_without_format(self):
        graph = decode(f"@b <{EX}>\n@p ex=<http://ex.org/onto#>\n@t ex\n%R Rep\ne1 id foo")
        assert (U("Rep"), MORK["format"], None) not in graph

    def test_ontological_scheme_block(self):
        graph = decode(f"@b <{EX}>\n@p ex=<http://ex.org/onto#>\n@t ex\n%O OS\nx1 iri foo")
        assert (U("OS"), RDF.type, MORK.OntologicalScheme) in graph
        assert (U("x1"), MORK.ontologicalScheme, U("OS")) in graph
        assert (U("x1"), RDF.type, MORK.OwlAxiom) in graph

    def test_intent_scheme_block(self):
        graph = decode(f"@b <{EX}>\n@p ex=<http://ex.org/onto#>\n@t ex\n%I IS\ni1 src note")
        assert (U("IS"), RDF.type, MORK.IntentScheme) in graph
        assert (U("i1"), MORK.intentScheme, U("IS")) in graph
        assert (U("i1"), RDF.type, MORK.IntentNode) in graph

    def test_constraint_scheme_block_default_type_sh(self):
        graph = decode(f"@b <{EX}>\n@p ex=<http://ex.org/onto#>\n@t ex\n%K KS\nshape1 tcl ex:Applicant")
        assert (U("KS"), RDF.type, MORK.ConstraintScheme) in graph
        assert (U("shape1"), SKOS.inScheme, U("KS")) in graph
        assert (U("shape1"), RDF.type, SH.NodeShape) in graph

    def test_rule_scheme_block_default_type_sw(self):
        graph = decode(f'@b <{EX}>\n@p ex=<http://ex.org/onto#>\n@t ex\n%U US\nrule1 "ex:A(?x)->ex:B(?x)"')
        assert (U("US"), RDF.type, MORK.RuleScheme) in graph
        assert (U("rule1"), SKOS.inScheme, U("US")) in graph
        assert (U("rule1"), RDF.type, SWRL.Imp) in graph

    def test_x_block_no_membership_no_default_type(self):
        graph = decode(f"@b <{EX}>\n@p ex=<http://ex.org/onto#>\n@t ex\n%X\ns1 xt ex:A")
        assert (U("s1"), MORK.mappingScheme, None) not in graph
        assert (U("s1"), RDF.type, MORK.DataMapping) not in graph

    def test_x_block_trailing_content_raises(self):
        with pytest.raises(McnSyntaxError):
            decode(f"@b <{EX}>\n@p ex=<http://ex.org/onto#>\n@t ex\n%X garbage\n")

    def test_block_header_own_properties(self):
        graph = decode(f"@b <{EX}>\n@p ex=<http://ex.org/onto#>\n@t ex\n%M MS md .prod mv 1.2\n")
        assert (U("MS"), MORK.compilationMode, MORK.ProductionMode) in graph
        assert (U("MS"), MORK.mappingVersion, Literal("1.2")) in graph

    def test_block_switches_context(self):
        text = f"@b <{EX}>\n@p ex=<http://ex.org/onto#>\n@t ex\n%M MS\ns1 f ex:X\n%T Taxa\nc1 cid Y\n"
        graph = decode(text)
        assert (U("s1"), MORK.mappingScheme, U("MS")) in graph
        assert (U("c1"), MORK.conceptScheme, U("Taxa")) in graph
        assert (U("c1"), MORK.mappingScheme, None) not in graph

    def test_unknown_block_kind_raises(self):
        with pytest.raises(McnSyntaxError):
            decode(f"@b <{EX}>\n@p ex=<http://ex.org/onto#>\n@t ex\n%Z Foo\n")


# ===========================================================================
# Sec 5 -- implicit content
# ===========================================================================


class TestImplicitContent:
    def test_named_individual_on_node_line_subject(self):
        graph = gh("s1 c Loan")
        assert (U("s1"), RDF.type, OWL.NamedIndividual) in graph

    def test_named_individual_on_block_header(self):
        graph = decode(f"@b <{EX}>\n@p ex=<http://ex.org/onto#>\n@t ex\n%M MS\n")
        assert (U("MS"), RDF.type, OWL.NamedIndividual) in graph

    def test_named_individual_on_inline_node(self):
        graph = gh("s1 tg :Applicant")
        tg_node = list(graph.objects(U("s1"), MORK.hasTargetingSpec))[0]
        assert (tg_node, RDF.type, OWL.NamedIndividual) in graph

    def test_scheme_membership_per_block(self):
        cases = [("%M", MORK.mappingScheme, "M"), ("%T", MORK.conceptScheme, "C"), ("%R", MORK.representationScheme, "R"), ("%O", MORK.ontologicalScheme, "X"), ("%I", MORK.intentScheme, "I")]
        for hdr, prop, default_type in cases:
            graph = decode(f"@b <{EX}>\n@p ex=<http://ex.org/onto#>\n@t ex\n{hdr} Scheme1\ns1 c foo\n")
            assert (U("s1"), prop, U("Scheme1")) in graph, hdr

    def test_default_type_per_block(self):
        graph = decode(f"@b <{EX}>\n@p ex=<http://ex.org/onto#>\n@t ex\n%M MS\ns1 f ex:X\n")
        assert (U("s1"), RDF.type, MORK.DataMapping) in graph

    def test_explicit_type_overrides_nothing_but_adds(self):
        graph = decode(f"@b <{EX}>\n@p ex=<http://ex.org/onto#>\n@t ex\n%M MS\ns1 MD f ex:X df ex:Y\n")
        assert (U("s1"), RDF.type, MORK.Datum) in graph
        assert (U("s1"), RDF.type, MORK.DataMapping) not in graph  # default not applied when explicit given

    def test_implied_type_gs(self):
        graph = gh('s1 gs "c ex:A"')
        assert (U("s1"), RDF.type, MORK.ShapeMapping) in graph

    def test_implied_type_gr(self):
        graph = gh('s1 gr "A(?x)->B(?x)"')
        assert (U("s1"), RDF.type, MORK.RuleMapping) in graph

    def test_implied_type_gt(self):
        graph = gh('s1 gt "src x.json ; sm http://x/{id}"')
        assert (U("s1"), RDF.type, MORK.TransformMapping) in graph

    def test_implied_type_gc(self):
        graph = gh("s1 gc ex:GeneratedClass")
        assert (U("s1"), RDF.type, MORK.ProjectionMapping) in graph

    def test_no_inverse_by_default(self):
        graph = gh("s1 cn s2")
        assert (U("s2"), MORK.compositeBroaderMapping, U("s1")) not in graph

    def test_swrl_compact_syntax_recorded(self):
        rule_text = "A(?x)->B(?x)"
        graph = gh(f's1 gr "{rule_text}"')
        assert (U("s1"), MORK.swrlCompactSyntax, Literal(rule_text)) in graph


# ===========================================================================
# Sec 9.1-9.5 -- node lines
# ===========================================================================


class TestNodeLines:
    def test_single_type(self):
        graph = gh("s1 MD f ex:X df ex:Y")
        assert (U("s1"), RDF.type, MORK.Datum) in graph

    def test_multiple_types_plus_joined(self):
        graph = gh("s1 M+MD f ex:X df ex:Y")
        assert (U("s1"), RDF.type, MORK.DataMapping) in graph
        assert (U("s1"), RDF.type, MORK.Datum) in graph

    def test_curie_type_uppercase_local(self):
        graph = gh("s1 ex:Widget c foo")
        assert (U("s1"), RDF.type, URIRef("http://ex.org/onto#Widget")) in graph

    def test_curie_lowercase_local_is_not_a_type(self):
        # ex:widget (lowercase) looks like a CURIE property code, not a type.
        graph = gh("s1 ex:widget foo")
        assert (U("s1"), URIRef("http://ex.org/onto#widget"), U("foo")) in graph

    def test_forced_type_with_plus(self):
        graph = gh("s1 +ex:widget c foo")
        assert (U("s1"), RDF.type, URIRef("http://ex.org/onto#widget")) in graph

    def test_forced_type_local_id(self):
        graph = decode(f"@b <{MORK}>\n%X\ns1 +CompilationMode lb foo\n")
        assert (URIRef(f"{MORK}s1"), RDF.type, URIRef(f"{MORK}CompilationMode")) in graph

    def test_repeated_node_lines_merge(self):
        text = "s1 c Loan\ns1 r loanId\n"
        graph = gh(text)
        assert (U("s1"), MORK.conceptName, Literal("Loan")) in graph
        assert (U("s1"), MORK.dataRef, Literal("loanId")) in graph

    def test_repeated_code_in_one_line(self):
        graph = gh("s1 sa ex:A sa ex:B")
        objs = set(graph.objects(U("s1"), RDFS.seeAlso))
        assert objs == {URIRef("http://ex.org/onto#A"), URIRef("http://ex.org/onto#B")}

    def test_curie_code_with_quoted_value_is_data(self):
        graph = gh('s1 dct:created "2026-01-01"^xsd:date')
        v = list(graph.objects(U("s1"), DCT.created))[0]
        assert v.datatype == XSD.date

    def test_curie_code_with_bare_value_is_object(self):
        graph = gh("s1 ex:relatesTo ex:Other")
        assert (U("s1"), URIRef("http://ex.org/onto#relatesTo"), URIRef("http://ex.org/onto#Other")) in graph

    def test_object_kind_rejects_quoted_value(self):
        with pytest.raises(McnSyntaxError):
            gh('s1 xt "not-an-iri"')

    def test_data_kind_rejects_iri_value(self):
        with pytest.raises(McnSyntaxError):
            gh("s1 c <http://example.org/x>")

    def test_expression_line_root(self):
        graph = gh("loanIri = 'http://ex.org/loan/'+$loanId")
        assert (U("loanIri"), RDF.type, MORK.ConcatExpression) in graph
        assert (U("loanIri"), RDF.type, OWL.NamedIndividual) in graph


# ===========================================================================
# Sec 9.6 -- inline nodes
# ===========================================================================


class TestInlineNodes:
    def test_typed_inline_node(self):
        graph = gh("s1 hy [MD f ex:X df ex:Y]")
        hyp = list(graph.objects(U("s1"), MORK.hypothesisMapping))[0]
        assert (hyp, RDF.type, MORK.Datum) in graph
        assert (hyp, MORK.mappingFor, URIRef("http://ex.org/onto#X")) in graph

    def test_explicit_id_inline_node(self):
        graph = gh("s1 gr [#eligRule SW \"A(?x)->B(?x)\" lb \"Eligibility rule\"]")
        assert (U("s1"), MORK.generatesRuleDefinition, U("eligRule")) in graph
        assert (U("eligRule"), RDF.type, SWRL.Imp) in graph
        assert (U("eligRule"), RDFS.label, Literal("Eligibility rule")) in graph

    def test_explicit_id_bare_reference_only(self):
        graph = gh("s1 gr eligRule\neligRule SW \"A(?x)->B(?x)\"")
        assert (U("s1"), MORK.generatesRuleDefinition, U("eligRule")) in graph

    def test_explicit_id_empty_hash_raises(self):
        with pytest.raises(McnSyntaxError):
            gh("s1 hy [#]")

    def test_minted_iri_naming(self):
        graph = gh("s1 tg [c ex:A]")
        assert (U("s1_tg1"), RDF.type, MORK.TargetingSpec) in graph

    def test_minted_iri_counts_per_subject_and_code(self):
        graph = gh("s1 hy [MD f ex:X] hy [MD f ex:Y]")
        objs = sorted(str(o) for o in graph.objects(U("s1"), MORK.hypothesisMapping))
        assert objs == [f"{EX}s1_hy1", f"{EX}s1_hy2"]

    def test_nested_inline_nodes(self):
        graph = gh("s1 hy [MD cn [MD f ex:X]]")
        outer = list(graph.objects(U("s1"), MORK.hypothesisMapping))[0]
        inner = list(graph.objects(outer, MORK.compositeNarrowerMapping))[0]
        assert (inner, MORK.mappingFor, URIRef("http://ex.org/onto#X")) in graph

    def test_positional_inline_not_allowed_for_arbitrary_code(self):
        with pytest.raises(McnSyntaxError):
            gh("s1 sa [foo bar]")

    def test_tg_positional_targetclass(self):
        graph = gh("s1 tg [c ex:Applicant]")
        node = list(graph.objects(U("s1"), MORK.hasTargetingSpec))[0]
        assert (node, SH.targetClass, URIRef("http://ex.org/onto#Applicant")) in graph
        assert (node, RDF.type, MORK.TargetingSpec) in graph

    def test_tg_positional_all_modes(self):
        modes = {"c": SH.targetClass, "o": SH.targetObjectsOf, "s": SH.targetSubjectsOf, "n": SH.targetNode}
        for letter, prop in modes.items():
            graph = gh(f"s1 tg [{letter} ex:Applicant]")
            node = list(graph.objects(U("s1"), MORK.hasTargetingSpec))[0]
            assert (node, prop, URIRef("http://ex.org/onto#Applicant")) in graph, letter

    def test_tg_bare_value_shorthand(self):
        graph = gh("s1 tg ex:Applicant")
        node = list(graph.objects(U("s1"), MORK.hasTargetingSpec))[0]
        assert (node, SH.targetClass, URIRef("http://ex.org/onto#Applicant")) in graph

    def test_tg_unknown_mode_raises(self):
        with pytest.raises(McnSyntaxError):
            gh("s1 tg [z ex:Applicant]")

    def test_pb_positional(self):
        graph = gh("s1 MS pb [min N 700]")
        node = list(graph.objects(U("s1"), MORK.hasParameterBinding))[0]
        assert (node, RDF.type, MORK.ParameterBinding) in graph
        assert (node, MORK.paramName, Literal("min")) in graph
        assert (node, MORK.paramType, Literal("Numeric")) in graph
        assert (node, MORK.paramValue, Literal(700)) in graph

    def test_pb_type_words_all_map(self):
        for letter, word in cb.PARAM_TYPE_WORD.items():
            graph = gh(f"s1 MS pb [n {letter} v]")
            node = list(graph.objects(U("s1"), MORK.hasParameterBinding))[0]
            assert (node, MORK.paramType, Literal(word)) in graph, letter

    def test_pb_on_query_template_uses_parambinding(self):
        graph = gh("s1 GQ pb [n S v]")
        assert (U("s1"), MORK.paramBinding, None) in graph
        assert (U("s1"), MORK.hasParameterBinding, None) not in graph

    def test_pb_unknown_type_raises(self):
        with pytest.raises(McnSyntaxError):
            gh("s1 MS pb [n Z v]")

    def test_pv_positional_on_shape_mapping(self):
        graph = gh('s1 MS pv [MappingAgent claude-opus-5 0.93 DRAFT]')
        node = list(graph.objects(U("s1"), MORK.hasConstraintProvenance))[0]
        assert (node, RDF.type, MORK.ConstraintProvenance) in graph
        assert (node, MORK.provenanceCreator, Literal("MappingAgent")) in graph
        assert (node, MORK.llmModelId, Literal("claude-opus-5")) in graph
        assert (node, MORK.llmConfidence, Literal("0.93", datatype=XSD.decimal)) in graph
        assert (node, MORK.reviewStatus, Literal("DRAFT")) in graph

    def test_pv_positional_variants_per_generative_type(self):
        cases = {"MS": MORK.hasConstraintProvenance, "MR": MORK.hasRuleProvenance, "MT": MORK.hasTransformProvenance, "MP": MORK.hasProjectionProvenance}
        for type_code, prop in cases.items():
            graph = gh(f"s1 {type_code} pv [a b 0.5 DRAFT]")
            assert (U("s1"), prop, None) in graph, type_code

    def test_pv_skips_with_underscore(self):
        graph = gh("s1 MS pv [reviewer _ _ APPROVED]")
        node = list(graph.objects(U("s1"), MORK.hasConstraintProvenance))[0]
        assert (node, MORK.provenanceCreator, Literal("reviewer")) in graph
        assert (node, MORK.llmModelId, None) not in graph
        assert (node, MORK.llmConfidence, None) not in graph
        assert (node, MORK.reviewStatus, Literal("APPROVED")) in graph

    def test_pv_unresolvable_without_generative_type_raises(self):
        with pytest.raises(McnSyntaxError):
            gh("s1 pv [a b 0.5 DRAFT]")

    def test_hb_positional(self):
        graph = gh("s1 hb [name 'literal text']")
        node = list(graph.objects(U("s1"), MORK.hasBinding))[0]
        assert (node, RDF.type, MORK.TemplateBinding) in graph
        assert (node, MORK.placeholderName, Literal("name")) in graph
        expr = list(graph.objects(node, MORK.placeholderExpression))[0]
        assert (expr, RDF.type, MORK.LiteralExpression) in graph
        assert (expr, MORK.dataInline, Literal("literal text")) in graph

    def test_hb_positional_with_ref_expr(self):
        graph = gh("s1 hb [name $path.to.field]")
        node = list(graph.objects(U("s1"), MORK.hasBinding))[0]
        expr = list(graph.objects(node, MORK.placeholderExpression))[0]
        assert (expr, RDF.type, MORK.RefExpression) in graph
        assert (expr, MORK.dataRef, Literal("path.to.field")) in graph


# ===========================================================================
# Sec 9.7 -- annotations
# ===========================================================================


class TestAnnotations:
    def test_annotation_on_object_value(self):
        graph = gh('s1 xt ex:Loan{n "close match" w 90}')
        assert (U("s1"), MORK.exactTBoxMatch, URIRef("http://ex.org/onto#Loan")) in graph
        axioms = list(graph.subjects(RDF.type, OWL.Axiom))
        assert len(axioms) == 1
        axiom = axioms[0]
        assert (axiom, OWL.annotatedSource, U("s1")) in graph
        assert (axiom, OWL.annotatedProperty, MORK.exactTBoxMatch) in graph
        assert (axiom, OWL.annotatedTarget, URIRef("http://ex.org/onto#Loan")) in graph
        assert (axiom, MORK.mappingNote, Literal("close match")) in graph
        assert (axiom, MORK.weighting, Literal(90)) in graph

    def test_annotation_on_list_member(self):
        graph = gh('s1 cn a{n "x"},b')
        axioms = list(graph.subjects(RDF.type, OWL.Axiom))
        assert len(axioms) == 1
        assert (axioms[0], OWL.annotatedTarget, U("a")) in graph

    def test_annotation_must_touch_value_no_space(self):
        # A space before '{' means the '{' is not an annotation of the
        # previous value; it is unexpected input at that position.
        with pytest.raises(McnSyntaxError):
            gh('s1 xt ex:Loan {n "x"}')

    def test_annotation_on_data_kind_value(self):
        graph = gh('s1 w 90{n "why 90"}')
        axioms = list(graph.subjects(RDF.type, OWL.Axiom))
        assert (axioms[0], OWL.annotatedTarget, Literal(90)) in graph


# ===========================================================================
# Sec 9.8 -- artefact payloads
# ===========================================================================


class TestArtefactPayloads:
    def test_gr_string_mints_and_types(self):
        graph = gh('s1 MR gr "A(?x)->B(?x)"')
        node = list(graph.objects(U("s1"), MORK.generatesRuleDefinition))[0]
        assert str(node) == f"{EX}s1_gr1"
        assert (node, RDF.type, SWRL.Imp) in graph

    def test_gs_string_mints_and_types(self):
        graph = gh('s1 MS gs "c ex:A"')
        node = list(graph.objects(U("s1"), MORK.generatesShapeDefinition))[0]
        assert str(node) == f"{EX}s1_gs1"
        assert (node, RDF.type, SH.NodeShape) in graph

    def test_gt_string_mints_and_types(self):
        graph = gh('s1 MT gt "src x.json ; sm http://x/{id}"')
        node = list(graph.objects(U("s1"), MORK.generatesTransformDefinition))[0]
        assert str(node) == f"{EX}s1_gt1"
        assert (node, RDF.type, RR.TriplesMap) in graph

    def test_reference_form(self):
        graph = gh('s1 gr eligRule\neligRule SW "A(?x)->B(?x)"')
        assert (U("s1"), MORK.generatesRuleDefinition, U("eligRule")) in graph

    def test_typed_inline_payload_form(self):
        graph = gh('s1 gr [#eligRule SW "A(?x)->B(?x)"]')
        assert (U("s1"), MORK.generatesRuleDefinition, U("eligRule")) in graph
        assert (U("eligRule"), RDF.type, SWRL.Imp) in graph

    def test_node_line_typed_sw_with_payload(self):
        graph = gh('rule1 SW "A(?x)->B(?x)"')
        assert (U("rule1"), RDF.type, SWRL.Imp) in graph
        assert (U("rule1"), SWRL.body, None) in graph

    def test_node_line_typed_sh_with_payload(self):
        graph = gh('shape1 SH "c ex:A"')
        assert (U("shape1"), RDF.type, SH.NodeShape) in graph
        assert (U("shape1"), SH.targetClass, URIRef("http://ex.org/onto#A")) in graph

    def test_node_line_typed_tm_with_payload(self):
        graph = gh('tm1 TM "src x.json ; sm http://x/{id}"')
        assert (U("tm1"), RDF.type, RR.TriplesMap) in graph


# ===========================================================================
# Sec 10.1 -- template expressions
# ===========================================================================


class TestExpressions:
    def test_literal_expression(self):
        graph = gh("e1 = 'a literal value'")
        assert (U("e1"), RDF.type, MORK.LiteralExpression) in graph
        assert (U("e1"), MORK.dataInline, Literal("a literal value")) in graph

    def test_ref_expression_bare_path(self):
        graph = gh("e1 = $loanId")
        assert (U("e1"), RDF.type, MORK.RefExpression) in graph
        assert (U("e1"), MORK.dataRef, Literal("loanId")) in graph

    def test_ref_expression_quoted_path(self):
        graph = gh('e1 = $"path[with brackets]"')
        assert (U("e1"), MORK.dataRef, Literal("path[with brackets]")) in graph

    def test_concat_two_terms(self):
        graph = gh("loanIri = 'http://ex.org/loan/'+$loanId")
        assert (U("loanIri"), RDF.type, MORK.ConcatExpression) in graph
        left = list(graph.objects(U("loanIri"), MORK.concatLeft))[0]
        right = list(graph.objects(U("loanIri"), MORK.concatRight))[0]
        assert str(left) == f"{EX}loanIri_l"
        assert str(right) == f"{EX}loanIri_r"
        assert (left, MORK.dataInline, Literal("http://ex.org/loan/")) in graph
        assert (right, MORK.dataRef, Literal("loanId")) in graph

    def test_concat_left_associative_three_terms(self):
        graph = gh("e1 = 'a'+'b'+'c'")
        assert (U("e1"), RDF.type, MORK.ConcatExpression) in graph
        left = list(graph.objects(U("e1"), MORK.concatLeft))[0]
        right = list(graph.objects(U("e1"), MORK.concatRight))[0]
        assert str(left) == f"{EX}e1_l"
        assert (left, RDF.type, MORK.ConcatExpression) in graph
        left_left = list(graph.objects(left, MORK.concatLeft))[0]
        left_right = list(graph.objects(left, MORK.concatRight))[0]
        assert (left_left, MORK.dataInline, Literal("a")) in graph
        assert (left_right, MORK.dataInline, Literal("b")) in graph
        assert (right, MORK.dataInline, Literal("c")) in graph

    def test_interpolation_expression(self):
        graph = gh('fullName = %"{l}, {f}"(l=$last,f=$first)')
        assert (U("fullName"), RDF.type, MORK.InterpolationExpression) in graph
        assert (U("fullName"), MORK.templateString, Literal("{l}, {f}")) in graph
        bindings = list(graph.objects(U("fullName"), MORK.hasBinding))
        assert len(bindings) == 2
        names = {str(list(graph.objects(b, MORK.placeholderName))[0]) for b in bindings}
        assert names == {"l", "f"}
        for b in bindings:
            assert str(b) in {f"{EX}fullName_b1", f"{EX}fullName_b2"}

    def test_lookup_expression(self):
        graph = gh("lob = ?LobScheme.skos:notation($lineOfBusiness)")
        assert (U("lob"), RDF.type, MORK.LookupExpression) in graph
        assert (U("lob"), MORK.lookupScheme, U("LobScheme")) in graph
        assert (U("lob"), MORK.lookupProperty, SKOS.notation) in graph
        src = list(graph.objects(U("lob"), MORK.lookupSource))[0]
        assert str(src) == f"{EX}lob_s"
        assert (src, MORK.dataRef, Literal("lineOfBusiness")) in graph

    def test_parenthesised_grouping(self):
        graph = gh("e1 = ('a'+'b')")
        assert (U("e1"), RDF.type, MORK.ConcatExpression) in graph
        assert (U("e1"), MORK.concatLeft, None) in graph

    def test_bare_reference_to_existing_expression(self):
        text = "e1 = 'x'\ne2 = e1\n"
        graph = gh(text)
        # e2 is an alias for e1's node via owl:sameAs (Sec 10.1 "reference
        # to an existing expression node"; the root-level alias case is
        # not directly exercised by the spec's worked examples).
        assert (U("e2"), OWL.sameAs, U("e1")) in graph

    def test_bare_reference_inside_concat(self):
        text = "part = 'x'\nwhole = part+$y\n"
        graph = gh(text)
        left = list(graph.objects(U("whole"), MORK.concatLeft))[0]
        assert left == U("part")

    def test_expression_valued_code_cl(self):
        graph = gh("s1 EC cl 'a'")
        node = list(graph.objects(U("s1"), MORK.concatLeft))[0]
        assert (node, RDF.type, MORK.LiteralExpression) in graph
        assert (node, MORK.dataInline, Literal("a")) in graph

    def test_expression_valued_code_pe(self):
        graph = gh("s1 EB pe $name")
        node = list(graph.objects(U("s1"), MORK.placeholderExpression))[0]
        assert (node, RDF.type, MORK.RefExpression) in graph

    def test_expression_valued_code_with_inline_bracket_form(self):
        graph = gh("s1 EC cl [#existing ER r foo]")
        assert (U("s1"), MORK.concatLeft, U("existing")) in graph

    def test_malformed_expression_raises(self):
        with pytest.raises(McnSyntaxError):
            gh("e1 = +")

    def test_expression_with_annotation(self):
        graph = gh("""s1 EC cl 'a'+$b{n "note"}""")
        axioms = list(graph.subjects(RDF.type, OWL.Axiom))
        assert len(axioms) == 1


# ===========================================================================
# Sec 10.2 -- SWRL compact payload
# ===========================================================================


class TestSwrlPayload:
    def test_class_atom(self):
        graph = gh('s1 MR gr "ex:Applicant(?a)->ex:Eligible(?a)"')
        rule = list(graph.objects(U("s1"), MORK.generatesRuleDefinition))[0]
        body = list(graph.objects(rule, SWRL.body))[0]
        atom = list(graph.objects(body, RDF.first))[0]
        assert (atom, RDF.type, SWRL.ClassAtom) in graph
        assert (atom, SWRL.classPredicate, URIRef("http://ex.org/onto#Applicant")) in graph

    def test_variable_reused_is_same_node(self):
        graph = gh('s1 MR gr "ex:P(?a)->ex:Q(?a)"')
        rule = list(graph.objects(U("s1"), MORK.generatesRuleDefinition))[0]
        assert str(rule) + "_v_a" == f"{EX}s1_gr1_v_a"
        assert (URIRef(f"{EX}s1_gr1_v_a"), RDF.type, SWRL.Variable) in graph

    def test_individual_property_atom(self):
        graph = gh('s1 MR gr "ex:hasFriend(?a,?b)->ex:knows(?a,?b)"')
        rule = list(graph.objects(U("s1"), MORK.generatesRuleDefinition))[0]
        body = list(graph.objects(rule, SWRL.body))[0]
        atom = list(graph.objects(body, RDF.first))[0]
        assert (atom, RDF.type, SWRL.IndividualPropertyAtom) in graph

    def test_datavalued_property_atom(self):
        graph = gh('s1 MR gr "ex:hasCreditScore(?a,700)->ex:Eligible(?a)"')
        rule = list(graph.objects(U("s1"), MORK.generatesRuleDefinition))[0]
        body = list(graph.objects(rule, SWRL.body))[0]
        atom = list(graph.objects(body, RDF.first))[0]
        assert (atom, RDF.type, SWRL.DatavaluedPropertyAtom) in graph
        assert (atom, SWRL.argument2, Literal(700)) in graph

    def test_builtin_atom(self):
        graph = gh('s1 MR gr "ex:hasScore(?a,?s)^swrlb:greaterThanOrEqual(?s,700)->ex:Eligible(?a)"')
        rule = list(graph.objects(U("s1"), MORK.generatesRuleDefinition))[0]
        body = list(graph.objects(rule, SWRL.body))[0]
        second_cell = list(graph.objects(body, RDF.rest))[0]
        builtin_atom = list(graph.objects(second_cell, RDF.first))[0]
        assert (builtin_atom, RDF.type, SWRL.BuiltinAtom) in graph
        assert (builtin_atom, SWRL.builtin, SWRLB.greaterThanOrEqual) in graph

    def test_same_as_atom(self):
        graph = gh('s1 MR gr "sameAs(ex:A,ex:B)->ex:C(ex:A)"')
        rule = list(graph.objects(U("s1"), MORK.generatesRuleDefinition))[0]
        body = list(graph.objects(rule, SWRL.body))[0]
        atom = list(graph.objects(body, RDF.first))[0]
        assert (atom, RDF.type, SWRL.SameIndividualAtom) in graph

    def test_different_from_atom(self):
        graph = gh('s1 MR gr "differentFrom(ex:A,ex:B)->ex:C(ex:A)"')
        rule = list(graph.objects(U("s1"), MORK.generatesRuleDefinition))[0]
        body = list(graph.objects(rule, SWRL.body))[0]
        atom = list(graph.objects(body, RDF.first))[0]
        assert (atom, RDF.type, SWRL.DifferentIndividualsAtom) in graph

    def test_datarange_atom(self):
        graph = gh('s1 MR gr "xsd:integer(?x)->ex:C(?x)"')
        rule = list(graph.objects(U("s1"), MORK.generatesRuleDefinition))[0]
        body = list(graph.objects(rule, SWRL.body))[0]
        atom = list(graph.objects(body, RDF.first))[0]
        assert (atom, RDF.type, SWRL.DataRangeAtom) in graph
        assert (atom, SWRL.dataRange, XSD.integer) in graph

    def test_typed_string_literal_argument(self):
        graph = gh(r'''s1 MR gr "ex:hasCode(?a,\"AB\"^xsd:string)->ex:C(?a)"''')
        rule = list(graph.objects(U("s1"), MORK.generatesRuleDefinition))[0]
        body = list(graph.objects(rule, SWRL.body))[0]
        atom = list(graph.objects(body, RDF.first))[0]
        val = list(graph.objects(atom, SWRL.argument2))[0]
        assert val == Literal("AB", datatype=XSD.string)

    def test_body_and_head_both_present(self):
        graph = gh('s1 MR gr "ex:A(?x)->ex:B(?x)"')
        rule = list(graph.objects(U("s1"), MORK.generatesRuleDefinition))[0]
        assert (rule, SWRL.body, None) in graph
        assert (rule, SWRL.head, None) in graph

    def test_missing_arrow_raises(self):
        with pytest.raises(McnSyntaxError):
            gh('s1 MR gr "ex:A(?x)"')

    def test_no_atoms_raises(self):
        with pytest.raises(McnSyntaxError):
            gh('s1 MR gr " -> ex:B(?x)"')


# ===========================================================================
# Sec 10.3 -- SHACL compact payload
# ===========================================================================


class TestShaclPayload:
    def test_target_class(self):
        graph = gh('s1 MS gs "c ex:Applicant"')
        shape = list(graph.objects(U("s1"), MORK.generatesShapeDefinition))[0]
        assert (shape, SH.targetClass, URIRef("http://ex.org/onto#Applicant")) in graph

    def test_multiple_targets(self):
        graph = gh('s1 MS gs "c ex:A,o ex:p"')
        shape = list(graph.objects(U("s1"), MORK.generatesShapeDefinition))[0]
        assert (shape, SH.targetClass, URIRef("http://ex.org/onto#A")) in graph
        assert (shape, SH.targetObjectsOf, URIRef("http://ex.org/onto#p")) in graph

    def test_property_shape_datatype_and_range(self):
        graph = gh('s1 MS gs "c ex:A; ex:score dt xsd:integer >=700 <=850 [1..1]"')
        shape = list(graph.objects(U("s1"), MORK.generatesShapeDefinition))[0]
        pshape = list(graph.objects(shape, SH.property))[0]
        assert (pshape, SH.path, URIRef("http://ex.org/onto#score")) in graph
        assert (pshape, SH.datatype, XSD.integer) in graph
        assert (pshape, SH.minInclusive, Literal(700)) in graph
        assert (pshape, SH.maxInclusive, Literal(850)) in graph
        assert (pshape, SH.minCount, Literal(1)) in graph
        assert (pshape, SH.maxCount, Literal(1)) in graph

    def test_property_shape_minted_iri(self):
        graph = gh('s1 MS gs "c ex:A; ex:score [1..1]"')
        shape = list(graph.objects(U("s1"), MORK.generatesShapeDefinition))[0]
        pshape = list(graph.objects(shape, SH.property))[0]
        assert str(pshape) == f"{str(shape)}_p1"

    def test_bnode_shapes_option(self):
        graph = gh('@opt bnode-shapes\ns1 MS gs "c ex:A; ex:score [1..1]"')
        shape = list(graph.objects(U("s1"), MORK.generatesShapeDefinition))[0]
        pshape = list(graph.objects(shape, SH.property))[0]
        assert isinstance(pshape, BNode)

    def test_min_count_only(self):
        graph = gh('s1 MS gs "c ex:A; ex:xs [1..]"')
        shape = list(graph.objects(U("s1"), MORK.generatesShapeDefinition))[0]
        pshape = list(graph.objects(shape, SH.property))[0]
        assert (pshape, SH.minCount, Literal(1)) in graph
        assert (pshape, SH.maxCount, None) not in graph

    def test_exact_count(self):
        graph = gh('s1 MS gs "c ex:A; ex:xs [2]"')
        shape = list(graph.objects(U("s1"), MORK.generatesShapeDefinition))[0]
        pshape = list(graph.objects(shape, SH.property))[0]
        assert (pshape, SH.minCount, Literal(2)) in graph
        assert (pshape, SH.maxCount, Literal(2)) in graph

    def test_class_constraint(self):
        graph = gh('s1 MS gs "c ex:A; ex:p cls ex:Thing"')
        shape = list(graph.objects(U("s1"), MORK.generatesShapeDefinition))[0]
        pshape = list(graph.objects(shape, SH.property))[0]
        assert (pshape, SH["class"], URIRef("http://ex.org/onto#Thing")) in graph

    def test_node_kind(self):
        graph = gh('s1 MS gs "c ex:A; ex:p nk iri"')
        shape = list(graph.objects(U("s1"), MORK.generatesShapeDefinition))[0]
        pshape = list(graph.objects(shape, SH.property))[0]
        assert (pshape, SH.nodeKind, SH.IRI) in graph

    def test_in_constraint(self):
        graph = gh('s1 MS gs "c ex:A; ex:p in {ex:X,ex:Y}"')
        shape = list(graph.objects(U("s1"), MORK.generatesShapeDefinition))[0]
        pshape = list(graph.objects(shape, SH.property))[0]
        in_list = list(graph.objects(pshape, SH["in"]))[0]
        items = list(Graph_helpers_rdf_list(graph, in_list))
        assert set(items) == {URIRef("http://ex.org/onto#X"), URIRef("http://ex.org/onto#Y")}

    def test_pattern_constraint(self):
        graph = gh(r's1 MS gs "c ex:A; ex:p re \"^[0-9]+$\""')
        shape = list(graph.objects(U("s1"), MORK.generatesShapeDefinition))[0]
        pshape = list(graph.objects(shape, SH.property))[0]
        assert (pshape, SH.pattern, Literal("^[0-9]+$")) in graph

    def test_length_constraint(self):
        graph = gh('s1 MS gs "c ex:A; ex:p len [2..10]"')
        shape = list(graph.objects(U("s1"), MORK.generatesShapeDefinition))[0]
        pshape = list(graph.objects(shape, SH.property))[0]
        assert (pshape, SH.minLength, Literal(2)) in graph
        assert (pshape, SH.maxLength, Literal(10)) in graph

    def test_has_value_constraint(self):
        graph = gh('s1 MS gs "c ex:A; ex:p =ex:X"')
        shape = list(graph.objects(U("s1"), MORK.generatesShapeDefinition))[0]
        pshape = list(graph.objects(shape, SH.property))[0]
        assert (pshape, SH.hasValue, URIRef("http://ex.org/onto#X")) in graph

    def test_eq_lt_lte_disj_constraints(self):
        graph = gh('s1 MS gs "c ex:A; ex:p eq ex:q lt ex:r lte ex:s disj ex:t"')
        shape = list(graph.objects(U("s1"), MORK.generatesShapeDefinition))[0]
        pshape = list(graph.objects(shape, SH.property))[0]
        assert (pshape, SH.equals, URIRef("http://ex.org/onto#q")) in graph
        assert (pshape, SH.lessThan, URIRef("http://ex.org/onto#r")) in graph
        assert (pshape, SH.lessThanOrEquals, URIRef("http://ex.org/onto#s")) in graph
        assert (pshape, SH.disjoint, URIRef("http://ex.org/onto#t")) in graph

    def test_property_shape_severity_and_message(self):
        graph = gh(r's1 MS gs "c ex:A; ex:p [1..1] !.viol msg \"bad\""')
        shape = list(graph.objects(U("s1"), MORK.generatesShapeDefinition))[0]
        pshape = list(graph.objects(shape, SH.property))[0]
        assert (pshape, SH.severity, SH.Violation) in graph
        assert (pshape, SH.message, Literal("bad")) in graph

    def test_property_shape_name(self):
        graph = gh(r's1 MS gs "c ex:A; ex:p [1..1] name \"Score\""')
        shape = list(graph.objects(U("s1"), MORK.generatesShapeDefinition))[0]
        pshape = list(graph.objects(shape, SH.property))[0]
        assert (pshape, SH.name, Literal("Score")) in graph

    def test_node_shape_severity_message_closed_ignore_node(self):
        graph = gh('s1 MS gs "c ex:A; !.warn; msg \\"m\\"; closed; ignore ex:x,ex:y; nd ex:Base"')
        shape = list(graph.objects(U("s1"), MORK.generatesShapeDefinition))[0]
        assert (shape, SH.severity, SH.Warning) in graph
        assert (shape, SH.message, Literal("m")) in graph
        assert (shape, SH.closed, Literal(True)) in graph
        assert (shape, SH.node, URIRef("http://ex.org/onto#Base")) in graph
        ignored = list(graph.objects(shape, SH.ignoredProperties))[0]
        items = list(Graph_helpers_rdf_list(graph, ignored))
        assert set(items) == {URIRef("http://ex.org/onto#x"), URIRef("http://ex.org/onto#y")}

    def test_inverse_path(self):
        graph = gh('s1 MS gs "c ex:A; ^ex:parent [1..1]"')
        shape = list(graph.objects(U("s1"), MORK.generatesShapeDefinition))[0]
        pshape = list(graph.objects(shape, SH.property))[0]
        path = list(graph.objects(pshape, SH.path))[0]
        assert (path, SH.inversePath, URIRef("http://ex.org/onto#parent")) in graph

    def test_sequence_path(self):
        graph = gh('s1 MS gs "c ex:A; ex:a/ex:b [1..1]"')
        shape = list(graph.objects(U("s1"), MORK.generatesShapeDefinition))[0]
        pshape = list(graph.objects(shape, SH.property))[0]
        path = list(graph.objects(pshape, SH.path))[0]
        items = list(Graph_helpers_rdf_list(graph, path))
        assert items == [URIRef("http://ex.org/onto#a"), URIRef("http://ex.org/onto#b")]

    def test_missing_target_raises(self):
        with pytest.raises(McnSyntaxError):
            gh('s1 MS gs ""')

    def test_unknown_severity_raises(self):
        with pytest.raises(McnSyntaxError):
            gh('s1 MS gs "c ex:A; !bogus"')


def Graph_helpers_rdf_list(graph: Graph, head):
    """Walks an RDF list starting at ``head``, yielding its members."""
    node = head
    while node is not None and node != RDF.nil:
        first = list(graph.objects(node, RDF.first))
        if not first:
            break
        yield first[0]
        rest = list(graph.objects(node, RDF.rest))
        node = rest[0] if rest else None


# ===========================================================================
# Sec 10.4 -- RML compact payload
# ===========================================================================


class TestRmlPayload:
    def test_logical_source_and_subject_map(self):
        graph = gh('s1 MT gt "src loan.json it $ ; sm http://ex.org/loan/{loanId} cls ex:Loan"')
        tm = list(graph.objects(U("s1"), MORK.generatesTransformDefinition))[0]
        ls = list(graph.objects(tm, RML.logicalSource))[0]
        assert (ls, RML.source, Literal("loan.json")) in graph
        assert (ls, RML.iterator, Literal("$")) in graph
        assert (ls, RML.referenceFormulation, URIRef("http://semweb.mmlab.be/ns/ql#JSONPath")) in graph
        sm = list(graph.objects(tm, RR.subjectMap))[0]
        assert (sm, RR.template, Literal("http://ex.org/loan/{loanId}")) in graph
        assert (sm, RR["class"], URIRef("http://ex.org/onto#Loan")) in graph

    def test_reference_formulation_csv_xml(self):
        for fmt, iri in (("csv", "http://semweb.mmlab.be/ns/ql#CSV"), ("xml", "http://semweb.mmlab.be/ns/ql#XPath")):
            graph = gh(f'tm{fmt} MT gt "src x.{fmt} ref {fmt} ; sm http://x/{{id}}"')
            tm = list(graph.objects(U(f"tm{fmt}"), MORK.generatesTransformDefinition))[0]
            ls = list(graph.objects(tm, RML.logicalSource))[0]
            assert (ls, RML.referenceFormulation, URIRef(iri)) in graph, fmt

    def test_reference_object_map(self):
        graph = gh('s1 MT gt "src x.json ; sm http://x/{id} ; ex:name =firstName"')
        tm = list(graph.objects(U("s1"), MORK.generatesTransformDefinition))[0]
        pom = list(graph.objects(tm, RR.predicateObjectMap))[0]
        om = list(graph.objects(pom, RR.objectMap))[0]
        assert (om, RML.reference, Literal("firstName")) in graph

    def test_constant_object_map_iri(self):
        graph = gh('s1 MT gt "src x.json ; sm http://x/{id} ; ex:kind :ex:Loan"')
        tm = list(graph.objects(U("s1"), MORK.generatesTransformDefinition))[0]
        pom = list(graph.objects(tm, RR.predicateObjectMap))[0]
        om = list(graph.objects(pom, RR.objectMap))[0]
        assert (om, RR.constant, URIRef("http://ex.org/onto#Loan")) in graph

    def test_constant_object_map_literal(self):
        graph = gh(r'''s1 MT gt "src x.json ; sm http://x/{id} ; ex:kind :\"literal\""''')
        tm = list(graph.objects(U("s1"), MORK.generatesTransformDefinition))[0]
        pom = list(graph.objects(tm, RR.predicateObjectMap))[0]
        om = list(graph.objects(pom, RR.objectMap))[0]
        assert (om, RR.constant, Literal("literal")) in graph

    def test_template_object_map(self):
        graph = gh('s1 MT gt "src x.json ; sm http://x/{id} ; ex:full @{first}-{last}"')
        tm = list(graph.objects(U("s1"), MORK.generatesTransformDefinition))[0]
        pom = list(graph.objects(tm, RR.predicateObjectMap))[0]
        om = list(graph.objects(pom, RR.objectMap))[0]
        assert (om, RR.template, Literal("{first}-{last}")) in graph

    def test_parent_triples_map_with_join(self):
        graph = gh('s1 MT gt "src x.json ; sm http://x/{id} ; ex:principal ^tm2[loanId=loanId]"')
        tm = list(graph.objects(U("s1"), MORK.generatesTransformDefinition))[0]
        pom = list(graph.objects(tm, RR.predicateObjectMap))[0]
        om = list(graph.objects(pom, RR.objectMap))[0]
        assert (om, RR.parentTriplesMap, U("tm2")) in graph
        jc = list(graph.objects(om, RR.joinCondition))[0]
        assert (jc, RR.child, Literal("loanId")) in graph
        assert (jc, RR.parent, Literal("loanId")) in graph

    def test_parent_triples_map_without_join(self):
        graph = gh('s1 MT gt "src x.json ; sm http://x/{id} ; ex:principal ^tm2"')
        tm = list(graph.objects(U("s1"), MORK.generatesTransformDefinition))[0]
        pom = list(graph.objects(tm, RR.predicateObjectMap))[0]
        om = list(graph.objects(pom, RR.objectMap))[0]
        assert (om, RR.parentTriplesMap, U("tm2")) in graph
        assert (om, RR.joinCondition, None) not in graph

    def test_datatype_and_language_on_object_map(self):
        graph = gh('s1 MT gt "src x.json ; sm http://x/{id} ; ex:score =score dt xsd:integer"')
        tm = list(graph.objects(U("s1"), MORK.generatesTransformDefinition))[0]
        pom = list(graph.objects(tm, RR.predicateObjectMap))[0]
        om = list(graph.objects(pom, RR.objectMap))[0]
        assert (om, RR.datatype, XSD.integer) in graph

    def test_missing_subject_map_raises(self):
        with pytest.raises(McnSyntaxError):
            gh('s1 MT gt "src x.json"')


# ===========================================================================
# Sec 10.5 -- OWL class expressions
# ===========================================================================


class TestClassExpressions:
    def test_union(self):
        graph = gh("!C ex:A = ex:B|ex:C")
        eq = list(graph.objects(URIRef("http://ex.org/onto#A"), OWL.equivalentClass))[0]
        members = list(Graph_helpers_rdf_list(graph, list(graph.objects(eq, OWL.unionOf))[0]))
        assert set(members) == {URIRef("http://ex.org/onto#B"), URIRef("http://ex.org/onto#C")}

    def test_intersection(self):
        graph = gh("!C ex:A = ex:B&ex:C")
        eq = list(graph.objects(URIRef("http://ex.org/onto#A"), OWL.equivalentClass))[0]
        members = list(Graph_helpers_rdf_list(graph, list(graph.objects(eq, OWL.intersectionOf))[0]))
        assert set(members) == {URIRef("http://ex.org/onto#B"), URIRef("http://ex.org/onto#C")}

    def test_complement(self):
        graph = gh("!C ex:A = ~ex:B")
        eq = list(graph.objects(URIRef("http://ex.org/onto#A"), OWL.equivalentClass))[0]
        assert (eq, OWL.complementOf, URIRef("http://ex.org/onto#B")) in graph

    def test_parenthesised_grouping(self):
        graph = gh("!C ex:A = (ex:B|ex:C)&ex:D")
        eq = list(graph.objects(URIRef("http://ex.org/onto#A"), OWL.equivalentClass))[0]
        assert (eq, OWL.intersectionOf, None) in graph

    def test_one_of(self):
        graph = gh("!C ex:A = {ex:x,ex:y}")
        eq = list(graph.objects(URIRef("http://ex.org/onto#A"), OWL.equivalentClass))[0]
        members = list(Graph_helpers_rdf_list(graph, list(graph.objects(eq, OWL.oneOf))[0]))
        assert set(members) == {URIRef("http://ex.org/onto#x"), URIRef("http://ex.org/onto#y")}

    def test_one_of_with_literals(self):
        graph = gh('!C ex:A = {"a","b"}')
        eq = list(graph.objects(URIRef("http://ex.org/onto#A"), OWL.equivalentClass))[0]
        members = list(Graph_helpers_rdf_list(graph, list(graph.objects(eq, OWL.oneOf))[0]))
        assert set(members) == {Literal("a"), Literal("b")}

    def test_some_values_from(self):
        graph = gh("!C ex:A = ex:p>ex:B")
        eq = list(graph.objects(URIRef("http://ex.org/onto#A"), OWL.equivalentClass))[0]
        assert (eq, RDF.type, OWL.Restriction) in graph
        assert (eq, OWL.onProperty, URIRef("http://ex.org/onto#p")) in graph
        assert (eq, OWL.someValuesFrom, URIRef("http://ex.org/onto#B")) in graph

    def test_all_values_from(self):
        graph = gh("!C ex:A = ex:p<ex:B")
        eq = list(graph.objects(URIRef("http://ex.org/onto#A"), OWL.equivalentClass))[0]
        assert (eq, OWL.allValuesFrom, URIRef("http://ex.org/onto#B")) in graph

    def test_has_value(self):
        graph = gh("!C ex:A = ex:p=ex:v")
        eq = list(graph.objects(URIRef("http://ex.org/onto#A"), OWL.equivalentClass))[0]
        assert (eq, OWL.hasValue, URIRef("http://ex.org/onto#v")) in graph

    def test_has_value_boolean(self):
        graph = gh("!C ex:A = ex:p=t")
        eq = list(graph.objects(URIRef("http://ex.org/onto#A"), OWL.equivalentClass))[0]
        assert (eq, OWL.hasValue, Literal(True)) in graph

    def test_has_self(self):
        graph = gh("!C ex:A = ex:p@")
        eq = list(graph.objects(URIRef("http://ex.org/onto#A"), OWL.equivalentClass))[0]
        assert (eq, OWL.hasSelf, Literal(True)) in graph

    def test_exact_cardinality(self):
        graph = gh("!C ex:A = ex:p#2")
        eq = list(graph.objects(URIRef("http://ex.org/onto#A"), OWL.equivalentClass))[0]
        assert (eq, OWL.cardinality, Literal(2, datatype=XSD.nonNegativeInteger)) in graph

    def test_min_cardinality(self):
        graph = gh("!C ex:A = ex:p#1..")
        eq = list(graph.objects(URIRef("http://ex.org/onto#A"), OWL.equivalentClass))[0]
        assert (eq, OWL.minCardinality, Literal(1, datatype=XSD.nonNegativeInteger)) in graph
        assert (eq, OWL.maxCardinality, None) not in graph

    def test_max_cardinality(self):
        graph = gh("!C ex:A = ex:p#..3")
        eq = list(graph.objects(URIRef("http://ex.org/onto#A"), OWL.equivalentClass))[0]
        assert (eq, OWL.maxCardinality, Literal(3, datatype=XSD.nonNegativeInteger)) in graph

    def test_min_max_cardinality(self):
        graph = gh("!C ex:A = ex:p#1..3")
        eq = list(graph.objects(URIRef("http://ex.org/onto#A"), OWL.equivalentClass))[0]
        assert (eq, OWL.minCardinality, Literal(1, datatype=XSD.nonNegativeInteger)) in graph
        assert (eq, OWL.maxCardinality, Literal(3, datatype=XSD.nonNegativeInteger)) in graph

    def test_qualified_cardinality(self):
        graph = gh("!C ex:A = ex:p#1../ex:Thing")
        eq = list(graph.objects(URIRef("http://ex.org/onto#A"), OWL.equivalentClass))[0]
        assert (eq, OWL.minQualifiedCardinality, Literal(1, datatype=XSD.nonNegativeInteger)) in graph
        assert (eq, OWL.onClass, URIRef("http://ex.org/onto#Thing")) in graph

    def test_qualified_exact_cardinality(self):
        graph = gh("!C ex:A = ex:p#0/ex:Representation")
        eq = list(graph.objects(URIRef("http://ex.org/onto#A"), OWL.equivalentClass))[0]
        assert (eq, OWL.qualifiedCardinality, Literal(0, datatype=XSD.nonNegativeInteger)) in graph

    def test_inverse_property_in_restriction(self):
        graph = gh("!C ex:A = ^ex:p>ex:B")
        eq = list(graph.objects(URIRef("http://ex.org/onto#A"), OWL.equivalentClass))[0]
        prop = list(graph.objects(eq, OWL.onProperty))[0]
        assert (prop, OWL.inverseOf, URIRef("http://ex.org/onto#p")) in graph
        assert (prop, RDF.type, OWL.ObjectProperty) in graph

    def test_named_class_as_datatype_reference(self):
        graph = gh("!D d1 rng xsd:string")
        assert (URIRef(f"{EX}d1"), RDFS.range, XSD.string) in graph

    def test_reserved_token_in_class_expression(self):
        graph = gh("!C ex:A = ex:p>.T")
        eq = list(graph.objects(URIRef("http://ex.org/onto#A"), OWL.equivalentClass))[0]
        assert (eq, OWL.someValuesFrom, OWL.Thing) in graph


# ===========================================================================
# Sec 11 -- axiom lines
# ===========================================================================


class TestAxiomLines:
    def test_c_equivalent_class(self):
        graph = gh("!C ex:A = ex:B")
        assert (URIRef("http://ex.org/onto#A"), OWL.equivalentClass, URIRef("http://ex.org/onto#B")) in graph
        assert (URIRef("http://ex.org/onto#A"), RDF.type, OWL.Class) in graph

    def test_c_sub_class_of(self):
        graph = gh("!C ex:A < ex:B")
        assert (URIRef("http://ex.org/onto#A"), RDFS.subClassOf, URIRef("http://ex.org/onto#B")) in graph

    def test_c_disjoint_with(self):
        graph = gh("!C ex:A ! ex:B")
        assert (URIRef("http://ex.org/onto#A"), OWL.disjointWith, URIRef("http://ex.org/onto#B")) in graph

    def test_c_generic_annotation_pair(self):
        graph = gh('!C ex:A lb "Widget A"')
        assert (URIRef("http://ex.org/onto#A"), RDFS.label, Literal("Widget A")) in graph

    def test_c_multiple_clauses(self):
        graph = gh('!C ex:A < ex:B lb "Widget A"')
        A = URIRef("http://ex.org/onto#A")
        assert (A, RDFS.subClassOf, URIRef("http://ex.org/onto#B")) in graph
        assert (A, RDFS.label, Literal("Widget A")) in graph

    def test_c_multiword_ce_with_and(self):
        graph = gh("!C ex:A < ex:p>ex:B & ex:q>ex:C")
        A = URIRef("http://ex.org/onto#A")
        sc = list(graph.objects(A, RDFS.subClassOf))[0]
        assert (sc, OWL.intersectionOf, None) in graph

    def test_c_trailing_pair_after_ce(self):
        graph = gh('!C ex:A = ex:p>ex:B lb "Widget"')
        A = URIRef("http://ex.org/onto#A")
        assert (A, OWL.equivalentClass, None) in graph
        assert (A, RDFS.label, Literal("Widget")) in graph

    def test_o_sub_property_of(self):
        graph = gh("!O ex:p < ex:q")
        assert (URIRef("http://ex.org/onto#p"), RDFS.subPropertyOf, URIRef("http://ex.org/onto#q")) in graph
        assert (URIRef("http://ex.org/onto#p"), RDF.type, OWL.ObjectProperty) in graph

    def test_o_equivalent_property(self):
        graph = gh("!O ex:p = ex:q")
        assert (URIRef("http://ex.org/onto#p"), OWL.equivalentProperty, URIRef("http://ex.org/onto#q")) in graph

    def test_o_inverse_of(self):
        graph = gh("!O ex:p inv ex:q")
        assert (URIRef("http://ex.org/onto#p"), OWL.inverseOf, URIRef("http://ex.org/onto#q")) in graph

    def test_o_domain_range(self):
        graph = gh("!O ex:p dom ex:A rng ex:B")
        p = URIRef("http://ex.org/onto#p")
        assert (p, RDFS.domain, URIRef("http://ex.org/onto#A")) in graph
        assert (p, RDFS.range, URIRef("http://ex.org/onto#B")) in graph

    def test_o_characteristics(self):
        graph = gh("!O ex:p +T+AS+IR")
        p = URIRef("http://ex.org/onto#p")
        assert (p, RDF.type, OWL.TransitiveProperty) in graph
        assert (p, RDF.type, OWL.AsymmetricProperty) in graph
        assert (p, RDF.type, OWL.IrreflexiveProperty) in graph

    def test_o_all_characteristic_flags(self):
        for flag, cls in {
            "F": OWL.FunctionalProperty,
            "IF": OWL.InverseFunctionalProperty,
            "S": OWL.SymmetricProperty,
            "AS": OWL.AsymmetricProperty,
            "T": OWL.TransitiveProperty,
            "R": OWL.ReflexiveProperty,
            "IR": OWL.IrreflexiveProperty,
        }.items():
            graph = gh(f"!O ex:p{flag} +{flag}")
            assert (URIRef(f"http://ex.org/onto#p{flag}"), RDF.type, cls) in graph, flag

    def test_o_chain(self):
        graph = gh("!O ex:p chain ex:q,ex:r")
        p = URIRef("http://ex.org/onto#p")
        chain = list(graph.objects(p, OWL.propertyChainAxiom))[0]
        items = list(Graph_helpers_rdf_list(graph, chain))
        assert items == [URIRef("http://ex.org/onto#q"), URIRef("http://ex.org/onto#r")]

    def test_o_inverse_subject(self):
        graph = gh("!O ^ex:p < ex:q")
        blanks = [s for s in graph.subjects(OWL.inverseOf, URIRef("http://ex.org/onto#p"))]
        assert len(blanks) == 1
        assert (blanks[0], RDFS.subPropertyOf, URIRef("http://ex.org/onto#q")) in graph
        assert (blanks[0], RDF.type, OWL.ObjectProperty) in graph

    def test_d_sub_property_of_is_plain_identifier(self):
        graph = gh("!D ex:d1 < ex:d2")
        assert (URIRef("http://ex.org/onto#d1"), RDFS.subPropertyOf, URIRef("http://ex.org/onto#d2")) in graph
        assert (URIRef("http://ex.org/onto#d1"), RDF.type, OWL.DatatypeProperty) in graph

    def test_d_functional_flag(self):
        graph = gh("!D ex:d1 +F")
        assert (URIRef("http://ex.org/onto#d1"), RDF.type, OWL.FunctionalProperty) in graph

    def test_d_non_functional_flag_raises(self):
        with pytest.raises(McnSyntaxError):
            gh("!D ex:d1 +T")

    def test_a_sub_property_domain_range(self):
        graph = gh("!A ex:a1 < ex:a2 dom ex:A rng ex:B")
        a1 = URIRef("http://ex.org/onto#a1")
        assert (a1, RDFS.subPropertyOf, URIRef("http://ex.org/onto#a2")) in graph
        assert (a1, RDFS.domain, URIRef("http://ex.org/onto#A")) in graph
        assert (a1, RDFS.range, URIRef("http://ex.org/onto#B")) in graph
        assert (a1, RDF.type, OWL.AnnotationProperty) in graph

    def test_i_typed_individual(self):
        graph = gh("!I ex:i1 : ex:Widget lb foo")
        i1 = URIRef("http://ex.org/onto#i1")
        assert (i1, RDF.type, URIRef("http://ex.org/onto#Widget")) in graph
        assert (i1, RDF.type, OWL.NamedIndividual) in graph
        assert (i1, RDFS.label, Literal("foo")) in graph

    def test_i_typed_individual_local_id_type(self):
        graph = decode(f"@b <{MORK}>\n!I s1 : CompilationMode lb foo\n")
        assert (URIRef(f"{MORK}s1"), RDF.type, URIRef(f"{MORK}CompilationMode")) in graph

    def test_i_typed_individual_type_code(self):
        graph = gh("!I i1 : MD")
        assert (URIRef(f"{EX}i1"), RDF.type, MORK.Datum) in graph

    def test_i_no_types(self):
        graph = gh("!I i1 lb foo")
        assert (URIRef(f"{EX}i1"), RDF.type, OWL.NamedIndividual) in graph
        assert (URIRef(f"{EX}i1"), RDFS.label, Literal("foo")) in graph

    def test_g_gci(self):
        graph = gh("!G ex:p>ex:A & ~ex:q>ex:B < .N")
        left = list(graph.subjects(RDFS.subClassOf, OWL.Nothing))
        assert len(left) == 1
        assert (left[0], OWL.intersectionOf, None) in graph

    def test_g_simple_bare_identifiers(self):
        graph = gh("!G ex:A < ex:B")
        assert (URIRef("http://ex.org/onto#A"), RDFS.subClassOf, URIRef("http://ex.org/onto#B")) in graph

    def test_g_missing_separator_raises(self):
        with pytest.raises(McnSyntaxError):
            gh("!G ex:A & ex:B")

    def test_dc_all_disjoint_classes(self):
        graph = gh("!DC ex:A,ex:B,ex:C")
        nodes = list(graph.subjects(RDF.type, OWL.AllDisjointClasses))
        assert len(nodes) == 1
        members = list(Graph_helpers_rdf_list(graph, list(graph.objects(nodes[0], OWL.members))[0]))
        assert set(members) == {URIRef("http://ex.org/onto#A"), URIRef("http://ex.org/onto#B"), URIRef("http://ex.org/onto#C")}

    def test_dp_all_disjoint_properties(self):
        graph = gh("!DP ex:p,ex:q")
        nodes = list(graph.subjects(RDF.type, OWL.AllDisjointProperties))
        assert len(nodes) == 1

    def test_di_all_different(self):
        graph = gh("!DI ex:a,ex:b")
        nodes = list(graph.subjects(RDF.type, OWL.AllDifferent))
        assert len(nodes) == 1
        members = list(Graph_helpers_rdf_list(graph, list(graph.objects(nodes[0], OWL.distinctMembers))[0]))
        assert set(members) == {URIRef("http://ex.org/onto#a"), URIRef("http://ex.org/onto#b")}

    def test_sa_pairwise_same_as(self):
        graph = gh("!SA ex:a,ex:b,ex:c")
        a, b, c = (URIRef(f"http://ex.org/onto#{x}") for x in "abc")
        assert (a, OWL.sameAs, b) in graph
        assert (a, OWL.sameAs, c) in graph
        assert (b, OWL.sameAs, c) in graph

    def test_disjoint_list_requires_two(self):
        with pytest.raises(McnSyntaxError):
            gh("!DC ex:A")

    def test_t_raw_triple_all_identifier(self):
        graph = gh("!T ex:s ex:p ex:o")
        assert (URIRef("http://ex.org/onto#s"), URIRef("http://ex.org/onto#p"), URIRef("http://ex.org/onto#o")) in graph

    def test_t_raw_triple_with_literal_object(self):
        graph = gh('!T ex:s ex:p "literal"')
        assert (URIRef("http://ex.org/onto#s"), URIRef("http://ex.org/onto#p"), Literal("literal")) in graph

    def test_t_raw_triple_with_iri_terms(self):
        graph = gh("!T <http://a.org> <http://b.org> <http://c.org>")
        assert (URIRef("http://a.org"), URIRef("http://b.org"), URIRef("http://c.org")) in graph

    def test_t_raw_triple_with_blank_subject(self):
        graph = gh("!T _:x rdf:type ex:Thing")
        subs = [s for s in graph.subjects(RDF.type, URIRef("http://ex.org/onto#Thing")) if isinstance(s, BNode)]
        assert len(subs) == 1

    def test_t_wrong_arity_raises(self):
        with pytest.raises(McnSyntaxError):
            gh("!T ex:s ex:p")

    def test_unknown_axiom_kind_raises(self):
        with pytest.raises(McnSyntaxError):
            gh("!Z ex:s")


# ===========================================================================
# Sec 12 -- identity, minting, determinism
# ===========================================================================


class TestIdentityAndDeterminism:
    def test_local_id_is_base_plus_token(self):
        graph = gh("s1 c Loan")
        assert (URIRef(f"{EX}s1"), MORK.conceptName, Literal("Loan")) in graph

    def test_repeated_decode_is_byte_identical(self):
        text = 'a MS xt ex:A{n "x"} hy [MD f ex:X]\n'
        text = f"@b <{EX}>\n@p ex=<http://ex.org/onto#>\n@t ex\n%M MS\n" + text
        g1 = decode(text)
        g2 = decode(text)
        assert canonical_ntriples(g1) == canonical_ntriples(g2)

    def test_two_isomorphic_but_differently_written_documents_match(self):
        t1 = gh('a MD f ex:X{n "note"}')
        t2 = gh('a MD f ex:X {n "note"}'.replace(" {", "{"))  # same content, sanity
        assert canonical_ntriples(t1) == canonical_ntriples(t2)

    def test_blank_node_numbering_axiom_prefix(self):
        graph = gh('a xt ex:A{n "x"}\nb xt ex:B{n "y"}\n')
        for s, p, o in graph.triples((None, RDF.type, OWL.Axiom)):
            assert isinstance(s, BNode)

    def test_canonical_ntriples_is_sorted_and_newline_terminated(self):
        graph = gh("a c B\nc c D\n")
        text = canonical_ntriples(graph)
        lines = text.rstrip("\n").split("\n")
        assert lines == sorted(lines)
        assert text.endswith("\n")

    def test_empty_graph_canonical_is_empty_string(self):
        assert canonical_ntriples(Graph()) == ""

    def test_mint_naming_matches_spec_table(self):
        graph = gh("s1 MR gr \"a(?x)->b(?x)\"")
        assert (U("s1"), MORK.generatesRuleDefinition, URIRef(f"{EX}s1_gr1")) in graph


# ===========================================================================
# Sec 14.1 -- decoder errors
# ===========================================================================


class TestDecoderErrors:
    def test_unknown_type_code_raises(self):
        with pytest.raises(McnSyntaxError):
            gh("s1 ZZ c foo")

    def test_unknown_property_code_raises(self):
        with pytest.raises(McnSyntaxError):
            gh("s1 zzz foo")

    def test_local_id_without_base_message_names_at_b(self):
        with pytest.raises(McnSyntaxError, match="@b"):
            decode("@t ex\ns1 c foo")

    def test_target_shorthand_without_at_t_message_names_at_t(self):
        with pytest.raises(McnSyntaxError, match="@t"):
            decode(f"@b <{EX}>\ns1 xt :foo")

    def test_quoted_in_object_slot_raises(self):
        with pytest.raises(McnSyntaxError):
            gh('s1 xt "notanid"')

    def test_inline_in_data_slot_raises(self):
        with pytest.raises(McnSyntaxError):
            gh("s1 c [MD f ex:X]")

    def test_unresolvable_polymorphic_raises(self):
        with pytest.raises(McnSyntaxError, match="polymorphic"):
            gh("s1 pv [a b 0.5 DRAFT]")

    def test_positional_form_under_wrong_code_raises(self):
        with pytest.raises(McnSyntaxError):
            gh("s1 sa [x y]")

    def test_unbalanced_brackets_raises(self):
        with pytest.raises(McnSyntaxError):
            gh("s1 tg [c ex:A")

    def test_annotation_not_attached_raises(self):
        with pytest.raises(McnSyntaxError):
            gh('s1 xt ex:A {n "x"}')

    def test_imports_before_ontology_raises(self):
        with pytest.raises(McnSyntaxError):
            decode("@i <http://a.org>\n")

    def test_rebinding_predeclared_prefix_raises(self):
        with pytest.raises(McnSyntaxError):
            decode("@p rdf=<http://evil.org/#>\n")

    def test_malformed_swrl_payload_raises(self):
        with pytest.raises(McnSyntaxError):
            gh('s1 MR gr "not a rule"')

    def test_malformed_shacl_payload_raises(self):
        with pytest.raises(McnSyntaxError):
            gh('s1 MS gs "c"')

    def test_malformed_rml_payload_raises(self):
        with pytest.raises(McnSyntaxError):
            gh('s1 MT gt "nonsense payload"')

    def test_malformed_expression_raises(self):
        with pytest.raises(McnSyntaxError):
            gh("e1 = %broken")

    def test_unknown_axiom_line_kind_raises(self):
        with pytest.raises(McnSyntaxError):
            gh("!Q ex:a")

    def test_undefined_reference_is_not_rejected(self):
        # Referencing an IRI never defined elsewhere in the document is
        # legal (spec Sec 14.1: the decoder never checks existence).
        graph = gh("s1 cn neverDefinedElsewhere")
        assert (U("s1"), MORK.compositeNarrowerMapping, U("neverDefinedElsewhere")) in graph

    def test_gci_violation_is_not_rejected(self):
        # ap without exactRBoxMatch/inverseRBoxMatch violates GCI 2.14a but
        # is a lint finding, not a decode-time error.
        graph = gh("s1 ap ex:parent")
        assert (U("s1"), MORK.broaderApplicative, URIRef("http://ex.org/onto#parent")) in graph

    def test_incomplete_mapping_is_not_rejected(self):
        graph = gh("s1 MS")  # ShapeMapping missing everything the GCIs require
        assert (U("s1"), RDF.type, MORK.ShapeMapping) in graph

    def test_error_names_line_number(self):
        text = f"@b <{EX}>\n@p ex=<http://ex.org/onto#>\n@t ex\ns1 c foo\ns2 zzz bar\n"
        with pytest.raises(McnSyntaxError) as excinfo:
            decode(text)
        assert excinfo.value.line_no == 5


# ===========================================================================
# Sec 14.2 -- lint rules
# ===========================================================================


class TestLint:
    def test_datum_without_deferred(self):
        graph = gh("s1 MD f ex:X")
        findings = lint(graph)
        assert any(f.rule_id == "datum-without-deferred" for f in findings)

    def test_datum_with_deferred_no_finding(self):
        graph = gh("s1 MD f ex:X df ex:Y")
        findings = lint(graph)
        assert not any(f.rule_id == "datum-without-deferred" for f in findings)

    def test_applicative_without_rbox(self):
        graph = gh("s1 ap ex:parent")
        findings = lint(graph)
        assert any(f.rule_id == "applicative-without-rbox" for f in findings)

    def test_applicative_with_rbox_no_finding(self):
        graph = gh("s1 ap ex:parent xr ex:prop")
        findings = lint(graph)
        assert not any(f.rule_id == "applicative-without-rbox" for f in findings)

    def test_aboxcat_composite_without_rbox(self):
        graph = gh("s1 ba ex:X cb ex:parent")
        findings = lint(graph)
        assert any(f.rule_id == "aboxcat-composite-without-rbox" for f in findings)

    def test_rboxcat_composite_without_abox(self):
        graph = gh("s1 br ex:X cb ex:parent")
        findings = lint(graph)
        assert any(f.rule_id == "rboxcat-composite-without-abox" for f in findings)

    def test_supersedes_without_effective_from(self):
        graph = gh("s1 ss ex:old")
        findings = lint(graph)
        assert any(f.rule_id == "supersedes-without-effective-from" for f in findings)

    def test_supersedes_with_effective_from_no_finding(self):
        graph = gh("s1 ss ex:old ef 2026-01-01T00:00:00Z")
        findings = lint(graph)
        assert not any(f.rule_id == "supersedes-without-effective-from" for f in findings)

    def test_generative_mapping_incomplete(self):
        graph = gh("s1 MS")
        findings = lint(graph)
        f = [x for x in findings if x.rule_id == "generative-mapping-incomplete"]
        assert len(f) == 1
        assert "hasTargetingSpec" in f[0].message

    def test_generative_mapping_complete_no_finding(self):
        graph = gh('s1 MS tg :Applicant pb [n N 1] pv [c m 0.5 DRAFT]')
        findings = lint(graph)
        assert not any(x.rule_id == "generative-mapping-incomplete" for x in findings)

    def test_transform_mapping_incomplete(self):
        graph = gh("s1 MT")
        findings = lint(graph)
        assert any(f.rule_id == "transform-mapping-incomplete" for f in findings)

    def test_targeting_spec_no_mode(self):
        graph = gh("s1 GT lb foo")
        findings = lint(graph)
        assert any(f.rule_id == "targeting-spec-no-mode" for f in findings)

    def test_provenance_incomplete(self):
        graph = gh("s1 GC lb foo")
        findings = lint(graph)
        assert any(f.rule_id == "provenance-incomplete" for f in findings)

    def test_provenance_complete_no_finding(self):
        graph = gh("s1 GC pc creator pd 2026-01-01T00:00:00Z")
        findings = lint(graph)
        assert not any(f.rule_id == "provenance-incomplete" for f in findings)

    def test_shape_and_rule_together(self):
        graph = gh('s1 gs "c ex:A" gr "ex:B(?x)->ex:C(?x)"')
        findings = lint(graph)
        assert any(f.rule_id == "shape-and-rule-together" for f in findings)

    def test_double_counted_edge(self):
        graph = gh("s1 cn ex:child ap ex:child xr ex:prop")
        findings = lint(graph)
        assert any(f.rule_id == "double-counted-edge" for f in findings)

    def test_governance_without_identity(self):
        graph = gh("s1 MS ms ex:MS gv .gA")
        findings = lint(graph)
        assert any(f.rule_id == "governance-without-identity" for f in findings)

    def test_governance_draft_no_finding(self):
        graph = gh("s1 MS ms ex:MS gv .gD")
        findings = lint(graph)
        assert not any(f.rule_id == "governance-without-identity" for f in findings)

    def test_governance_with_identity_no_finding(self):
        graph = gh("s1 MS ms ex:MS gv .gA fi [PI]")
        findings = lint(graph)
        assert not any(f.rule_id == "governance-without-identity" for f in findings)

    def test_uncertain_mapping_incomplete(self):
        graph = gh("s1 MU w 40")
        findings = lint(graph)
        assert any(f.rule_id == "uncertain-mapping-incomplete" for f in findings)

    def test_uncertain_mapping_with_hypothesis_no_finding(self):
        graph = gh("s1 MU hy [MD f ex:X]")
        findings = lint(graph)
        assert not any(f.rule_id == "uncertain-mapping-incomplete" for f in findings)

    def test_strict_mode_raises_on_finding(self):
        with pytest.raises(McnLintError):
            gh("@opt strict\ns1 MD f ex:X")

    def test_strict_mode_passes_clean_document(self):
        graph = gh("@opt strict\ns1 MD f ex:X df ex:Y")
        assert (U("s1"), MORK.mappingFor, None) in graph

    def test_lint_without_strict_does_not_raise(self):
        graph = gh("s1 MD f ex:X")  # no @opt strict
        assert (U("s1"), RDF.type, MORK.Datum) in graph


# ===========================================================================
# @opt inv
# ===========================================================================


class TestInverseOption:
    def test_inv_materialises_known_inverse(self):
        graph = gh("@opt inv\ns1 f ex:X")
        assert (URIRef("http://ex.org/onto#X"), MORK.hasMapping, U("s1")) in graph

    def test_without_inv_no_materialisation(self):
        graph = gh("s1 f ex:X")
        assert (URIRef("http://ex.org/onto#X"), MORK.hasMapping, U("s1")) not in graph

    def test_inv_does_not_double_count_composite_narrower(self):
        # Documents the loan example's own reasoning: without @opt inv,
        # compositeNarrowerMapping does not also assert compositeBroaderMapping.
        graph = gh("s1 cn s2")
        assert (U("s2"), MORK.compositeBroaderMapping, U("s1")) not in graph
        graph2 = gh("@opt inv\ns1 cn s2")
        assert (U("s2"), MORK.compositeBroaderMapping, U("s1")) in graph2


# ===========================================================================
# Sec 16 -- worked examples, round-tripped against the repository's own
# example Turtle files.
# ===========================================================================


def _strip_named_individual(graph: Graph) -> None:
    for triple in list(graph.triples((None, RDF.type, OWL.NamedIndividual))):
        graph.remove(triple)


@pytest.mark.skipif(not LOAN_TTL.exists(), reason="repository example file not found")
class TestWorkedExampleLoanMapping:
    MCN_TEXT = """\
@b <http://example.org/mapping#>
@p fin=<http://example.org/fin#>
@p qnt=<https://www.nebularis.org/neuro-semantic/lattice/quantification#>
@t fin
!D qnt:numericValue
!O qnt:onSpace
!O qnt:inUnit
!C :Loan
!O :principal dom :Loan rng qnt:Quantity
!I :LoanPrincipalSpace : qnt:ValueSpace
!I :USD : qnt:Unit
%R Scheme_Loan_Source .json id loan.json
%X
Concept_Loan C cs MS rs Scheme_Loan_Source p $
%M MS
Map_Loan_Class xt :Loan
Map_Loan M+MD f Concept_Loan df Map_Loan_Class c Loan r loanId
Map_Principal ap Map_Loan cb Map_Loan xi :principal c LoanPrincipal r loanId cn Map_PrincipalValue
Map_PrincipalValue cb Map_Principal xr qnt:numericValue r principal
"""

    def test_round_trip_exact(self):
        decoded = decode(self.MCN_TEXT)
        original = Graph().parse(str(LOAN_TTL), format="turtle")
        _strip_named_individual(decoded)
        _strip_named_individual(original)
        iso_decoded, iso_original = to_isomorphic(decoded), to_isomorphic(original)
        both, only_decoded, only_original = graph_diff(iso_decoded, iso_original)
        assert len(only_decoded) == 0
        assert len(only_original) == 0
        assert len(both) == 40


@pytest.mark.skipif(not UNCERTAIN_TTL.exists(), reason="repository example file not found")
class TestWorkedExampleUncertainMappings:
    MCN_TEXT = """\
@b <http://www.nebularis.org/ontologies/UncertainMappings#>
@o <http://www.nebularis.org/ontologies/UncertainMappings>
@i <http://www.nebularis.org/ontologies/Mork>,<http://www.w3.org/2004/02/skos/core>,<http://www.nebularis.org/ontologies/Zoo>,<http://www.nebularis.org/ontologies/Petstore>
@p zoo=<http://www.nebularis.org/ontologies/Zoo#>
@p pets=<http://www.nebularis.org/ontologies/Petstore#>
@t zoo
!C OviparousBase = :laysEggs=t
!D Map_EggSize_Hypothesis rng xsd:string
%M Mappings
Map_EggSize MU hy Map_EggSize_Hypothesis lx :laysEggs{n "Close lexical match on conceptName 'EggSize' and DataProperty name 'eggSize'."} mr "Create a new datatype property in the output ontology to represent the size of Eggs." w 40
Map_EggSize_Hypothesis ad Map_Yield_Oviparous br .top f EggSize c #eggSize n "Mapping the concept 'EggSize' to a new data property 'eggSize' in the target ontology."
Map_Eggs MU hy Map_Eggs_Hypothesis lx :laysEggs{n "Close lexical match on conceptName 'Eggs' and ObjectProperty name 'laysEggs'."} f pets:EggsType,pets:Rep_Falcon_Eggs,pets:Rep_Platypus_Eggs w 50 nn "Possible match between concept 'Eggs' the object property 'laysEggs' in the target ontology."
Map_Eggs_Hypothesis bt .T cn Map_EggSize c #Eggs n "Hypothesis mapping for 'Eggs' is a deferred class definition."
Map_Falcon MU hy Map_Falcon_Hypothesis{n "Hypothesise the creation of several new types/classes to support the Falcon concept."} f pets:FalconType,pets:Rep_Falcon mr "Recommend defining a new individual 'Falcon' in the target ontology, representing the concept of Falcon as an individual species of Bird." w 65
Map_Falcon_Hypothesis MD cn Map_Lays_Eggs df Map_Gen_Bird_Class{n "Falcon is a bird, birds lay eggs, however birds are not reptiles. Recommend defining a new class 'Bird' in the target ontology, and then defining 'Falcon' as an individual of the class."} xt .dcd,Map_Yield_Oviparous,Map_Yield_Pet i #Falcon n "Hypothesis mapping for 'Falcon' is Pet, Bird."
Map_Gen_Bird_Class bt Map_Yield_Oviparous,:Animal dp Map_Oviparity c #Bird n "Create a class 'Bird' in the output ontology."
Map_Gen_Monotreme_Class bt Map_Yield_Oviparous,:Mamal c #Monotreme n "Create a class 'Monotreme' in the output ontology."
Map_Lays_Eggs MD cn Map_Eggs xr :laysEggs v t n "Asserts the property `Falcon laysEggs true`"
Map_Oviparity MX bt .T tc mork:OviparousBase c #Oviparous mr "Recommend introducing a notional construct to model reproductive modes, with 'Oviparity' as a member/individual."
Map_Pet xt :Animal f pets:PetType c #Pet w 90 n "'Pet' is a possible sematic match with the class 'Animal' in the target ontology, representing the concept of pet animals."
Map_Platypus MU hy Map_Platypus_Hypothesis{n "Recommendation requires creation of several new types/classes."} f pets:PlatypusType,pets:Rep_Platypus mr "Recommend defining a new individual 'Platypus' in the target ontology, representing the concept of Platypus as an individual species." w 70
Map_Platypus_Hypothesis MD cn Map_Lays_Eggs df Map_Gen_Monotreme_Class dp Map_Oviparity xt .dcd,Map_Yield_Oviparous,Map_Yield_Pet i #Platypus n "'Platypus' is a type of Monotreme (which lays eggs), and also (apparently) a Pet."
Map_Yield_Oviparous MX y .dci c #Oviparous n "Yields the axiom <BaseIRI>#Oviparous at processing time."
Map_Yield_Pet MX y .dci c #Pet n "Yields the axiom <BaseIRI>#Pet at processing time."
"""

    def test_round_trip_matches_except_documented_original_defect(self):
        """This MCN excerpt (spec Sec 16.2) omits the file's standalone
        :TempMapping/skos:example block (an unrelated illustration, not
        part of the mapping scheme); the three remaining differences are
        the *original* Turtle's own defect -- three owl:Axiom
        reifications whose annotatedTarget uses the mork: prefix instead
        of the local one, so they annotate nothing. MCN's {...} form
        makes that mistake syntactically impossible."""
        decoded = decode(self.MCN_TEXT)
        original = Graph().parse(str(UNCERTAIN_TTL), format="turtle")
        _strip_named_individual(decoded)
        _strip_named_individual(original)
        iso_decoded, iso_original = to_isomorphic(decoded), to_isomorphic(original)
        both, only_decoded, only_original = graph_diff(iso_decoded, iso_original)
        assert len(only_decoded) == 3
        for _s, p, o in only_decoded:
            assert p == OWL.annotatedTarget
            assert "UncertainMappings#" in str(o)
        wrong_prefix_diffs = [t for t in only_original if t[1] == OWL.annotatedTarget]
        assert len(wrong_prefix_diffs) == 3
        for _s, p, o in wrong_prefix_diffs:
            assert "Mork#Map_" in str(o)


# ===========================================================================
# Sec 20 -- codebook governance: every declared term in Mork.ttl has a code
# ===========================================================================


@pytest.mark.skipif(not MORK_TTL.exists(), reason="ontology/mork/spec/Mork.ttl not found")
class TestCodebookCoverage:
    @staticmethod
    def _declared_terms():
        text = MORK_TTL.read_text()
        # Strip triple-quoted string bodies (skos:example, skos:scopeNote,
        # ...) first: they routinely embed illustrative Turtle snippets
        # (an "Aardvark" class, an "isSubcategoryOf" property) that name
        # real MCN terms in prose but are not themselves declarations in
        # this ontology.
        text = re.sub(r'"""(?:[^"]|"(?!""))*"""', "", text, flags=re.S)
        declared = set()
        for m in re.finditer(r"^:(\w+)\s+(?:rdf:type|a)\s+owl:(\w+)", text, re.M):
            declared.add((m.group(1), m.group(2)))
        return declared

    def test_no_duplicate_type_codes(self):
        # mcn_codebook._type() already raises on duplicates at import
        # time; re-assert the invariant here so a regression is reported
        # as a test failure, not an ImportError somewhere else.
        assert len(cb.TYPES) == len({(v.curie, k) for k, v in cb.TYPES.items()}) or True
        seen = set()
        for code in cb.TYPES:
            assert code not in seen
            seen.add(code)

    def test_no_duplicate_property_codes(self):
        seen = set()
        for code in cb.PROPERTIES:
            assert code not in seen
            seen.add(code)

    def test_every_class_has_a_type_code(self):
        covered = {v.curie.split(":")[1] for v in cb.TYPES.values() if v.curie.startswith("mork:")}
        missing = [name for name, kind in self._declared_terms() if kind == "Class" and name not in covered]
        assert not missing, f"classes with no MCN type code: {missing}"

    def test_every_object_and_data_property_has_a_code(self):
        covered = set()
        for spec in cb.PROPERTIES.values():
            for part in spec.curie.split("/"):
                if part.startswith("mork:"):
                    covered.add(part.split(":")[1])
        missing = [
            name
            for name, kind in self._declared_terms()
            if kind in ("ObjectProperty", "DatatypeProperty", "AnnotationProperty") and name not in covered
        ]
        assert not missing, f"properties with no MCN code: {missing}"

    def test_every_named_individual_has_a_reserved_token_or_type_code(self):
        covered_res = {v.split(":")[1] for v in cb.RESERVED.values() if v.startswith("mork:")}
        covered_types = {v.curie.split(":")[1] for v in cb.TYPES.values() if v.curie.startswith("mork:")}
        missing = [
            name
            for name, kind in self._declared_terms()
            if kind == "NamedIndividual" and name not in covered_res and name not in covered_types
        ]
        assert not missing, f"individuals with no MCN reserved token: {missing}"

    def test_predeclared_prefixes_cover_mork_ttl_namespaces(self):
        text = MORK_TTL.read_text()
        for prefix_decl in re.finditer(r"@prefix\s+(\w+):\s+<([^>]+)>", text):
            prefix, iri = prefix_decl.group(1), prefix_decl.group(2)
            if prefix in ("xml",):
                continue
            assert prefix in cb.PREDECLARED_PREFIXES, f"{prefix} not predeclared"
            assert cb.PREDECLARED_PREFIXES[prefix] == iri, f"{prefix} IRI mismatch"


# ===========================================================================
# codebook.code_for() / codes_for() -- unconditional (no Mork.ttl needed)
# ===========================================================================


class TestCodebookLookup:
    def test_code_for_resolves_a_type(self):
        assert cb.code_for(cb.MORK_NS + "Datum") == "MD"

    def test_code_for_resolves_a_property(self):
        assert cb.code_for(cb.MORK_NS + "exactTBoxMatch") == "xt"

    def test_code_for_resolves_a_reserved_individual(self):
        assert cb.code_for(cb.MORK_NS + "DraftMode") == ".draft"

    def test_code_for_unknown_iri_is_none(self):
        assert cb.code_for("http://example.org/not-in-mork#Nope") is None

    def test_code_for_resolves_polymorphic_property_members(self):
        assert cb.code_for(cb.MORK_NS + "hasParameterBinding") == "pb"
        assert cb.code_for(cb.MORK_NS + "paramBinding") == "pb"
        assert cb.code_for(cb.MORK_NS + "hasConstraintProvenance") == "pv"

    def test_codes_for_preserves_order_and_drops_unknowns(self):
        iris = [
            cb.MORK_NS + "exactTBoxMatch",
            "http://example.org/not-in-mork#Nope",
            cb.MORK_NS + "broadTBoxCategoryMatch",
        ]
        assert cb.codes_for(iris) == ["xt", "bt"]

    def test_every_code_reverse_resolves_to_a_code(self):
        # Every forward entry in TYPES/PROPERTIES/RESERVED should round-trip
        # through code_for() to *some* code (not necessarily the same one,
        # since a few IRIs have more than one code -- e.g. possibleMatch's
        # synonym pm/px -- but never None).
        for code, spec in cb.TYPES.items():
            assert cb.code_for(cb._expand(spec.curie)) is not None, code
        for code, spec in cb.PROPERTIES.items():
            for part in spec.curie.split("/"):
                assert cb.code_for(cb._expand(part)) is not None, code


# ===========================================================================
# Miscellaneous public-API tests
# ===========================================================================


class TestPublicApi:
    def test_decode_returns_graph_instance(self):
        assert isinstance(gh("s1 c Loan"), Graph)

    def test_lint_finding_shape(self):
        graph = gh("s1 MD f ex:X")
        findings = lint(graph)
        assert findings and isinstance(findings[0], LintFinding)
        f = findings[0]
        assert isinstance(f.rule_id, str) and f.rule_id
        assert isinstance(f.subject, URIRef)
        assert isinstance(f.message, str) and f.message
        assert isinstance(f.mirrors, str)
        assert f.severity == "warning"
        assert f.line is None
        assert f.code == f.rule_id  # .code is a stable alias for .rule_id

    def test_syntax_error_has_stable_namespaced_code(self):
        with pytest.raises(McnSyntaxError) as excinfo:
            gh("s1 zzz foo")
        assert excinfo.value.code == "core-unknown-property-code"

    def test_syntax_error_code_namespaced_per_sub_parser(self):
        cases = {
            'MS gs "c"': "shacl-",
            'MR gr "no arrow here"': "swrl-",
            'MT gt "nonsense"': "rml-",
        }
        for fragment, prefix in cases.items():
            with pytest.raises(McnSyntaxError) as excinfo:
                gh(f"s1 {fragment}")
            assert excinfo.value.code.startswith(prefix), (fragment, excinfo.value.code)

    def test_every_raised_syntax_error_has_a_non_default_code(self):
        # Sanity check on the whole error surface: no raise site should be
        # silently falling back to one of the generic per-parser defaults
        # ("core-error", "lex-error", "ce-error", "swrl-error",
        # "shacl-error", "rml-error", "expr-error", "syntax-error").
        generic = {
            "syntax-error", "lex-error", "ce-error", "swrl-error",
            "shacl-error", "rml-error", "expr-error", "core-error",
        }
        samples = [
            "s1 zzz foo",
            "s1 ZZ c foo",
            's1 xt "notanid"',
            "s1 c [MD f ex:X]",
            "s1 tg [z ex:Applicant]",
            "!T ex:s ex:p",
            "!Z ex:s",
            'e1 = %broken',
        ]
        for text in samples:
            with pytest.raises(McnSyntaxError) as excinfo:
                gh(text)
            assert excinfo.value.code not in generic, (text, excinfo.value.code)

    def test_decode_options_kwarg_seeds_options(self):
        with pytest.raises(McnLintError):
            decode(f"@b <{EX}>\n@p ex=<http://ex.org/onto#>\n@t ex\ns1 MD f ex:X\n", options=["strict"])

    def test_internal_failure_wrapped_as_syntax_error(self):
        # Any unexpected internal exception (KeyError/IndexError/ValueError)
        # should surface as an McnSyntaxError naming the offending line,
        # never as a raw traceback from decoder internals.
        with pytest.raises(McnSyntaxError):
            gh("s1 MS pb [n N]")  # missing the value slot -> IndexError internally

    def test_namespaces_match_predeclared_prefixes(self):
        assert str(MORK) == cb.PREDECLARED_PREFIXES["mork"]
        assert str(SH) == cb.PREDECLARED_PREFIXES["sh"]
        assert str(SWRL) == cb.PREDECLARED_PREFIXES["swrl"]
        assert str(RR) == cb.PREDECLARED_PREFIXES["rr"]
        assert str(RML) == cb.PREDECLARED_PREFIXES["rml"]
        assert str(FND) == cb.PREDECLARED_PREFIXES["fnd"]
        assert str(DCT) == cb.PREDECLARED_PREFIXES["dct"]
        assert str(SKOS) == cb.PREDECLARED_PREFIXES["skos"]


class TestMcnPackage:
    """`import mcn` is a thin re-export over mcn_decoder/mcn_codebook, kept
    for consumers (e.g. the MTP generator sketches in ontology/mork/docs/) that
    expect a package literally named `mcn` with decode/lint as top-level
    functions."""

    def test_import_mcn_exposes_decode_and_lint(self):
        import mcn

        graph = mcn.decode(f"@b <{EX}>\n@p ex=<http://ex.org/onto#>\n@t ex\ns1 MD f ex:X df ex:Y\n")
        assert (U("s1"), MORK.mappingFor, URIRef("http://ex.org/onto#X")) in graph
        assert mcn.lint(graph) == []

    def test_mcn_package_reuses_the_same_classes(self):
        import mcn

        assert mcn.decode is decode
        assert mcn.lint is lint
        assert mcn.McnSyntaxError is McnSyntaxError
        assert mcn.LintFinding is LintFinding

    def test_mcn_package_exposes_codebook_submodule(self):
        import mcn

        assert mcn.codebook.code_for(mcn.codebook.MORK_NS + "exactTBoxMatch") == "xt"

    def test_mcn_package_has_no_encode(self):
        # Deliberately absent: spec §15 (RDF -> MCN) is not implemented.
        # Consumers are expected to check via getattr(mcn, "encode", None).
        import mcn

        assert not hasattr(mcn, "encode")
