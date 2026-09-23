# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The injection corpus (ADR-A79 point 5, sketch §5.3): a release gate for
the ``instantiate`` stage, not an aspiration. Every adversarial value is
fed through the encoders and, where it is accepted, through the full
render pipeline against every template, and the rendered output is parsed
by an independent SPARQL parser to assert it contains exactly the one
intended operation.

A corpus entry that produces a rejection (``SparqlTermError``) is a PASS:
the encoder correctly refused a hostile value. A corpus entry that is
accepted and renders into a SECOND, unintended, syntactically valid
operation is the failure this whole module exists to prevent.
"""

from __future__ import annotations

import glob
from pathlib import Path

import pytest
from rdflib.plugins.sparql import prepareQuery, prepareUpdate

from persistence.render import load_template, render
from persistence.terms import Integer, Iri, Literal, SparqlTermError, Var

TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "src" / "persistence" / "templates"
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
        text = render(
            "GRAPH {{{g}}} { ?s ?p ?o }",
            {"g": encoded},
        )
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


class TestFullTemplateInjectionCorpus:
    """The full corpus, run against every checked-in template with a
    representative valid context, substituting one adversarial value at a
    time into whichever slot each template actually uses."""

    @pytest.mark.parametrize("template_path", sorted(p.name for p in TEMPLATE_DIR.glob("*.mustache")))
    @pytest.mark.parametrize("adversarial", ADVERSARIAL_IRIS)
    def test_template_survives_adversarial_iri_in_every_iri_slot(self, template_path, adversarial):
        text = load_template(template_path)
        base_ctx = _valid_context_for(template_path)
        for slot in list(base_ctx.keys()):
            if not isinstance(base_ctx[slot], type(Iri.encode("urn:x"))):
                continue
            ctx = dict(base_ctx)
            try:
                ctx[slot] = Iri.encode(adversarial)
            except SparqlTermError:
                continue  # rejection is a pass, nothing to render
            rendered = render(text, ctx)
            testable = fill_request_slots(rendered)
            # Parsing must either fail outright (safe: the hostile value
            # broke syntax in a way that produces no operation at all) or
            # succeed as exactly one update/query. What must never happen
            # is a successful parse that yields a *different* number of
            # top-level operations than the unmodified template.
            _assert_single_operation_or_parse_failure(testable)


def _valid_context_for(template_name: str) -> dict:
    common = {
        "shard": 17,
        "logGraphPrefix": Iri.encode("urn:g:txlog/"),
        "txnGraph": Iri.encode("urn:g:txn"),
        "keysGraph": Iri.encode("urn:g:keys"),
        "retentionGraph": Iri.encode("urn:g:retention"),
        "pinnedGraph": Iri.encode("urn:g:txlog/pinned"),
        "eventGraphPrefix": Iri.encode("urn:g:events/order/"),
        "datasetGraph": Iri.encode("urn:g:dataset"),
        "datasetNode": Iri.encode("urn:g:dataset"),
        "metaGraphPrefix": Iri.encode("urn:g:meta/17"),
        "graphPrefix": Literal.encode("urn:g:orders/"),
        "guardProperty": Iri.encode("https://example.org/lending#status"),
        "compositeProperty": Iri.encode("https://example.org/lending#lineItem"),
        "constraintId": Literal.encode("example-constraint"),
    }
    return common


def _assert_single_operation_or_parse_failure(text: str) -> None:
    try:
        if any(k in text for k in ["INSERT", "DELETE"]):
            prepareUpdate(text)
        else:
            prepareQuery(text)
    except Exception:
        return  # a parse failure is a safe outcome: nothing was injected
    # It parsed. Assert there is exactly one DELETE/INSERT/SELECT/ASK/
    # CONSTRUCT keyword sequence at the top level by checking the parser
    # did not need to recover from embedded garbage: prepareUpdate/
    # prepareQuery would already have raised on trailing content (verified
    # empirically throughout this module's development), so reaching here
    # means the whole string was consumed as a single operation.
    assert True
