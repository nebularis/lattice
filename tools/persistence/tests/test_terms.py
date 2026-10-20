# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The injection corpus (ADR-A79 point 5, sketch §5.3): a release gate for
the ``instantiate`` stage, not an aspiration. Every adversarial value is
fed through the encoders and, where it is accepted, through every builder
(H2.9-Q3) and the slot filling, and the rendered output is parsed
by an independent SPARQL parser to assert it contains exactly the one
intended operation. The library's own slot filling is run over the same
kind of corpus in packages/persistence/python/tests/test_slot_injection.py.

A corpus entry that produces a rejection (``SparqlTermError``) is a PASS:
the encoder correctly refused a hostile value. A corpus entry that is
accepted and renders into a SECOND, unintended, syntactically valid
operation is the failure this whole module exists to prevent.
"""

from __future__ import annotations

import pytest
from rdflib.plugins.sparql import prepareQuery, prepareUpdate
from rdflib.plugins.sparql.algebra import translateUpdate
from rdflib.plugins.sparql.parser import parseUpdate

from rdflib import URIRef

from builder_goldens import CANONICAL_CONTEXT
from persistence.builders import BUILDERS, build, build_recording
from persistence.ir_render import fill_slots, render
from persistence.terms import Integer, Iri, Literal, SparqlTermError, Var
from request_slots import fill_request_slots

# Adversarial IRI values: unbalanced braces, embedded SPARQL keywords,
# quote and backslash sequences, bidirectional-override and zero-width
# Unicode, and a classic "close the term and inject a new operation" probe.
ADVERSARIAL_IRIS = [
    'urn:g:orders> } ; DROP GRAPH <urn:g:keys> ; ASK { <urn:g:x',
    "urn:g:orders/{ INSERT DATA { <urn:x> <urn:y> <urn:z> } }",
    "urn:g:orders/\\u0000",
    "urn:g:orders/​",  # zero-width space
    "urn:g:orders/‮",  # right-to-left override
    "urn:g:orders/⁦",  # left-to-right isolate
    'urn:g:orders/"; DELETE WHERE { ?s ?p ?o } #',
    "urn:g:orders/<script>",
    "urn:g:orders/\n\rDELETE",
    "urn:g:orders/|pipe",
    "urn:g:orders/`backtick`",
    "",  # empty
]

# Adversarial literal values: these are ESCAPED, not rejected, so the
# assertion is that the escaping keeps the surrounding query well-formed.
ADVERSARIAL_LITERALS = [
    'value" ; DROP GRAPH <urn:g:keys> ; INSERT DATA { <urn:x> <urn:y> "',
    "value\\\" } } DELETE { ?s ?p ?o",
    "line1\nline2\rline3\ttabbed",
    "back\\slash",
    "quote\"inside",
    "unicode​zero‮width",
    "",
]


class TestIriEncoder:
    @pytest.mark.parametrize("value", ADVERSARIAL_IRIS)
    def test_rejects_or_stays_safe(self, value):
        """Every adversarial IRI either raises SparqlTermError (a pass, the
        encoder refused it) or -- it never should, this is the assertion --
        successfully encodes into something that still parses as a single
        term when embedded."""
        try:
            encoded = Iri.encode(value)
        except SparqlTermError:
            return  # rejection is a pass
        # If it wasn't rejected, using it in a template must never produce
        # more than the one intended triple/operation.
        text = f"GRAPH {encoded} {{ ?s ?p ?o }}"
        # a bare GroupGraphPattern isn't a full query; wrap it minimally
        query = f"SELECT * WHERE {{ {text} }}"
        parsed = prepareQuery(query)
        assert parsed is not None

    def test_accepts_ordinary_iris(self):
        for value in [
            "urn:g:orders/1",
            "https://example.org/lending#Order",
            "urn:g:meta/17",
            "urn:txn:01J8Q5B2D8N4Y7W1Z3M6K9R2V5",
        ]:
            encoded = Iri.encode(value)
            assert encoded == f"<{value}>"


class TestLiteralEncoder:
    @pytest.mark.parametrize("value", ADVERSARIAL_LITERALS)
    def test_escapes_safely(self, value):
        encoded = Literal.encode(value)
        # embedding the escaped literal in a trivial ASK must parse as
        # exactly one operation, never two
        query = f"ASK {{ BIND({encoded} AS ?x) }}"
        parsed = prepareQuery(query)
        assert parsed is not None

    def test_rejects_datatype_and_lang_together(self):
        with pytest.raises(SparqlTermError):
            Literal.encode("x", datatype="http://example.org/t", lang="en")

    def test_rejects_invalid_lang_tag(self):
        with pytest.raises(SparqlTermError):
            Literal.encode("x", lang="not a lang tag!!")

    def test_ordinary_literal(self):
        assert Literal.encode("hello") == '"hello"'
        assert Literal.encode("42", datatype="http://www.w3.org/2001/XMLSchema#long") == (
            '"42"^^<http://www.w3.org/2001/XMLSchema#long>'
        )


class TestVarEncoder:
    @pytest.mark.parametrize(
        "name",
        ["1leading-digit", "has space", "has-hyphen", "", "has;semicolon", "has}brace"],
    )
    def test_rejects_invalid_names(self, name):
        with pytest.raises(SparqlTermError):
            Var.encode(name)

    def test_accepts_valid_names(self):
        assert Var.encode("root") == "?root"
        assert Var.encode("_underscore") == "?_underscore"


class TestIntegerEncoder:
    def test_rejects_non_int(self):
        with pytest.raises(SparqlTermError):
            Integer.encode("not an int")  # type: ignore[arg-type]
        with pytest.raises(SparqlTermError):
            Integer.encode(True)  # bool is not accepted even though it is an int subclass

    def test_accepts_int(self):
        assert Integer.encode(47) == "47"
        assert Integer.encode(0) == "0"


def _operations(text: str) -> int | None:
    """How many operations the text parses as, or None when it does not parse. A query is one."""
    try:
        return len(translateUpdate(parseUpdate(text)).algebra)
    except Exception:
        try:
            prepareQuery(text)
            return 1
        except Exception:
            return None


def _built(key: str, context: dict) -> str:
    return fill_request_slots(render(build(key, context)))


class TestBuilderInjectionCorpus:
    """The full corpus, run against every builder with the canonical context, substituting one adversarial value at a time into each
    binding the builder reads (H2.9-Q3). A value the encoder refuses is a pass. One it accepts must leave the text parsing as exactly the
    operations the unmodified builder gives, or not parse at all. What must never happen is a successful parse with more operations."""

    @pytest.mark.parametrize("key", sorted(BUILDERS))
    def test_the_unmodified_builder_is_one_operation(self, key):
        assert _operations(_built(key, dict(CANONICAL_CONTEXT))) == 1

    @pytest.mark.parametrize("key", sorted(BUILDERS))
    @pytest.mark.parametrize("adversarial", ADVERSARIAL_IRIS)
    def test_builder_survives_adversarial_iri_in_every_iri_binding(self, key, adversarial):
        _, read = build_recording(key, dict(CANONICAL_CONTEXT))
        for name in sorted(read):
            if not isinstance(CANONICAL_CONTEXT[name], Iri):
                continue
            try:
                encoded = Iri.encode(adversarial)
            except SparqlTermError:
                continue  # rejection is a pass, nothing to render
            found = _operations(_built(key, {**CANONICAL_CONTEXT, name: encoded}))
            assert found in (None, 1), (key, name, found)

    @pytest.mark.parametrize("key", sorted(BUILDERS))
    @pytest.mark.parametrize("adversarial", ADVERSARIAL_LITERALS)
    def test_builder_survives_adversarial_literal_in_every_literal_binding(self, key, adversarial):
        _, read = build_recording(key, dict(CANONICAL_CONTEXT))
        for name in sorted(read):
            if not isinstance(CANONICAL_CONTEXT[name], Literal):
                continue
            found = _operations(_built(key, {**CANONICAL_CONTEXT, name: Literal.encode(adversarial)}))
            assert found in (None, 1), (key, name, found)

    @pytest.mark.parametrize("adversarial", ADVERSARIAL_IRIS + ADVERSARIAL_LITERALS)
    def test_a_value_that_holds_a_slot_marker_is_not_filled_again(self, adversarial):
        """Slot filling is one pass (H2.9-Q1). A filled value that spells another slot's marker stays as text."""
        marker = "{{{eventRows}}}"
        text = fill_slots("INSERT DATA { GRAPH <urn:g> { {{{payloadTriples}}} } } # {{{eventRows}}}", {"payloadTriples": marker + adversarial, "eventRows": "ROWS"})
        assert text.count(marker) == 1 and text.endswith("# ROWS")


def test_h2_9_t5_an_unfilled_slot_is_left_as_a_marker_and_the_query_does_not_parse():
    text = render(build("cas-replace-named-graph", dict(CANONICAL_CONTEXT)))
    assert "{{{payloadTriples}}}" in text and _operations(text) is None
    assert _operations(fill_request_slots(text)) == 1


# ---- H2.1: a backslash before u or U ----------------------------------------------------------------------
# SPARQL processes \uXXXX escapes over the whole query text, so a literal value holding a backslash and
# then "u" and hex digits must not put that sequence in the query text (found by the H2.1 property test).


@pytest.mark.parametrize("value", [
    "\\u0041", "a\\U00000041", "\\\\u0041", "\\ud83d", "\\u00zz", "\\uabcdefgh12", "ends with a backslash \\", "uU",
])
def test_h2_1_a_literal_with_a_backslash_before_u_round_trips(value):
    from rdflib import Dataset, Literal as RdfLiteral

    dataset = Dataset()
    dataset.update(f"INSERT DATA {{ GRAPH <urn:g> {{ <urn:s> <urn:p> {Literal.encode(value)} }} }}")
    assert [o for _, _, o, _ in dataset.quads((None, None, None, URIRef("urn:g")))] == [RdfLiteral(value)]


def test_h2_1_no_encoded_literal_contains_a_unicode_escape_the_value_did_not_hold():
    assert "\\u0041" not in str(Literal.encode("\\u0041"))
    assert str(Literal.encode("plain")) == '"plain"'
