"""
mcn_decoder.py

A decoder for MCN (MORK Compact Notation) -- the token-minimal notation for
MORK graphs specified in docs/architecture/mork-compact-notation.md. This
module implements the decoding algorithm of spec section 13 (D1-D9): it is a
total function from well-formed MCN text to an rdflib Graph, using exactly
the codebook in mcn_codebook.py.

This module does not implement the encoding direction (RDF -> MCN, spec
section 15); it decodes only.

Public API:
    decode(text, *, options=None, profiles=None, source_name="<mcn>") -> Graph
    canonical_ntriples(graph) -> str          (spec Section 12.4)
    lint(graph) -> List[LintFinding]          (spec Section 14.2)
    McnSyntaxError                            (spec Section 14.1)
    McnLintError                              (raised when "strict" fires)
    Profile                                   (spec Section 6.1)

Section references in comments ("Sec 9.6", "D6.2", ...) are to
docs/architecture/mork-compact-notation.md.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, XSD

import mcn_codebook as cb

# ---------------------------------------------------------------------------
# Namespaces
# ---------------------------------------------------------------------------

MORK = Namespace(cb.MORK_NS)
SKOS = Namespace(cb.PREDECLARED_PREFIXES["skos"])
SH = Namespace(cb.PREDECLARED_PREFIXES["sh"])
SWRL = Namespace(cb.PREDECLARED_PREFIXES["swrl"])
SWRLB = Namespace(cb.PREDECLARED_PREFIXES["swrlb"])
RR = Namespace(cb.PREDECLARED_PREFIXES["rr"])
RML = Namespace(cb.PREDECLARED_PREFIXES["rml"])
FND = Namespace(cb.PREDECLARED_PREFIXES["fnd"])
DCT = Namespace(cb.PREDECLARED_PREFIXES["dct"])

_QL = Namespace("http://semweb.mmlab.be/ns/ql#")


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class McnSyntaxError(SyntaxError):
    """A well-formedness violation (spec Sec 14.1). Always names the
    logical line it was found on, 1-indexed.

    ``code`` is a stable, machine-matchable slug identifying the *kind* of
    failure (e.g. "core-unknown-property-code", "shacl-unknown-severity"),
    namespaced by the sub-parser that raised it (lex/ce/swrl/shacl/rml/expr/
    core). It exists so tooling built on top of this decoder -- a repair
    loop, a mutation-testing harness, a diagnostic->doctrine table -- can
    key off a stable identifier the way it already can for LintFinding.code,
    instead of pattern-matching free-text messages. It is not part of the
    MCN spec itself; only the message and line number are normative.
    """

    def __init__(
        self,
        message: str,
        line_no: Optional[int] = None,
        line_text: str = "",
        code: str = "syntax-error",
    ):
        self.line_no = line_no
        self.line_text = line_text
        self.code = code
        located = f"line {line_no}: {message}" if line_no is not None else message
        if line_text:
            located += f"\n    {line_text}"
        super().__init__(located)


class McnLintError(McnSyntaxError):
    """Raised instead of a warning when "@opt strict" is in force and a
    Sec 14.2 lint rule fires."""


# ---------------------------------------------------------------------------
# Profiles (spec Sec 6.1)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Profile:
    """A named, out-of-band bundle of directive settings, loaded by "@u
    name". Deployments maintain their own registry of these; this module
    only defines the shape and the effect of loading one.
    """

    base: Optional[str] = None
    prefixes: Dict[str, str] = field(default_factory=dict)
    target: Optional[str] = None
    options: Set[str] = field(default_factory=set)

    def content_hash(self) -> str:
        """A stable hash of this profile's content, recorded as
        mork:inputHash on the ontology node per spec Sec 6.1, so decoded
        output stays reproducible even though the profile itself is not
        in the document.
        """
        parts = [
            f"base={self.base or ''}",
            "prefixes=" + ",".join(f"{k}={v}" for k, v in sorted(self.prefixes.items())),
            f"target={self.target or ''}",
            "options=" + ",".join(sorted(self.options)),
        ]
        digest = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()
        return f"sha256:{digest}"


# ---------------------------------------------------------------------------
# Value: the result of reading one token in value position (spec Sec 3.3-3.4)
# ---------------------------------------------------------------------------


@dataclass
class Value:
    kind: str  # "bare" | "quoted" | "iri" | "inline"
    text: str  # for quoted: the unescaped string content
    lang: Optional[str] = None       # quoted only
    datatype: Optional[str] = None   # quoted only; a CURIE string


# ---------------------------------------------------------------------------
# Low-level line scanner: one logical line's worth of MCN syntax.
# Shared by node lines, block headers, inline-node bodies, annotation
# bodies, and the generic "code value-list" tail of axiom-line clauses.
# ---------------------------------------------------------------------------

_DELIMS = " \t,{}[]"
_ESCAPES = {"n": "\n", "t": "\t", '"': '"', "\\": "\\"}


class _Lexer:
    """A cursor over one logical line's text (spec Sec 3.3)."""

    def __init__(self, text: str, line_no: int):
        self.s = text
        self.i = 0
        self.n = len(text)
        self.line_no = line_no

    # -- primitives --

    def _err(self, message: str, code: str = "lex-error") -> McnSyntaxError:
        return McnSyntaxError(message, self.line_no, self.s, code=code)

    def peek_char(self) -> str:
        return self.s[self.i] if self.i < self.n else ""

    def skip_ws(self) -> None:
        while self.i < self.n and self.s[self.i] in " \t":
            self.i += 1

    def at_end(self) -> bool:
        self.skip_ws()
        return self.i >= self.n

    # -- quoted literal: "..." with escapes, optional @lang or ^curie --

    def read_quoted(self) -> Value:
        assert self.s[self.i] == '"'
        self.i += 1
        out: List[str] = []
        while True:
            if self.i >= self.n:
                raise self._err("unterminated quoted string", code="lex-unterminated-quoted-string")
            c = self.s[self.i]
            if c == "\\":
                if self.i + 1 >= self.n:
                    raise self._err("dangling backslash escape in quoted string", code="lex-dangling-backslash-escape-in-quoted-string")
                nxt = self.s[self.i + 1]
                if nxt == "u":
                    hexdigits = self.s[self.i + 2 : self.i + 6]
                    if len(hexdigits) != 4 or not re.fullmatch(r"[0-9A-Fa-f]{4}", hexdigits):
                        raise self._err(r"malformed \u escape in quoted string", code="lex-malformed-u-escape-in-quoted-string")
                    out.append(chr(int(hexdigits, 16)))
                    self.i += 6
                    continue
                if nxt not in _ESCAPES:
                    raise self._err(f"unknown escape '\\{nxt}' in quoted string", code="lex-unknown-escape-in-quoted-string")
                out.append(_ESCAPES[nxt])
                self.i += 2
                continue
            if c == '"':
                self.i += 1
                break
            out.append(c)
            self.i += 1
        text = "".join(out)
        lang = None
        datatype = None
        if self.peek_char() == "@":
            m = re.match(r"@([A-Za-z]+(?:-[A-Za-z0-9]+)*)", self.s[self.i :])
            if not m:
                raise self._err("malformed language tag after quoted string", code="lex-malformed-language-tag-after-quoted-string")
            lang = m.group(1)
            self.i += m.end()
        elif self.peek_char() == "^":
            m = re.match(r"\^([A-Za-z_][\w.\-]*:[\w.\-]+)", self.s[self.i :])
            if not m:
                raise self._err("malformed datatype CURIE after quoted string (expected ^prefix:local)", code="lex-malformed-datatype-curie-after-quoted-string")
            datatype = m.group(1)
            self.i += m.end()
        return Value(kind="quoted", text=text, lang=lang, datatype=datatype)

    # -- bracketed span: returns the *inner* text, unconsumed of quoting --

    def read_bracketed(self, open_ch: str, close_ch: str) -> str:
        assert self.s[self.i] == open_ch
        start = self.i
        depth = 0
        while self.i < self.n:
            c = self.s[self.i]
            if c == '"':
                # Skip over a quoted string verbatim so its brackets don't count.
                self._skip_quoted_verbatim()
                continue
            if c == open_ch:
                depth += 1
            elif c == close_ch:
                depth -= 1
                if depth == 0:
                    self.i += 1
                    return self.s[start + 1 : self.i - 1]
            self.i += 1
        raise self._err(f"unbalanced '{open_ch}'", code="lex-unbalanced")

    def _skip_quoted_verbatim(self) -> None:
        assert self.s[self.i] == '"'
        self.i += 1
        while self.i < self.n:
            c = self.s[self.i]
            if c == "\\":
                self.i += 2
                continue
            if c == '"':
                self.i += 1
                return
            self.i += 1
        raise self._err("unterminated quoted string", code="lex-unterminated-quoted-string")

    # -- bare token: runs until whitespace or a delimiter --

    def read_bare(self) -> str:
        start = self.i
        while self.i < self.n and self.s[self.i] not in _DELIMS:
            self.i += 1
        if self.i == start:
            raise self._err(f"unexpected character {self.s[self.i]!r}", code="lex-unexpected-character")
        return self.s[start : self.i]

    def peek_bare(self) -> str:
        save = self.i
        try:
            return self.read_bare()
        finally:
            self.i = save

    # -- one value (no list, no annotation) --

    def read_value(self) -> Value:
        self.skip_ws()
        c = self.peek_char()
        if c == "":
            raise self._err("expected a value, found end of line", code="lex-expected-a-value-found-end-of")
        if c == '"':
            return self.read_quoted()
        if c == "<":
            j = self.s.find(">", self.i)
            if j == -1:
                raise self._err("unterminated '<' IRI", code="lex-unterminated-iri")
            text = self.s[self.i + 1 : j]
            self.i = j + 1
            return Value(kind="iri", text=text)
        if c == "[":
            inner = self.read_bracketed("[", "]")
            return Value(kind="inline", text=inner)
        if c in "{}]":
            raise self._err(f"unexpected '{c}'", code="lex-unexpected")
        return Value(kind="bare", text=self.read_bare())

    # -- one value plus its optional {annotation}, for list members --

    def read_value_with_annotation(self) -> Tuple[Value, Optional[str]]:
        v = self.read_value()
        ann = None
        if self.peek_char() == "{":
            ann = self.read_bracketed("{", "}")
        return v, ann

    # -- value(,value)* --

    def read_value_list(self) -> List[Tuple[Value, Optional[str]]]:
        items = [self.read_value_with_annotation()]
        while self.peek_char() == ",":
            self.i += 1
            items.append(self.read_value_with_annotation())
        return items

    # -- a bare "word" (used for codes, keywords, ids) --

    def read_word(self) -> str:
        self.skip_ws()
        if self.at_end():
            raise self._err("expected a word, found end of line", code="lex-expected-a-word-found-end-of")
        return self.read_bare()

    def peek_word(self) -> Optional[str]:
        self.skip_ws()
        c = self.peek_char()
        if c in ("", '"', "<", "["):
            return None
        return self.peek_bare()


# ---------------------------------------------------------------------------
# Bracket/quote-aware top-level word splitter, used only for axiom-line
# (!C/!O/!D/!A) clause grouping (spec Sec 11), where fixed clause keywords
# and generic "code value" pairs are interleaved in one whitespace-
# separated tail and a value may itself contain nested [...] / {...} / "...".
# ---------------------------------------------------------------------------


def _split_top_level_words(text: str) -> List[str]:
    words: List[str] = []
    buf: List[str] = []
    i = 0
    n = len(text)
    depth = 0
    in_quote = False
    while i < n:
        ch = text[i]
        if in_quote:
            buf.append(ch)
            if ch == "\\" and i + 1 < n:
                buf.append(text[i + 1])
                i += 2
                continue
            if ch == '"':
                in_quote = False
            i += 1
            continue
        if ch == '"':
            in_quote = True
            buf.append(ch)
            i += 1
            continue
        if ch in "[{":
            depth += 1
            buf.append(ch)
            i += 1
            continue
        if ch in "]}":
            depth -= 1
            buf.append(ch)
            i += 1
            continue
        if ch in " \t" and depth == 0:
            if buf:
                words.append("".join(buf))
                buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    if in_quote:
        raise McnSyntaxError("unterminated quoted string", line_text=text, code="lex-unterminated-quoted-string")
    if depth != 0:
        raise McnSyntaxError("unbalanced brackets", line_text=text, code="lex-unbalanced-brackets")
    if buf:
        words.append("".join(buf))
    return words


# ---------------------------------------------------------------------------
# Literal construction (spec Sec 3.5)
# ---------------------------------------------------------------------------

_BOOL_TRUE = {"t", "true"}
_BOOL_FALSE = {"f", "false"}
_INT_RE = re.compile(r"-?[0-9]+")
_DECIMAL_RE = re.compile(r"-?[0-9]+\.[0-9]+")
_XSD_BOOLEAN = "xsd:boolean"


def _infer_literal_text(text: str) -> Tuple[str, Optional[str]]:
    """Spec Sec 3.5, "bare token, code's datatype is inferred" row.
    Returns (lexical_text, datatype_curie_or_None)."""
    if text in _BOOL_TRUE:
        return "true", _XSD_BOOLEAN
    if text in _BOOL_FALSE:
        return "false", _XSD_BOOLEAN
    if _INT_RE.fullmatch(text):
        return text, "xsd:integer"
    if _DECIMAL_RE.fullmatch(text):
        return text, "xsd:decimal"
    return text, None  # plain string


# ---------------------------------------------------------------------------
# Sec 10.5 -- OWL class-expression sub-language, also used for PE (property
# expressions) inside !O/!D clauses and for the !G general class inclusion.
# ---------------------------------------------------------------------------

_CE_TOKEN_RE = re.compile(
    r"""
      \d+\.\.\d*                 # n..  or n..m
    | \.\.\d+                    # ..m
    | \d+(?:\.\d+)?               # plain integer or decimal
    | [()&|~<>=#@{},^/]          # punctuation
    | "(?:[^"\\]|\\.)*"          # quoted string
    | :?[A-Za-z_][\w:.\-]*       # identifier (CURIE, :Local, local id, bare word)
    | \.[A-Za-z]+                # reserved token (.T, .N, ...)
    """,
    re.VERBOSE,
)


def _tokenize_ce(text: str, line_no: int) -> List[str]:
    tokens: List[str] = []
    pos = 0
    n = len(text)
    while pos < n:
        if text[pos] in " \t":
            pos += 1
            continue
        m = _CE_TOKEN_RE.match(text, pos)
        if not m:
            raise McnSyntaxError(
                f"malformed class expression near {text[pos:pos + 20]!r}", line_no, text,
                code="ce-malformed-class-expression-near",
            )
        tokens.append(m.group(0))
        pos = m.end()
    return tokens


class _ClassExpressionParser:
    """Recursive-descent parser for spec Sec 10.5's CE/IE/AE/PE grammar.

    ``resolve`` resolves an identifier token to an RDF term (URIRef);
    ``mint_bnode`` and ``rdf_list`` are supplied by the owning decoder so
    that blank-node numbering stays part of the single document-wide
    left-to-right pass (spec Sec 12.3).
    """

    def __init__(self, decoder: "_Decoder", tokens: List[str], line_no: int):
        self.d = decoder
        self.toks = tokens
        self.pos = 0
        self.line_no = line_no

    def _err(self, message: str, code: str = "ce-error"):
        return McnSyntaxError(message, self.line_no, code=code)

    def peek(self) -> Optional[str]:
        return self.toks[self.pos] if self.pos < len(self.toks) else None

    def take(self) -> str:
        if self.pos >= len(self.toks):
            raise self._err("unexpected end of class expression", code="ce-unexpected-end-of-class-expression")
        tok = self.toks[self.pos]
        self.pos += 1
        return tok

    def expect(self, tok: str) -> None:
        got = self.take()
        if got != tok:
            raise self._err(f"expected {tok!r}, found {got!r}", code="ce-expected-found")

    def at_end(self) -> bool:
        return self.pos >= len(self.toks)

    # CE := IE ('|' IE)*
    def parse_ce(self) -> URIRef:
        items = [self.parse_ie()]
        while self.peek() == "|":
            self.take()
            items.append(self.parse_ie())
        if len(items) == 1:
            return items[0]
        node = self.d._mint_bnode()
        self.d.graph.add((node, RDF.type, OWL.Class))
        self.d.graph.add((node, OWL.unionOf, self.d._rdf_list(items)))
        return node

    # IE := AE ('&' AE)*
    def parse_ie(self) -> URIRef:
        items = [self.parse_ae()]
        while self.peek() == "&":
            self.take()
            items.append(self.parse_ae())
        if len(items) == 1:
            return items[0]
        node = self.d._mint_bnode()
        self.d.graph.add((node, RDF.type, OWL.Class))
        self.d.graph.add((node, OWL.intersectionOf, self.d._rdf_list(items)))
        return node

    def parse_pe(self):
        """Returns (property_node, is_inverse: bool)."""
        if self.peek() == "^":
            self.take()
            prop = self.d._resolve_identifier(self.take(), self.line_no)
            inv_node = self.d._mint_bnode()
            self.d.graph.add((inv_node, RDF.type, OWL.ObjectProperty))
            self.d.graph.add((inv_node, OWL.inverseOf, prop))
            return inv_node, True
        prop = self.d._resolve_identifier(self.take(), self.line_no)
        return prop, False

    def parse_card(self) -> Tuple[Optional[int], Optional[int]]:
        """card := n | n'..' | '..'m | n'..'m -- as one pre-tokenized
        piece (the tokenizer already fuses these), or as separate tokens
        when a plain integer atom is followed by a bare '..'-prefixed
        continuation (handled by the tokenizer producing '..m' tokens).
        """
        tok = self.take()
        m = re.fullmatch(r"(\d+)?(\.\.)?(\d+)?", tok)
        if not m or tok == "":
            raise self._err(f"malformed cardinality {tok!r}", code="ce-malformed-cardinality")
        lo_s, dots, hi_s = m.group(1), m.group(2), m.group(3)
        lo = int(lo_s) if lo_s is not None else None
        hi = int(hi_s) if hi_s is not None else None
        if not dots:
            hi = lo
        return lo, hi

    # AE := '~' AE | '(' CE ')' | '{' ind,... '}' | PE op ... | identifier
    def parse_ae(self) -> URIRef:
        tok = self.peek()
        if tok is None:
            raise self._err("unexpected end of class expression", code="ce-unexpected-end-of-class-expression")
        if tok == "~":
            self.take()
            operand = self.parse_ae()
            node = self.d._mint_bnode()
            self.d.graph.add((node, RDF.type, OWL.Class))
            self.d.graph.add((node, OWL.complementOf, operand))
            return node
        if tok == "(":
            self.take()
            inner = self.parse_ce()
            self.expect(")")
            return inner
        if tok == "{":
            self.take()
            individuals = []
            while self.peek() != "}":
                t = self.take()
                individuals.append(self._resolve_enum_member(t))
                if self.peek() == ",":
                    self.take()
            self.expect("}")
            node = self.d._mint_bnode()
            self.d.graph.add((node, RDF.type, OWL.Class))
            self.d.graph.add((node, OWL.oneOf, self.d._rdf_list(individuals)))
            return node
        # Otherwise: either a PE followed by a restriction operator, or a
        # bare named class/datatype identifier.
        save = self.pos
        prop, _inv = self.parse_pe()
        op = self.peek()
        if op in (">", "<", "=", "#", "@"):
            return self._parse_restriction(prop)
        # Not a restriction: this was just a plain identifier atom, and
        # parse_pe already resolved + (for '^') possibly minted a spurious
        # inverse node. Roll back and resolve as a plain term instead.
        self.pos = save
        tok = self.take()
        return self._resolve_enum_member(tok)

    def _resolve_enum_member(self, tok: str):
        if tok.startswith('"'):
            inner = tok[1:-1]
            inner = inner.replace('\\"', '"').replace("\\\\", "\\")
            return Literal(inner)
        return self.d._resolve_identifier(tok, self.line_no)

    def _parse_restriction(self, prop: URIRef) -> URIRef:
        op = self.take()
        node = self.d._mint_bnode()
        self.d.graph.add((node, RDF.type, OWL.Restriction))
        self.d.graph.add((node, OWL.onProperty, prop))
        if op == ">":
            self.d.graph.add((node, OWL.someValuesFrom, self.parse_ae()))
        elif op == "<":
            self.d.graph.add((node, OWL.allValuesFrom, self.parse_ae()))
        elif op == "@":
            self.d.graph.add((node, OWL.hasSelf, Literal(True)))
        elif op == "=":
            tok = self.take()
            self.d.graph.add((node, OWL.hasValue, self._resolve_hasvalue(tok)))
        elif op == "#":
            lo, hi = self.parse_card()
            qualifier = None
            if self.peek() == "/":
                self.take()
                qualifier = self.parse_ae()
            nn = XSD.nonNegativeInteger
            if lo is not None and lo == hi:
                pred = OWL.qualifiedCardinality if qualifier is not None else OWL.cardinality
                self.d.graph.add((node, pred, Literal(lo, datatype=nn)))
            else:
                if lo is not None:
                    pred = OWL.minQualifiedCardinality if qualifier is not None else OWL.minCardinality
                    self.d.graph.add((node, pred, Literal(lo, datatype=nn)))
                if hi is not None:
                    pred = OWL.maxQualifiedCardinality if qualifier is not None else OWL.maxCardinality
                    self.d.graph.add((node, pred, Literal(hi, datatype=nn)))
            if qualifier is not None:
                self.d.graph.add((node, OWL.onClass, qualifier))
        else:
            raise self._err(f"unknown restriction operator {op!r}", code="ce-unknown-restriction-operator")
        return node

    def _resolve_hasvalue(self, tok: str):
        if tok.startswith('"'):
            return self._resolve_enum_member(tok)
        if tok in ("t", "f"):
            return Literal(tok == "t")
        if _INT_RE.fullmatch(tok):
            return Literal(int(tok))
        if _DECIMAL_RE.fullmatch(tok):
            return Literal(tok, datatype=XSD.decimal)
        return self.d._resolve_identifier(tok, self.line_no)


def _parse_class_expression(decoder: "_Decoder", text: str, line_no: int) -> URIRef:
    tokens = _tokenize_ce(text, line_no)
    parser = _ClassExpressionParser(decoder, tokens, line_no)
    result = parser.parse_ce()
    if not parser.at_end():
        raise McnSyntaxError(
            f"unexpected trailing content in class expression: {''.join(parser.toks[parser.pos:])!r}",
            line_no,
            code="ce-unexpected-trailing-content-in-class-expression",
        )
    return result


def _parse_property_expression(decoder: "_Decoder", text: str, line_no: int) -> URIRef:
    tokens = _tokenize_ce(text, line_no)
    parser = _ClassExpressionParser(decoder, tokens, line_no)
    node, _inv = parser.parse_pe()
    if not parser.at_end():
        raise McnSyntaxError(
            f"unexpected trailing content in property expression: {''.join(parser.toks[parser.pos:])!r}",
            line_no,
            code="ce-unexpected-trailing-content-in-property-expression",
        )
    return node


# ---------------------------------------------------------------------------
# Sec 10.2 -- SWRL compact payload
# ---------------------------------------------------------------------------

_SWRL_ARG_SPLIT_RE = re.compile(r'"(?:[^"\\]|\\.)*"(?:\^[\w.\-]+:[\w.\-]+)?|[^,]+')
_SWRL_ATOM_RE = re.compile(r"([\w:.\-]+)\(([^)]*)\)")


def _split_swrl_args(text: str) -> List[str]:
    return [m.group(0).strip() for m in _SWRL_ARG_SPLIT_RE.finditer(text) if m.group(0).strip()]


class _SwrlPayloadParser:
    """Parses the payload sub-notation of spec Sec 10.2 onto a pre-minted
    swrl:Imp node."""

    def __init__(self, decoder: "_Decoder", imp: URIRef, line_no: int):
        self.d = decoder
        self.imp = imp
        self.line_no = line_no
        self._vars: Dict[str, URIRef] = {}

    def _err(self, message: str, code: str = "swrl-error"):
        return McnSyntaxError(f"malformed SWRL payload: {message}", self.line_no, code=code)

    def parse(self, text: str) -> None:
        if "->" not in text:
            raise self._err("missing '->' separating body from head", code="swrl-missing-separating-body-from-head")
        body_text, head_text = text.split("->", 1)
        body_atoms = self._parse_atoms(body_text.strip())
        head_atoms = self._parse_atoms(head_text.strip())
        self.d.graph.add((self.imp, RDF.type, SWRL.Imp))
        self.d.graph.add((self.imp, SWRL.body, self.d._rdf_list(body_atoms, cell_type=SWRL.AtomList)))
        self.d.graph.add((self.imp, SWRL.head, self.d._rdf_list(head_atoms, cell_type=SWRL.AtomList)))

    def _parse_atoms(self, text: str) -> List[URIRef]:
        if not text:
            raise self._err("empty atom conjunction", code="swrl-empty-atom-conjunction")
        atoms = []
        pos = 0
        for m in _SWRL_ATOM_RE.finditer(text):
            atoms.append(self._make_atom(m.group(1), _split_swrl_args(m.group(2))))
        if not atoms:
            raise self._err(f"no atoms found in {text!r}", code="swrl-no-atoms-found-in")
        return atoms

    def _var(self, name: str) -> URIRef:
        if name not in self._vars:
            v = URIRef(f"{self.imp}_v_{name}")
            self.d.graph.add((v, RDF.type, SWRL.Variable))
            self._vars[name] = v
        return self._vars[name]

    def _arg(self, text: str):
        text = text.strip()
        if text.startswith("?"):
            return self._var(text[1:])
        if text.startswith('"'):
            m = re.fullmatch(r'"((?:[^"\\]|\\.)*)"(?:\^([\w.\-]+:[\w.\-]+))?', text)
            if not m:
                raise self._err(f"malformed literal argument {text!r}", code="swrl-malformed-literal-argument")
            unescaped = m.group(1).replace('\\"', '"').replace("\\\\", "\\")
            if m.group(2):
                return Literal(unescaped, datatype=self.d._resolve_curie(m.group(2), self.line_no))
            return Literal(unescaped)
        if _DECIMAL_RE.fullmatch(text):
            return Literal(text, datatype=XSD.decimal)
        if _INT_RE.fullmatch(text):
            return Literal(int(text))
        return self.d._resolve_identifier(text, self.line_no)

    def _make_atom(self, name: str, raw_args: List[str]) -> URIRef:
        node = self.d._mint_bnode()
        if name == "sameAs":
            self._require_arity(name, raw_args, 2)
            self.d.graph.add((node, RDF.type, SWRL.SameIndividualAtom))
            self.d.graph.add((node, SWRL.argument1, self._arg(raw_args[0])))
            self.d.graph.add((node, SWRL.argument2, self._arg(raw_args[1])))
            return node
        if name == "differentFrom":
            self._require_arity(name, raw_args, 2)
            self.d.graph.add((node, RDF.type, SWRL.DifferentIndividualsAtom))
            self.d.graph.add((node, SWRL.argument1, self._arg(raw_args[0])))
            self.d.graph.add((node, SWRL.argument2, self._arg(raw_args[1])))
            return node
        if name.startswith("swrlb:"):
            self.d.graph.add((node, RDF.type, SWRL.BuiltinAtom))
            self.d.graph.add((node, SWRL.builtin, self.d._resolve_curie(name, self.line_no)))
            arg_nodes = [self._arg(a) for a in raw_args]
            self.d.graph.add((node, SWRL.arguments, self.d._rdf_list(arg_nodes)))
            return node
        if name.startswith("xsd:") and len(raw_args) == 1:
            self.d.graph.add((node, RDF.type, SWRL.DataRangeAtom))
            self.d.graph.add((node, SWRL.dataRange, self.d._resolve_curie(name, self.line_no)))
            self.d.graph.add((node, SWRL.argument1, self._arg(raw_args[0])))
            return node
        predicate = self.d._resolve_identifier(name, self.line_no)
        if len(raw_args) == 1:
            self.d.graph.add((node, RDF.type, SWRL.ClassAtom))
            self.d.graph.add((node, SWRL.classPredicate, predicate))
            self.d.graph.add((node, SWRL.argument1, self._arg(raw_args[0])))
            return node
        if len(raw_args) == 2:
            arg2 = self._arg(raw_args[1])
            is_data = isinstance(arg2, Literal)
            self.d.graph.add(
                (node, RDF.type, SWRL.DatavaluedPropertyAtom if is_data else SWRL.IndividualPropertyAtom)
            )
            self.d.graph.add((node, SWRL.propertyPredicate, predicate))
            self.d.graph.add((node, SWRL.argument1, self._arg(raw_args[0])))
            self.d.graph.add((node, SWRL.argument2, arg2))
            return node
        raise self._err(f"atom {name}(...) has {len(raw_args)} arguments; expected 1 or 2", code="swrl-atom-has-arguments-expected-1-or")

    def _require_arity(self, name: str, args: List[str], expected: int) -> None:
        if len(args) != expected:
            raise self._err(f"{name}(...) expects {expected} arguments, found {len(args)}", code="swrl-expects-arguments-found")


# ---------------------------------------------------------------------------
# Sec 10.3 -- SHACL compact payload
# ---------------------------------------------------------------------------

_SH_TOKEN_RE = re.compile(
    r'>=|<=|\.\.|"(?:[^"\\]|\\.)*"|[;,\[\]{}></=^!]|-?\d+(?:\.\d+)?'
    r'|\.[A-Za-z]+|:?[A-Za-z_][\w:.\-]*'
)

_SH_SEVERITY = {".viol": SH.Violation, ".warn": SH.Warning, ".info": SH.Info}
_SH_NODEKIND = {
    "iri": SH.IRI,
    "bnode": SH.BlankNode,
    "lit": SH.Literal,
    "biri": SH.BlankNodeOrIRI,
    "blit": SH.BlankNodeOrLiteral,
    "ilit": SH.IRIOrLiteral,
}


def _tokenize_sh(text: str, line_no: int) -> List[str]:
    tokens = []
    pos = 0
    n = len(text)
    while pos < n:
        if text[pos] in " \t":
            pos += 1
            continue
        m = _SH_TOKEN_RE.match(text, pos)
        if not m:
            raise McnSyntaxError(f"malformed SHACL payload near {text[pos:pos + 20]!r}", line_no, code="shacl-malformed-shacl-payload-near")
        tokens.append(m.group(0))
        pos = m.end()
    return tokens


class _ShaclPayloadParser:
    def __init__(self, decoder: "_Decoder", shape: URIRef, line_no: int, bnode_shapes: bool):
        self.d = decoder
        self.shape = shape
        self.line_no = line_no
        self.bnode_shapes = bnode_shapes
        self.toks: List[str] = []
        self.pos = 0
        self._prop_shape_count = 0

    def _err(self, message: str, code: str = "shacl-error"):
        return McnSyntaxError(f"malformed SHACL payload: {message}", self.line_no, code=code)

    def peek(self) -> Optional[str]:
        return self.toks[self.pos] if self.pos < len(self.toks) else None

    def take(self) -> str:
        if self.pos >= len(self.toks):
            raise self._err("unexpected end of payload", code="shacl-unexpected-end-of-payload")
        t = self.toks[self.pos]
        self.pos += 1
        return t

    def expect(self, tok: str) -> str:
        got = self.take()
        if got != tok:
            raise self._err(f"expected {tok!r}, found {got!r}", code="shacl-expected-found")
        return got

    def parse(self, text: str) -> None:
        self.toks = _tokenize_sh(text, self.line_no)
        self.pos = 0
        self.d.graph.add((self.shape, RDF.type, SH.NodeShape))
        self._parse_targets()
        while self.peek() == ";":
            self.take()
            self._parse_clause()

    def _parse_targets(self) -> None:
        mode_pred = {"c": SH.targetClass, "o": SH.targetObjectsOf, "s": SH.targetSubjectsOf, "n": SH.targetNode}
        while True:
            mode = self.take()
            if mode not in mode_pred:
                raise self._err(f"unknown target mode {mode!r} (expected c/o/s/n)", code="shacl-unknown-target-mode-expected-c-o")
            target_iri = self._resolve(self.take())
            self.d.graph.add((self.shape, mode_pred[mode], target_iri))
            if self.peek() == ",":
                self.take()
                continue
            break

    def _parse_clause(self) -> None:
        tok = self.peek()
        if tok == "!":
            self.take()
            sev = self.take()
            if sev not in _SH_SEVERITY:
                raise self._err(f"unknown severity {sev!r}", code="shacl-unknown-severity")
            self.d.graph.add((self.shape, SH.severity, _SH_SEVERITY[sev]))
            return
        if tok == "msg":
            self.take()
            self.d.graph.add((self.shape, SH.message, self._literal_or_string(self.take())))
            return
        if tok == "closed":
            self.take()
            self.d.graph.add((self.shape, SH.closed, Literal(True)))
            return
        if tok == "ignore":
            self.take()
            props = [self._resolve(self.take())]
            while self.peek() == ",":
                self.take()
                props.append(self._resolve(self.take()))
            self.d.graph.add((self.shape, SH.ignoredProperties, self.d._rdf_list(props)))
            return
        if tok == "nd":
            self.take()
            self.d.graph.add((self.shape, SH.node, self._resolve(self.take())))
            return
        self._parse_property_shape()

    def _resolve(self, tok: str) -> URIRef:
        return self.d._resolve_identifier(tok, self.line_no)

    def _literal_or_string(self, tok: str):
        if tok.startswith('"'):
            inner = tok[1:-1].replace('\\"', '"').replace("\\\\", "\\")
            return Literal(inner)
        return Literal(tok)

    def _parse_path(self):
        elems = []
        while True:
            if self.peek() == "^":
                self.take()
                elems.append(("inv", self._resolve(self.take())))
            else:
                elems.append(("fwd", self._resolve(self.take())))
            if self.peek() == "/":
                self.take()
                continue
            break
        if len(elems) == 1:
            kind, iri = elems[0]
            if kind == "fwd":
                return iri
            inv_node = self.d._mint_bnode()
            self.d.graph.add((inv_node, SH.inversePath, iri))
            return inv_node
        nodes = []
        for kind, iri in elems:
            if kind == "fwd":
                nodes.append(iri)
            else:
                inv_node = self.d._mint_bnode()
                self.d.graph.add((inv_node, SH.inversePath, iri))
                nodes.append(inv_node)
        return self.d._rdf_list(nodes)

    def _parse_property_shape(self) -> None:
        self._prop_shape_count += 1
        if self.bnode_shapes:
            pshape = self.d._mint_bnode()
        else:
            pshape = URIRef(f"{self.shape}_p{self._prop_shape_count}")
        self.d.graph.add((pshape, RDF.type, SH.PropertyShape))
        self.d.graph.add((self.shape, SH.property, pshape))
        self.d.graph.add((pshape, SH.path, self._parse_path()))
        while self.peek() not in (None, ";"):
            self._parse_constraint(pshape)

    def _parse_count(self, pshape: URIRef) -> None:
        """Consumes 'n..m]' / 'n]' / '..m]' after the leading '[' has
        already been taken by the caller."""
        lo = None
        hi = None
        tok = self.take()
        if tok == "..":
            hi = int(self.take())
        else:
            lo = int(tok)
            if self.peek() == "..":
                self.take()
                if self.peek() not in (None, "]"):
                    hi = int(self.take())
            else:
                hi = lo
        self.expect("]")
        if lo is not None:
            self.d.graph.add((pshape, SH.minCount, Literal(lo, datatype=XSD.integer)))
        if hi is not None:
            self.d.graph.add((pshape, SH.maxCount, Literal(hi, datatype=XSD.integer)))

    def _parse_constraint(self, pshape: URIRef) -> None:
        tok = self.take()
        if tok == "dt":
            self.d.graph.add((pshape, SH.datatype, self._resolve(self.take())))
        elif tok == "cls":
            self.d.graph.add((pshape, SH["class"], self._resolve(self.take())))
        elif tok == "nd":
            self.d.graph.add((pshape, SH.node, self._resolve(self.take())))
        elif tok == "nk":
            kind = self.take()
            if kind not in _SH_NODEKIND:
                raise self._err(f"unknown node kind {kind!r}", code="shacl-unknown-node-kind")
            self.d.graph.add((pshape, SH.nodeKind, _SH_NODEKIND[kind]))
        elif tok == "[":
            self._parse_count(pshape)
        elif tok in (">=", "<=", ">", "<"):
            pred = {">=": SH.minInclusive, "<=": SH.maxInclusive, ">": SH.minExclusive, "<": SH.maxExclusive}[tok]
            self.d.graph.add((pshape, pred, self._number(self.take())))
        elif tok == "in":
            self.expect("{")
            values = [self._value(self.take())]
            while self.peek() == ",":
                self.take()
                values.append(self._value(self.take()))
            self.expect("}")
            self.d.graph.add((pshape, SH["in"], self.d._rdf_list(values)))
        elif tok == "re":
            self.d.graph.add((pshape, SH.pattern, self._literal_or_string(self.take())))
        elif tok == "len":
            self.expect("[")
            lo = self.take()
            self.expect("..")
            hi = self.take()
            self.expect("]")
            self.d.graph.add((pshape, SH.minLength, Literal(int(lo), datatype=XSD.integer)))
            self.d.graph.add((pshape, SH.maxLength, Literal(int(hi), datatype=XSD.integer)))
        elif tok == "=":
            self.d.graph.add((pshape, SH.hasValue, self._value(self.take())))
        elif tok == "eq":
            self.d.graph.add((pshape, SH.equals, self._resolve(self.take())))
        elif tok == "lt":
            self.d.graph.add((pshape, SH.lessThan, self._resolve(self.take())))
        elif tok == "lte":
            self.d.graph.add((pshape, SH.lessThanOrEquals, self._resolve(self.take())))
        elif tok == "disj":
            self.d.graph.add((pshape, SH.disjoint, self._resolve(self.take())))
        elif tok == "!":
            sev = self.take()
            if sev not in _SH_SEVERITY:
                raise self._err(f"unknown severity {sev!r}", code="shacl-unknown-severity")
            self.d.graph.add((pshape, SH.severity, _SH_SEVERITY[sev]))
        elif tok == "msg":
            self.d.graph.add((pshape, SH.message, self._literal_or_string(self.take())))
        elif tok == "name":
            self.d.graph.add((pshape, SH.name, self._literal_or_string(self.take())))
        else:
            raise self._err(f"unknown property-shape constraint {tok!r}", code="shacl-unknown-property-shape-constraint")

    def _number(self, tok: str):
        if _DECIMAL_RE.fullmatch(tok):
            return Literal(tok, datatype=XSD.decimal)
        return Literal(int(tok))

    def _value(self, tok: str):
        if tok.startswith('"'):
            return self._literal_or_string(tok)
        if tok in ("t", "f"):
            return Literal(tok == "t")
        if _DECIMAL_RE.fullmatch(tok):
            return Literal(tok, datatype=XSD.decimal)
        if _INT_RE.fullmatch(tok):
            return Literal(int(tok))
        return self._resolve(tok)


# ---------------------------------------------------------------------------
# Sec 10.4 -- RML compact payload
# ---------------------------------------------------------------------------

_RML_REF_FORMULATION = {
    "json": _QL.JSONPath,
    "csv": _QL.CSV,
    "xml": _QL.XPath,
}


class _RmlPayloadParser:
    """Parses the payload sub-notation of spec Sec 10.4 onto a pre-minted
    rr:TriplesMap node."""

    def __init__(self, decoder: "_Decoder", tm: URIRef, line_no: int):
        self.d = decoder
        self.tm = tm
        self.line_no = line_no

    def _err(self, message: str, code: str = "rml-error"):
        return McnSyntaxError(f"malformed RML payload: {message}", self.line_no, code=code)

    def parse(self, text: str) -> None:
        self.d.graph.add((self.tm, RDF.type, RR.TriplesMap))
        clauses = _split_top_level_words_on_semicolons(text)
        if not clauses:
            raise self._err("empty payload", code="rml-empty-payload")
        self._parse_logical_source(clauses[0])
        if len(clauses) < 2:
            raise self._err("missing subject map ('sm ...') clause", code="rml-missing-subject-map-sm-clause")
        self._parse_subject_map(clauses[1])
        for clause in clauses[2:]:
            self._parse_predicate_object_map(clause)

    def _parse_logical_source(self, clause: str) -> None:
        words = _split_top_level_words(clause)
        if not words or words[0] != "src":
            raise self._err("logical source clause must start with 'src'", code="rml-logical-source-clause-must-start-with")
        i = 1
        if i >= len(words):
            raise self._err("'src' requires a source string", code="rml-src-requires-a-source-string")
        source = self._string(words[i])
        i += 1
        ref_formulation = _RML_REF_FORMULATION["json"]
        iterator = None
        while i < len(words):
            if words[i] == "ref":
                i += 1
                fmt = words[i]
                if fmt not in _RML_REF_FORMULATION:
                    raise self._err(f"unknown reference formulation {fmt!r}", code="rml-unknown-reference-formulation")
                ref_formulation = _RML_REF_FORMULATION[fmt]
                i += 1
            elif words[i] == "it":
                i += 1
                iterator = self._string(words[i])
                i += 1
            else:
                raise self._err(f"unexpected token in logical source: {words[i]!r}", code="rml-unexpected-token-in-logical-source")
        ls = self.d._mint_bnode()
        self.d.graph.add((self.tm, RML.logicalSource, ls))
        self.d.graph.add((ls, RML.source, Literal(source)))
        self.d.graph.add((ls, RML.referenceFormulation, ref_formulation))
        if iterator is not None:
            self.d.graph.add((ls, RML.iterator, Literal(iterator)))

    def _parse_subject_map(self, clause: str) -> None:
        words = _split_top_level_words(clause)
        if not words or words[0] != "sm":
            raise self._err("subject map clause must start with 'sm'", code="rml-subject-map-clause-must-start-with")
        if len(words) < 2:
            raise self._err("'sm' requires a template", code="rml-sm-requires-a-template")
        template = words[1]
        sm = self.d._mint_bnode()
        self.d.graph.add((self.tm, RR.subjectMap, sm))
        self.d.graph.add((sm, RR.template, Literal(self._unquote_maybe(template))))
        i = 2
        while i < len(words):
            if words[i] != "cls":
                raise self._err(f"unexpected token in subject map: {words[i]!r}", code="rml-unexpected-token-in-subject-map")
            i += 1
            self.d.graph.add((sm, RR["class"], self.d._resolve_identifier(words[i], self.line_no)))
            i += 1

    def _parse_predicate_object_map(self, clause: str) -> None:
        words = _split_top_level_words(clause)
        if len(words) < 2:
            raise self._err(f"malformed predicate-object map: {clause!r}", code="rml-malformed-predicate-object-map")
        predicate = self.d._resolve_identifier(words[0], self.line_no)
        pom = self.d._mint_bnode()
        self.d.graph.add((self.tm, RR.predicateObjectMap, pom))
        self.d.graph.add((pom, RR.predicate, predicate))
        om = self.d._mint_bnode()
        self.d.graph.add((pom, RR.objectMap, om))
        op = words[1]
        i = 2
        if op.startswith("="):
            self.d.graph.add((om, RML.reference, Literal(self._unquote_maybe(op[1:]))))
        elif op.startswith(":"):
            self.d.graph.add((om, RR.constant, self._constant(op[1:])))
        elif op.startswith("@"):
            self.d.graph.add((om, RR.template, Literal(self._unquote_maybe(op[1:]))))
        elif op.startswith("^"):
            ref = op[1:]
            join_text = None
            if "[" in ref:
                ref, bracketed = ref.split("[", 1)
                if not bracketed.endswith("]"):
                    raise self._err(f"unbalanced '[' in join condition: {op!r}", code="rml-unbalanced-in-join-condition")
                join_text = bracketed[:-1]
            parent = self.d._resolve_identifier(ref, self.line_no)
            self.d.graph.add((om, RR.parentTriplesMap, parent))
            if join_text is not None:
                for pair in join_text.split(","):
                    child, _, par = pair.partition("=")
                    jc = self.d._mint_bnode()
                    self.d.graph.add((om, RR.joinCondition, jc))
                    self.d.graph.add((jc, RR.child, Literal(child.strip())))
                    self.d.graph.add((jc, RR.parent, Literal(par.strip())))
        else:
            raise self._err(f"unknown object-map operator {op[:1]!r} in {op!r}", code="rml-unknown-object-map-operator-in")
        while i < len(words):
            if words[i] == "dt":
                i += 1
                self.d.graph.add((om, RR.datatype, self.d._resolve_identifier(words[i], self.line_no)))
                i += 1
            elif words[i] == "lang":
                i += 1
                self.d.graph.add((om, RR.language, Literal(words[i])))
                i += 1
            else:
                raise self._err(f"unexpected trailing token {words[i]!r} in predicate-object map", code="rml-unexpected-trailing-token-in-predicate-object")

    def _string(self, tok: str) -> str:
        if tok.startswith('"'):
            return tok[1:-1].replace('\\"', '"').replace("\\\\", "\\")
        return tok

    def _unquote_maybe(self, tok: str) -> str:
        return self._string(tok)

    def _constant(self, tok: str):
        if tok.startswith('"'):
            return Literal(self._string(tok))  # literal for :"..." constants
        return self.d._resolve_identifier(tok, self.line_no)


# ---------------------------------------------------------------------------
# Sec 10.1 -- Template expression sub-language
# ---------------------------------------------------------------------------


def _expr_split_top_level(text: str, sep: str) -> List[str]:
    """Splits ``text`` on ``sep`` at top level only, respecting '...' and
    "..." quoting and (...) nesting -- the expression sub-language's own
    delimiters, distinct from the rest of MCN's [...]/{...}/"..." (spec
    Sec 10.1 uses single quotes for LiteralExpression content, and a
    double-quoted span may itself appear nested inside an interpolation
    term, e.g. %"{l}, {f}"(...)).
    """
    parts: List[str] = []
    buf: List[str] = []
    depth = 0
    quote: Optional[str] = None
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if quote:
            buf.append(ch)
            if ch == "\\" and i + 1 < n:
                buf.append(text[i + 1])
                i += 2
                continue
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in ("'", '"'):
            quote = ch
            buf.append(ch)
            i += 1
            continue
        if ch == "(":
            depth += 1
            buf.append(ch)
            i += 1
            continue
        if ch == ")":
            depth -= 1
            buf.append(ch)
            i += 1
            continue
        if ch == sep and depth == 0:
            parts.append("".join(buf).strip())
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    parts.append("".join(buf).strip())
    return parts


class _ExpressionParser:
    """Builds a mork:TemplateExpression tree under a given root node from
    raw expression text (spec Sec 10.1)."""

    def __init__(self, decoder: "_Decoder", line_no: int):
        self.d = decoder
        self.line_no = line_no

    def _err(self, message: str, code: str = "expr-error"):
        return McnSyntaxError(f"malformed expression: {message}", self.line_no, code=code)

    def parse_into(self, node: URIRef, text: str, *, is_root: bool = False) -> URIRef:
        text = text.strip()
        if not text:
            raise self._err("empty expression", code="expr-empty-expression")
        return self._build(node, text, is_root=is_root)

    def _build(self, node: URIRef, text: str, *, is_root: bool = False) -> URIRef:
        parts = _expr_split_top_level(text, "+")
        if not parts or any(p == "" for p in parts):
            raise self._err(f"empty term in {text!r}", code="expr-empty-term-in")
        if len(parts) == 1:
            resolved = self._term(node, parts[0])
            if is_root and resolved != node:
                # The whole expression was a bare reference to another
                # expression node: `id` names an alias for it.
                self.d._assert_named_individual(node)
                self.d.graph.add((node, OWL.sameAs, resolved))
            return node if is_root else resolved
        last = parts[-1]
        rest = "+".join(parts[:-1])
        left_node = URIRef(f"{node}_l")
        right_node = URIRef(f"{node}_r")
        left_resolved = self._build(left_node, rest)
        right_resolved = self._term(right_node, last)
        self.d._add_type(node, MORK.ConcatExpression, "mork:ConcatExpression")
        self.d.graph.add((node, MORK.concatLeft, left_resolved))
        self.d.graph.add((node, MORK.concatRight, right_resolved))
        return node

    def _term(self, node: URIRef, text: str) -> URIRef:
        text = text.strip()
        if text.startswith("'"):
            content = self._read_quoted(text, "'")
            self.d._add_type(node, MORK.LiteralExpression, "mork:LiteralExpression")
            self.d.graph.add((node, MORK.dataInline, Literal(content)))
            return node
        if text.startswith("$"):
            path = text[1:].strip()
            if path.startswith('"'):
                path = self._read_quoted(path, '"')
            self.d._add_type(node, MORK.RefExpression, "mork:RefExpression")
            self.d.graph.add((node, MORK.dataRef, Literal(path)))
            return node
        if text.startswith("%"):
            return self._interpolation(node, text)
        if text.startswith("?"):
            return self._lookup(node, text)
        if text.startswith("(") and text.endswith(")"):
            return self._build(node, text[1:-1])
        # A bare reference to an already-defined expression node.
        return self.d._resolve_identifier(text, self.line_no)

    def _read_quoted(self, text: str, quote_char: str) -> str:
        if not text.startswith(quote_char):
            raise self._err(f"expected {quote_char!r} at start of {text!r}", code="expr-expected-at-start-of")
        out: List[str] = []
        i = 1
        n = len(text)
        escapes = {"n": "\n", "t": "\t", quote_char: quote_char, "\\": "\\"}
        while i < n:
            c = text[i]
            if c == "\\" and i + 1 < n and text[i + 1] in escapes:
                out.append(escapes[text[i + 1]])
                i += 2
                continue
            if c == quote_char:
                i += 1
                break
            out.append(c)
            i += 1
        else:
            raise self._err(f"unterminated {quote_char!r} in {text!r}", code="expr-unterminated-in")
        if i != n:
            raise self._err(f"unexpected trailing content after quoted span: {text!r}", code="expr-unexpected-trailing-content-after-quoted-span")
        return "".join(out)

    def _interpolation(self, node: URIRef, text: str) -> URIRef:
        m = re.match(r'%"((?:[^"\\]|\\.)*)"\((.*)\)$', text, re.DOTALL)
        if not m:
            raise self._err(f"malformed interpolation expression {text!r}", code="expr-malformed-interpolation-expression")
        template = m.group(1).replace('\\"', '"').replace("\\\\", "\\")
        bindings_text = m.group(2).strip()
        self.d._add_type(node, MORK.InterpolationExpression, "mork:InterpolationExpression")
        self.d.graph.add((node, MORK.templateString, Literal(template)))
        parts = _expr_split_top_level(bindings_text, ",") if bindings_text else []
        if not parts:
            raise self._err("interpolation expression has no bindings", code="expr-interpolation-expression-has-no-bindings")
        for idx, part in enumerate(parts, start=1):
            name, sep, expr_text = part.partition("=")
            if not sep:
                raise self._err(f"malformed binding {part!r} (expected name=expr)", code="expr-malformed-binding-expected-name-expr")
            binding = URIRef(f"{node}_b{idx}")
            self.d._add_type(binding, MORK.TemplateBinding, "mork:TemplateBinding")
            self.d.graph.add((node, MORK.hasBinding, binding))
            self.d.graph.add((binding, MORK.placeholderName, Literal(name.strip())))
            expr_node = URIRef(f"{binding}_e")
            resolved = self._build(expr_node, expr_text.strip())
            self.d.graph.add((binding, MORK.placeholderExpression, resolved))
        return node

    def _lookup(self, node: URIRef, text: str) -> URIRef:
        m = re.match(r"\?([^.(]+)\.([^(]+)\((.*)\)$", text, re.DOTALL)
        if not m:
            raise self._err(f"malformed lookup expression {text!r}", code="expr-malformed-lookup-expression")
        scheme_tok, prop_tok, source_text = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
        self.d._add_type(node, MORK.LookupExpression, "mork:LookupExpression")
        self.d.graph.add((node, MORK.lookupScheme, self.d._resolve_identifier(scheme_tok, self.line_no)))
        self.d.graph.add((node, MORK.lookupProperty, self.d._resolve_identifier(prop_tok, self.line_no)))
        source_node = URIRef(f"{node}_s")
        resolved = self._build(source_node, source_text)
        self.d.graph.add((node, MORK.lookupSource, resolved))
        return node


def _split_top_level_words_on_semicolons(text: str) -> List[str]:
    """Splits an RML payload into its ';'-separated clauses, respecting
    quotes and [...] nesting (join-condition lists)."""
    parts: List[str] = []
    buf: List[str] = []
    depth = 0
    in_quote = False
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if in_quote:
            buf.append(ch)
            if ch == "\\" and i + 1 < n:
                buf.append(text[i + 1])
                i += 2
                continue
            if ch == '"':
                in_quote = False
            i += 1
            continue
        if ch == '"':
            in_quote = True
            buf.append(ch)
            i += 1
            continue
        if ch == "[":
            depth += 1
            buf.append(ch)
            i += 1
            continue
        if ch == "]":
            depth -= 1
            buf.append(ch)
            i += 1
            continue
        if ch == ";" and depth == 0:
            parts.append("".join(buf).strip())
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    tail = "".join(buf).strip()
    if tail:
        parts.append(tail)
    return [p for p in parts if p]


# ---------------------------------------------------------------------------
# The decoder proper (spec Sec 13, D1-D9)
# ---------------------------------------------------------------------------

_EXPRESSION_VALUED_CODES = {"pe", "ls", "cl", "cr"}
_ARTEFACT_PAYLOAD_CODES = {"gs": "SH", "gr": "SW", "gt": "TM"}
_ANNOTATION_ONLY_CLAUSE_KEYWORDS = {"=", "<", "!", "dom", "rng", "inv", "chain"}
_CHARACTERISTIC_FLAG_RE = re.compile(r"^\+(F|IF|S|AS|T|R|IR)(\+(F|IF|S|AS|T|R|IR))*$")
_OBJECT_PROPERTY_CHARACTERISTICS = {
    "F": OWL.FunctionalProperty,
    "IF": OWL.InverseFunctionalProperty,
    "S": OWL.SymmetricProperty,
    "AS": OWL.AsymmetricProperty,
    "T": OWL.TransitiveProperty,
    "R": OWL.ReflexiveProperty,
    "IR": OWL.IrreflexiveProperty,
}


class _Decoder:
    """One decode() call's worth of state. Not reused across documents."""

    def __init__(self, profiles: Optional[Mapping[str, Profile]] = None):
        self.profiles: Mapping[str, Profile] = profiles or {}
        self.graph = Graph()
        for prefix, iri in cb.PREDECLARED_PREFIXES.items():
            self.graph.bind(prefix, Namespace(iri))

        self.prefixes: Dict[str, str] = dict(cb.PREDECLARED_PREFIXES)
        self.base: Optional[str] = None
        self.target_prefix: Optional[str] = None
        self.options: Set[str] = set()
        self.ontology: Optional[URIRef] = None
        self._pending_profile_hashes: List[str] = []

        # Block context (Sec 7): membership predicate CURIE, scheme node,
        # default type code. None/None/None means "%X".
        self.block_membership: Optional[str] = None
        self.block_scheme: Optional[URIRef] = None
        self.block_default_type: Optional[str] = None

        self._bnode_counter = 0
        self._axiom_bnode_counter = 0
        self._named_bnodes: Dict[str, BNode] = {}
        self._mint_counters: Dict[Tuple[str, str], int] = {}
        self._subject_types: Dict[URIRef, Set[str]] = {}

        self._line_no = 0
        self._current_line_text = ""

    # -- error helper --------------------------------------------------

    def _error(self, message: str, code: str = "core-error") -> McnSyntaxError:
        return McnSyntaxError(message, self._line_no, self._current_line_text, code=code)

    # -- identifier resolution (Sec 3.4) --------------------------------

    def _parse_iri_literal(self, tok: str) -> URIRef:
        tok = tok.strip()
        if tok.startswith("<") and tok.endswith(">") and len(tok) >= 2:
            return URIRef(tok[1:-1])
        if not tok:
            raise self._error("expected an IRI", code="core-expected-an-iri")
        return URIRef(tok)

    def _resolve_curie(self, curie: str, line_no: Optional[int] = None) -> URIRef:
        prefix, sep, local = curie.partition(":")
        if not sep:
            raise McnSyntaxError(f"malformed CURIE {curie!r}", line_no or self._line_no, self._current_line_text, code="core-malformed-curie")
        if prefix not in self.prefixes:
            raise McnSyntaxError(
                f"unbound prefix {prefix!r} in {curie!r}", line_no or self._line_no, self._current_line_text,
                code="core-unbound-prefix-in",
            )
        return URIRef(self.prefixes[prefix] + local)

    def _resolve_identifier(self, tok: str, line_no: Optional[int] = None):
        ln = line_no if line_no is not None else self._line_no
        if tok.startswith("<") and tok.endswith(">") and len(tok) >= 2:
            return URIRef(tok[1:-1])
        if tok in cb.RESERVED:
            return self._resolve_curie(cb.RESERVED[tok], ln)
        if tok.startswith("_:"):
            label = tok[2:]
            if not label:
                raise McnSyntaxError("empty blank node label after '_:'", ln, self._current_line_text, code="core-empty-blank-node-label-after")
            if label not in self._named_bnodes:
                self._named_bnodes[label] = BNode()
            return self._named_bnodes[label]
        if tok.startswith(":"):
            if self.target_prefix is None:
                raise McnSyntaxError(
                    f"{tok!r} used but no '@t' default target prefix is in force", ln, self._current_line_text,
                    code="core-used-but-no-t-default-target",
                )
            return URIRef(self.prefixes[self.target_prefix] + tok[1:])
        if ":" in tok:
            return self._resolve_curie(tok, ln)
        if not tok or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.\-]*", tok):
            raise McnSyntaxError(f"malformed identifier {tok!r}", ln, self._current_line_text, code="core-malformed-identifier")
        if self.base is None:
            raise McnSyntaxError(f"local id {tok!r} used but no '@b' base IRI is in force", ln, self._current_line_text, code="core-local-id-used-but-no-b")
        return URIRef(self.base + tok)

    def _resolve_value_as_identifier(self, value: Value):
        if value.kind == "iri":
            return URIRef(value.text)
        if value.kind == "bare":
            return self._resolve_identifier(value.text)
        raise self._error(f"cannot resolve a {value.kind} value as an identifier", code="core-cannot-resolve-a-value-as-an")

    # -- type detection and assertion (Sec 9.2, Sec 8.1, Sec 11) --------

    def _is_type_like(self, tok: str) -> bool:
        if tok in cb.TYPES:
            return True
        if tok.startswith(":"):
            local = tok[1:]
            return bool(local) and local[0].isupper()
        if ":" in tok:
            _prefix, _sep, local = tok.partition(":")
            return bool(local) and local[0].isupper()
        return False

    def _looks_like_typelist(self, tok: Optional[str]) -> bool:
        if not tok:
            return False
        if tok.startswith("+"):
            return True
        parts = tok.split("+")
        return bool(parts) and all(p and self._is_type_like(p) for p in parts)

    def _resolve_type_token(self, tok: str, *, allow_bare_local: bool = False) -> Tuple[URIRef, str]:
        forced = tok.startswith("+")
        if forced:
            tok = tok[1:]
            if not tok:
                raise self._error("empty type token after '+'", code="core-empty-type-token-after")
        if tok in cb.TYPES:
            curie = cb.TYPES[tok].curie
            return self._resolve_curie(curie), curie
        if tok.startswith(":") or ":" in tok:
            return self._resolve_identifier(tok), tok
        if forced or allow_bare_local:
            return self._resolve_identifier(tok), tok
        raise self._error(f"unknown type code {tok!r}", code="core-unknown-type-code")

    def _assert_named_individual(self, subject) -> None:
        self.graph.add((subject, RDF.type, OWL.NamedIndividual))

    def _add_type(self, subject, class_iri: URIRef, key: str) -> URIRef:
        self._assert_named_individual(subject)
        self.graph.add((subject, RDF.type, class_iri))
        self._subject_types.setdefault(subject, set()).add(key)
        return subject

    def _assert_type(self, subject, tok: str, *, allow_bare_local: bool = False) -> None:
        class_iri, key = self._resolve_type_token(tok, allow_bare_local=allow_bare_local)
        self._add_type(subject, class_iri, key)

    def _assert_type_list(self, subject, type_list_token: str, *, allow_bare_local: bool = False) -> None:
        if type_list_token.startswith("+"):
            for part in type_list_token[1:].split("+"):
                self._assert_type(subject, "+" + part, allow_bare_local=allow_bare_local)
            return
        for part in type_list_token.split("+"):
            self._assert_type(subject, part, allow_bare_local=allow_bare_local)

    # -- minting (Sec 12.2, Sec 12.3) ------------------------------------

    def _mint(self, parent: URIRef, code: str) -> URIRef:
        key = (str(parent), code)
        self._mint_counters[key] = self._mint_counters.get(key, 0) + 1
        node = URIRef(f"{parent}_{code}{self._mint_counters[key]}")
        self._assert_named_individual(node)
        return node

    def _mint_bnode(self) -> BNode:
        self._bnode_counter += 1
        return BNode(f"b{self._bnode_counter}")

    def _mint_axiom_bnode(self) -> BNode:
        self._axiom_bnode_counter += 1
        return BNode(f"a{self._axiom_bnode_counter}")

    def _rdf_list(self, items: Sequence, *, cell_type: Optional[URIRef] = None):
        items = list(items)
        if not items:
            return RDF.nil
        cells = [self._mint_bnode() for _ in items]
        for idx, (cell, item) in enumerate(zip(cells, items)):
            if cell_type is not None:
                self.graph.add((cell, RDF.type, cell_type))
            self.graph.add((cell, RDF.first, item))
            nxt = cells[idx + 1] if idx + 1 < len(cells) else RDF.nil
            self.graph.add((cell, RDF.rest, nxt))
        return cells[0]

    # -- literal construction (Sec 3.5) ----------------------------------

    def _literal_for_value(self, value: Value, datatype_spec: Optional[str]) -> Literal:
        if value.kind == "quoted":
            if value.lang:
                return Literal(value.text, lang=value.lang)
            if value.datatype:
                return Literal(value.text, datatype=self._resolve_curie(value.datatype))
            return Literal(value.text)
        if value.kind != "bare":
            raise self._error(f"expected a literal (quoted string or bare token), found {value.kind}", code="core-expected-a-literal-quoted-string-or")
        text = value.text
        if datatype_spec == "*":
            lex, inferred = _infer_literal_text(text)
            return Literal(lex, datatype=self._resolve_curie(inferred)) if inferred else Literal(lex)
        if datatype_spec is None:
            return Literal(text)
        if datatype_spec == _XSD_BOOLEAN:
            if text in _BOOL_TRUE:
                return Literal(True)
            if text in _BOOL_FALSE:
                return Literal(False)
            raise self._error(f"expected a boolean (t/f/true/false), found {text!r}", code="core-expected-a-boolean-t-f-true")
        return Literal(text, datatype=self._resolve_curie(datatype_spec))

    # -- expression-span reading (used by pe/ls/cl/cr and hb's 2nd slot) -

    def _read_expression_span(self, lx: _Lexer) -> str:
        lx.skip_ws()
        start = lx.i
        depth = 0
        quote: Optional[str] = None
        while lx.i < lx.n:
            ch = lx.s[lx.i]
            if quote:
                if ch == "\\" and lx.i + 1 < lx.n:
                    lx.i += 2
                    continue
                if ch == quote:
                    quote = None
                lx.i += 1
                continue
            if ch in ("'", '"'):
                quote = ch
                lx.i += 1
                continue
            if ch == "(":
                depth += 1
                lx.i += 1
                continue
            if ch == ")":
                depth -= 1
                lx.i += 1
                continue
            if depth == 0 and ch in ",}]{":
                break
            lx.i += 1
        if quote:
            raise self._error("unterminated quote in expression value", code="core-unterminated-quote-in-expression-value")
        if depth != 0:
            raise self._error("unbalanced parentheses in expression value", code="core-unbalanced-parentheses-in-expression-value")
        span = lx.s[start : lx.i].strip()
        if not span:
            raise self._error("expected an expression value", code="core-expected-an-expression-value")
        return span

    def _read_slot_or_skip(self, lx: _Lexer) -> Optional[Value]:
        """One positional slot: a value, or '_' to skip it (Sec 9.6)."""
        lx.skip_ws()
        if lx.peek_char() not in ('"', "<", "["):
            save = lx.i
            tok = lx.read_bare()
            if tok == "_":
                return None
            lx.i = save
        return lx.read_value()

    # -- property-pair resolution and assertion (D6) ---------------------

    def _resolve_predicate(self, subject, code: str) -> Tuple[URIRef, str, Optional[str]]:
        """Returns (predicate, kind, matched_polymorphic_key). ``kind`` is
        one of cb.KIND_OBJECT, cb.KIND_DATA, or "curie" (a code-position
        CURIE, whose per-value kind is decided dynamically, Sec 4)."""
        if code in cb.PROPERTIES:
            spec = cb.PROPERTIES[code]
            if spec.kind == cb.KIND_POLYMORPHIC:
                table = cb.POLYMORPHIC[code]
                types_here = self._subject_types.get(subject, set())
                for type_key, prop_curie in table.items():
                    if type_key == "*":
                        continue
                    if type_key in types_here:
                        return self._resolve_curie(prop_curie), cb.KIND_OBJECT, type_key
                if "*" in table:
                    return self._resolve_curie(table["*"]), cb.KIND_OBJECT, "*"
                raise self._error(
                    f"cannot resolve polymorphic code {code!r}: subject's types "
                    f"{sorted(types_here) or ['<none>']} match none of {sorted(table)}",
                    code="core-cannot-resolve-polymorphic-code-subject-s",
                )
            return self._resolve_curie(spec.curie), spec.kind, None
        if ":" in code:
            return self._resolve_curie(code), "curie", None
        raise self._error(f"unknown property code {code!r}", code="core-unknown-property-code")

    def _resolve_object(self, subject, code: str, value: Value, kind: str, matched_key: Optional[str]):
        if kind == cb.KIND_DATA:
            if value.kind == "inline":
                raise self._error(f"code {code!r} takes a literal value, not an inline node", code="core-code-takes-a-literal-value-not")
            if value.kind == "iri":
                raise self._error(f"code {code!r} takes a literal value, not an IRI", code="core-code-takes-a-literal-value-not")
            return self._literal_for_value(value, cb.PROPERTIES[code].datatype)
        if value.kind == "inline":
            return self._decode_inline(value.text, subject, code, matched_key)
        if code == "tg" and value.kind in ("bare", "iri"):
            placeholder_target = value.text if value.kind == "bare" else f"<{value.text}>"
            return self._decode_inline(f"c {placeholder_target}", subject, code, matched_key)
        if code in _ARTEFACT_PAYLOAD_CODES and value.kind == "quoted":
            return self._decode_artefact_payload(code, value.text, subject)
        if kind == "curie":
            if value.kind == "quoted":
                return self._literal_for_value(value, None)
            return self._resolve_value_as_identifier(value)
        # object kind
        if value.kind == "quoted":
            raise self._error(f"code {code!r} takes an object (IRI) value, not a quoted string", code="core-code-takes-an-object-iri-value")
        return self._resolve_value_as_identifier(value)

    def _assert_annotation(self, subject, predicate, obj, annotation_body: str) -> None:
        axiom = self._mint_axiom_bnode()
        self.graph.add((axiom, RDF.type, OWL.Axiom))
        self.graph.add((axiom, OWL.annotatedSource, subject))
        self.graph.add((axiom, OWL.annotatedProperty, predicate))
        self.graph.add((axiom, OWL.annotatedTarget, obj))
        lx = _Lexer(annotation_body, self._line_no)
        self._decode_pairs(axiom, lx)

    def _assert_one(self, subject, code: str, value: Value, annotation_body: Optional[str]) -> None:
        predicate, kind, matched_key = self._resolve_predicate(subject, code)
        obj = self._resolve_object(subject, code, value, kind, matched_key)
        self.graph.add((subject, predicate, obj))
        if code in cb.IMPLIED_TYPE_FOR_CODE:
            self._assert_type(subject, cb.IMPLIED_TYPE_FOR_CODE[code])
        if annotation_body is not None:
            self._assert_annotation(subject, predicate, obj, annotation_body)

    def _assert_property_pair(self, subject, code: str, lx: _Lexer) -> None:
        lx.skip_ws()
        if code in _EXPRESSION_VALUED_CODES and lx.peek_char() != "[":
            span = self._read_expression_span(lx)
            node = self._mint(subject, code)
            resolved = _ExpressionParser(self, self._line_no).parse_into(node, span)
            predicate, _kind, _matched = self._resolve_predicate(subject, code)
            self.graph.add((subject, predicate, resolved))
            ann = None
            if lx.peek_char() == "{":
                ann = lx.read_bracketed("{", "}")
                self._assert_annotation(subject, predicate, resolved, ann)
            return
        for value, annotation_body in lx.read_value_list():
            self._assert_one(subject, code, value, annotation_body)

    def _decode_pairs(self, subject, lx: _Lexer) -> None:
        while not lx.at_end():
            code = lx.read_word()
            self._assert_property_pair(subject, code, lx)

    # -- inline nodes (Sec 9.6) -------------------------------------------

    def _decode_inline(self, body: str, parent: URIRef, code: str, matched_key: Optional[str]) -> URIRef:
        line_no = self._line_no
        lx = _Lexer(body.strip(), line_no)
        lx.skip_ws()
        explicit_id: Optional[str] = None
        if lx.peek_char() == "#":
            tok = lx.read_bare()
            explicit_id = tok[1:]
            if not explicit_id:
                raise self._error("empty explicit id '#' in inline node", code="core-empty-explicit-id-in-inline-node")

        if explicit_id is not None:
            node = self._resolve_identifier(explicit_id, line_no)
            self._assert_named_individual(node)
        else:
            node = self._mint(parent, code)

        if lx.at_end():
            return node

        next_word = lx.peek_word()
        if self._looks_like_typelist(next_word):
            type_list_token = lx.read_word()
            self._assert_type_list(node, type_list_token)
            self._maybe_decode_payload_prefix(node, lx)
            self._decode_pairs(node, lx)
        else:
            self._decode_positional(node, lx, code, matched_key)
        return node

    def _decode_positional(self, node: URIRef, lx: _Lexer, code: str, parent_matched_key: Optional[str]) -> None:
        form = cb.POSITIONAL_FORMS.get(code)
        if form is None:
            raise self._error(f"code {code!r} does not accept a positional inline node", code="core-code-does-not-accept-a-positional")
        if code == "tg":
            self._decode_positional_tg(node, lx)
        elif code == "pb":
            self._decode_positional_pb(node, lx)
        elif code == "pv":
            self._decode_positional_pv(node, lx, parent_matched_key)
        elif code == "hb":
            self._decode_positional_hb(node, lx)
        else:  # pragma: no cover -- exhaustive given cb.POSITIONAL_FORMS
            raise self._error(f"no positional decoder registered for {code!r}", code="core-no-positional-decoder-registered-for")
        self._decode_pairs(node, lx)

    def _decode_positional_tg(self, node: URIRef, lx: _Lexer) -> None:
        self._assert_type(node, "GT")
        mode_tok = lx.read_word()
        if mode_tok not in cb.TARGETING_MODE_CODE:
            raise self._error(f"unknown targeting mode {mode_tok!r} (expected one of c/o/s/n)", code="core-unknown-targeting-mode-expected-one-of")
        target_value = lx.read_value()
        target = self._resolve_value_as_identifier(target_value)
        target_code = cb.TARGETING_MODE_CODE[mode_tok]
        self.graph.add((node, self._resolve_curie(cb.PROPERTIES[target_code].curie), target))

    def _decode_positional_pb(self, node: URIRef, lx: _Lexer) -> None:
        self._assert_type(node, "GP")
        name_val = self._read_slot_or_skip(lx)
        type_tok = lx.read_word()
        if type_tok not in cb.PARAM_TYPE_WORD:
            raise self._error(f"unknown parameter type {type_tok!r}", code="core-unknown-parameter-type")
        value_val = self._read_slot_or_skip(lx)
        if name_val is not None:
            self.graph.add((node, MORK.paramName, self._literal_for_value(name_val, None)))
        self.graph.add((node, MORK.paramType, Literal(cb.PARAM_TYPE_WORD[type_tok])))
        if value_val is not None:
            self.graph.add((node, MORK.paramValue, self._literal_for_value(value_val, "*")))

    def _decode_positional_pv(self, node: URIRef, lx: _Lexer, parent_matched_key: Optional[str]) -> None:
        if parent_matched_key is None or parent_matched_key not in cb.PV_PROVENANCE_TYPE:
            raise self._error(
                "cannot determine the provenance node's type for positional 'pv': "
                "the parent subject's generative type (ShapeMapping/RuleMapping/"
                "TransformMapping/ProjectionMapping) could not be determined",
                code="core-cannot-determine-the-provenance-node-s",
            )
        self._assert_type(node, cb.PV_PROVENANCE_TYPE[parent_matched_key])
        creator = self._read_slot_or_skip(lx)
        model = self._read_slot_or_skip(lx)
        confidence = self._read_slot_or_skip(lx)
        status = self._read_slot_or_skip(lx)
        if creator is not None:
            self.graph.add((node, MORK.provenanceCreator, self._literal_for_value(creator, None)))
        if model is not None:
            self.graph.add((node, MORK.llmModelId, self._literal_for_value(model, None)))
        if confidence is not None:
            self.graph.add((node, MORK.llmConfidence, self._literal_for_value(confidence, "xsd:decimal")))
        if status is not None:
            self.graph.add((node, MORK.reviewStatus, self._literal_for_value(status, None)))

    def _decode_positional_hb(self, node: URIRef, lx: _Lexer) -> None:
        self._assert_type(node, "EB")
        name_val = self._read_slot_or_skip(lx)
        if name_val is not None:
            self.graph.add((node, MORK.placeholderName, self._literal_for_value(name_val, None)))
        span = self._read_expression_span(lx)
        expr_node = URIRef(f"{node}_e")
        resolved = _ExpressionParser(self, self._line_no).parse_into(expr_node, span)
        self.graph.add((node, MORK.placeholderExpression, resolved))

    # -- artefact payloads (Sec 9.8, 10.2-10.4) ---------------------------

    def _decode_artefact_payload(self, code: str, payload_text: str, subject: URIRef) -> URIRef:
        type_code = _ARTEFACT_PAYLOAD_CODES[code]
        node = self._mint(subject, code)
        self._decode_payload_onto(type_code, node, payload_text)
        if code == "gr":
            self.graph.add((subject, MORK.swrlCompactSyntax, Literal(payload_text)))
        return node

    def _decode_payload_onto(self, type_code: str, node: URIRef, payload_text: str) -> None:
        if type_code == "SW":
            self._add_type(node, SWRL.Imp, "swrl:Imp")
            _SwrlPayloadParser(self, node, self._line_no).parse(payload_text)
        elif type_code == "SH":
            self._add_type(node, SH.NodeShape, "sh:NodeShape")
            _ShaclPayloadParser(self, node, self._line_no, "bnode-shapes" in self.options).parse(payload_text)
        elif type_code == "TM":
            self._add_type(node, RR.TriplesMap, "rr:TriplesMap")
            _RmlPayloadParser(self, node, self._line_no).parse(payload_text)
        else:  # pragma: no cover
            raise self._error(f"no payload parser for type code {type_code!r}", code="core-no-payload-parser-for-type-code")

    _PAYLOAD_TYPE_CURIES = (("SW", "swrl:Imp"), ("SH", "sh:NodeShape"), ("TM", "rr:TriplesMap"))

    def _maybe_decode_payload_prefix(self, node: URIRef, lx: _Lexer) -> None:
        """D5.5 / Sec 9.6's typed-inline-node analogue: if ``node`` was
        just typed SW, SH or TM and the next token is a quoted string,
        that string is the artefact payload, decoded onto ``node`` itself
        (no minting) before any remaining 'code value' pairs are read."""
        types_here = self._subject_types.get(node, set())
        payload_type_code = None
        for code, curie in self._PAYLOAD_TYPE_CURIES:
            if curie in types_here:
                payload_type_code = code
                break
        if payload_type_code is None:
            return
        lx.skip_ws()
        if lx.peek_char() == '"':
            payload_value = lx.read_quoted()
            self._decode_payload_onto(payload_type_code, node, payload_value.text)

    # -- directives (Sec 6) ------------------------------------------------

    def _directive(self, line: str) -> None:
        m = re.match(r"@(\S+)\s*(.*)$", line)
        assert m is not None
        d, rest = m.group(1), m.group(2)
        handler = getattr(self, f"_directive_{d}", None)
        if handler is None:
            raise self._error(f"unknown directive '@{d}'", code="core-unknown-directive")
        handler(rest)

    def _directive_b(self, rest: str) -> None:
        self.base = str(self._parse_iri_literal(rest.strip()))

    def _directive_o(self, rest: str) -> None:
        parts = rest.split()
        if not parts:
            raise self._error("'@o' requires an ontology IRI", code="core-o-requires-an-ontology-iri")
        onto = self._parse_iri_literal(parts[0])
        self.ontology = onto
        self.graph.add((onto, RDF.type, OWL.Ontology))
        if len(parts) > 1:
            self.graph.add((onto, OWL.versionIRI, self._parse_iri_literal(parts[1])))
        for digest in self._pending_profile_hashes:
            self.graph.add((onto, MORK.inputHash, Literal(digest)))
        self._pending_profile_hashes = []

    def _directive_i(self, rest: str) -> None:
        if self.ontology is None:
            raise self._error("'@i' (imports) requires a preceding '@o'", code="core-i-imports-requires-a-preceding-o")
        for tok in rest.split(","):
            tok = tok.strip()
            if not tok:
                continue
            self.graph.add((self.ontology, OWL.imports, self._parse_iri_literal(tok)))

    def _directive_p(self, rest: str) -> None:
        name, sep, iri_text = rest.partition("=")
        name = name.strip()
        iri_text = iri_text.strip()
        if not sep or not name or not iri_text:
            raise self._error("malformed '@p' directive (expected '@p prefix=<iri>')", code="core-malformed-p-directive-expected-p-prefix")
        if name in cb.PREDECLARED_PREFIXES:
            raise self._error(f"cannot rebind predeclared prefix {name!r}", code="core-cannot-rebind-predeclared-prefix")
        resolved = self._parse_iri_literal(iri_text)
        self.prefixes[name] = str(resolved)
        self.graph.bind(name, Namespace(str(resolved)))

    def _directive_t(self, rest: str) -> None:
        name = rest.strip()
        if not name:
            raise self._error("'@t' requires a prefix name", code="core-t-requires-a-prefix-name")
        self.target_prefix = name

    def _directive_u(self, rest: str) -> None:
        name = rest.strip()
        if not name:
            raise self._error("'@u' requires a profile name", code="core-u-requires-a-profile-name")
        if name not in self.profiles:
            raise self._error(f"unknown profile {name!r} (none registered with this decode() call)", code="core-unknown-profile-none-registered-with-this")
        self._load_profile(self.profiles[name])

    def _directive_opt(self, rest: str) -> None:
        flags = rest.split()
        if not flags:
            raise self._error("'@opt' requires at least one flag", code="core-opt-requires-at-least-one-flag")
        self.options.update(flags)

    def _directive_v(self, rest: str) -> None:
        # Informational only for this decoder: it does not version-gate.
        pass

    def _load_profile(self, profile: Profile) -> None:
        if profile.base is not None:
            self.base = profile.base
        for name, iri in profile.prefixes.items():
            if name in cb.PREDECLARED_PREFIXES:
                raise self._error(f"profile {profile!r} rebinds predeclared prefix {name!r}", code="core-profile-rebinds-predeclared-prefix")
            self.prefixes[name] = iri
            self.graph.bind(name, Namespace(iri))
        if profile.target is not None:
            self.target_prefix = profile.target
        self.options.update(profile.options)
        digest = profile.content_hash()
        if self.ontology is not None:
            self.graph.add((self.ontology, MORK.inputHash, Literal(digest)))
        else:
            self._pending_profile_hashes.append(digest)

    # -- block headers (Sec 7, D4) ------------------------------------------

    def _block_header(self, line: str) -> None:
        m = re.match(r"(%[A-Z])\s*(.*)$", line)
        if not m:
            raise self._error(f"malformed block header {line!r}", code="core-malformed-block-header")
        kind, rest = m.group(1), m.group(2)
        if kind not in cb.BLOCKS:
            raise self._error(f"unknown block kind {kind!r}", code="core-unknown-block-kind")
        spec = cb.BLOCKS[kind]
        if kind == "%X":
            if rest.strip():
                raise self._error("unexpected content after '%X'", code="core-unexpected-content-after-x")
            self.block_membership = None
            self.block_scheme = None
            self.block_default_type = None
            return

        lx = _Lexer(rest, self._line_no)
        scheme_id = lx.read_word()
        scheme = self._resolve_identifier(scheme_id)
        self._assert_type(scheme, spec.scheme_type_code)

        if kind == "%R":
            lx.skip_ws()
            fmt_tok = lx.peek_bare() if lx.peek_char() not in ('"', "<", "[", "") else None
            if fmt_tok in cb.REPRESENTATION_FORMATS:
                lx.read_bare()
                self.graph.add((scheme, MORK["format"], self._resolve_identifier(fmt_tok)))

        self._decode_pairs(scheme, lx)

        self.block_membership = spec.membership_property
        self.block_scheme = scheme
        self.block_default_type = spec.default_type_code

    # -- node lines and expression lines (Sec 9, Sec 10.1, D5) --------------

    def _node_or_expr_line(self, line: str) -> None:
        lx = _Lexer(line, self._line_no)
        subject_tok = lx.read_word()
        subject = self._resolve_identifier(subject_tok)

        lx.skip_ws()
        if lx.peek_char() == "=" and (lx.i + 1 >= lx.n or lx.s[lx.i + 1] in " \t"):
            lx.i += 1
            remainder = lx.s[lx.i :].strip()
            self._assert_named_individual(subject)
            _ExpressionParser(self, self._line_no).parse_into(subject, remainder, is_root=True)
            return

        self._assert_named_individual(subject)

        next_word = lx.peek_word()
        if self._looks_like_typelist(next_word):
            type_list_token = lx.read_word()
            self._assert_type_list(subject, type_list_token)
        elif self.block_default_type is not None:
            self._assert_type(subject, self.block_default_type)

        if self.block_membership is not None and self.block_scheme is not None:
            membership_predicate = self._resolve_curie(self.block_membership)
            self.graph.add((subject, membership_predicate, self.block_scheme))

        self._maybe_decode_payload_prefix(subject, lx)
        self._decode_pairs(subject, lx)

    # -- axiom lines (Sec 11, D7) --------------------------------------------

    def _resolve_term(self, value: Value):
        if value.kind == "quoted":
            return self._literal_for_value(value, None)
        if value.kind == "iri":
            return URIRef(value.text)
        if value.kind == "bare":
            return self._resolve_identifier(value.text)
        raise self._error(f"cannot use a {value.kind} value as a raw-triple term", code="core-cannot-use-a-value-as-a")

    def _axiom_line(self, line: str) -> None:
        m = re.match(r"!([A-Za-z]+)\s*(.*)$", line)
        if not m:
            raise self._error(f"malformed axiom line {line!r}", code="core-malformed-axiom-line")
        kind, rest = m.group(1), m.group(2)
        handler = {
            "C": self._axiom_class,
            "O": self._axiom_object_property,
            "D": self._axiom_data_property,
            "A": self._axiom_annotation_property,
            "I": self._axiom_individual,
            "G": self._axiom_gci,
            "DC": self._axiom_all_disjoint_classes,
            "DP": self._axiom_all_disjoint_properties,
            "DI": self._axiom_all_different,
            "SA": self._axiom_pairwise_same_as,
            "T": self._axiom_raw_triple,
        }.get(kind)
        if handler is None:
            raise self._error(f"unknown axiom line kind '!{kind}'", code="core-unknown-axiom-line-kind")
        handler(rest)

    def _read_ident_list(self, rest: str) -> List[URIRef]:
        lx = _Lexer(rest, self._line_no)
        items = [self._resolve_value_as_identifier(lx.read_value())]
        while lx.peek_char() == ",":
            lx.i += 1
            items.append(self._resolve_value_as_identifier(lx.read_value()))
        if not lx.at_end():
            raise self._error("unexpected trailing content after identifier list", code="core-unexpected-trailing-content-after-identifier-list")
        if len(items) < 2:
            raise self._error("expected at least two comma-separated identifiers", code="core-expected-at-least-two-comma-separated")
        return items

    def _axiom_raw_triple(self, rest: str) -> None:
        lx = _Lexer(rest, self._line_no)
        s_val = lx.read_value()
        p_val = lx.read_value()
        o_val = lx.read_value()
        if not lx.at_end():
            raise self._error("'!T' takes exactly three terms (subject predicate object)", code="core-t-takes-exactly-three-terms-subject")
        self.graph.add((self._resolve_term(s_val), self._resolve_term(p_val), self._resolve_term(o_val)))

    def _axiom_all_disjoint_classes(self, rest: str) -> None:
        node = self._mint_bnode()
        self.graph.add((node, RDF.type, OWL.AllDisjointClasses))
        self.graph.add((node, OWL.members, self._rdf_list(self._read_ident_list(rest))))

    def _axiom_all_disjoint_properties(self, rest: str) -> None:
        node = self._mint_bnode()
        self.graph.add((node, RDF.type, OWL.AllDisjointProperties))
        self.graph.add((node, OWL.members, self._rdf_list(self._read_ident_list(rest))))

    def _axiom_all_different(self, rest: str) -> None:
        node = self._mint_bnode()
        self.graph.add((node, RDF.type, OWL.AllDifferent))
        self.graph.add((node, OWL.distinctMembers, self._rdf_list(self._read_ident_list(rest))))

    def _axiom_pairwise_same_as(self, rest: str) -> None:
        items = self._read_ident_list(rest)
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                self.graph.add((items[i], OWL.sameAs, items[j]))

    def _axiom_gci(self, rest: str) -> None:
        words = _split_top_level_words(rest)
        idx = None
        for i, w in enumerate(words):
            if w == "<":
                if idx is not None:
                    raise self._error("'!G' allows exactly one top-level '<' separator", code="core-g-allows-exactly-one-top-level")
                idx = i
        if idx is None:
            raise self._error("'!G' requires a top-level '<' separating two class expressions", code="core-g-requires-a-top-level-separating")
        left_text = " ".join(words[:idx])
        right_text = " ".join(words[idx + 1 :])
        if not left_text or not right_text:
            raise self._error("'!G' requires a class expression on both sides of '<'", code="core-g-requires-a-class-expression-on")
        left = _parse_class_expression(self, left_text, self._line_no)
        right = _parse_class_expression(self, right_text, self._line_no)
        self.graph.add((left, RDFS.subClassOf, right))

    # -- shared clause scanning for !C/!O/!D (Sec 11) ------------------------

    def _ce_words_balanced(self, toks: List[str]) -> bool:
        depth = 0
        for ch in " ".join(toks):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
        if depth != 0:
            return False
        return toks[-1] not in ("&", "|", "~", "^")

    def _consume_ce_clause_value(self, words: List[str], i: int) -> Tuple[str, int]:
        """Greedily consumes words[i:] into one class-expression clause
        value: at least one word, continuing across whitespace-separated
        '&'/'|' continuations until the accumulated text is a balanced,
        non-dangling expression (Sec 10.5's tight-binding restriction
        operators mean a legitimate multi-word CE only ever continues via
        a standalone '&' or '|' word)."""
        if i >= len(words):
            raise self._error("expected a class expression after clause keyword", code="core-expected-a-class-expression-after-clause")
        collected = [words[i]]
        i += 1
        while True:
            if self._ce_words_balanced(collected):
                if i < len(words) and words[i] in ("&", "|"):
                    collected.append(words[i])
                    i += 1
                    continue
                break
            if i >= len(words):
                raise self._error(f"unbalanced/incomplete class expression: {' '.join(collected)!r}", code="core-unbalanced-incomplete-class-expression")
            collected.append(words[i])
            i += 1
        return " ".join(collected), i

    def _scan_clauses(self, words: List[str], allowed_keywords: Set[str]) -> List[Tuple[str, str]]:
        clauses: List[Tuple[str, str]] = []
        i = 0
        n = len(words)
        while i < n:
            w = words[i]
            if w in allowed_keywords:
                i += 1
                if w in ("=", "<", "!", "dom", "rng"):
                    value_text, i = self._consume_ce_clause_value(words, i)
                elif w == "inv":
                    if i < n and words[i] == "^":
                        if i + 1 >= n:
                            raise self._error("'inv ^' requires a property identifier", code="core-inv-requires-a-property-identifier")
                        value_text = "^" + words[i + 1]
                        i += 2
                    else:
                        if i >= n:
                            raise self._error("'inv' requires a property identifier", code="core-inv-requires-a-property-identifier")
                        value_text = words[i]
                        i += 1
                elif w == "chain":
                    items = []
                    while True:
                        if i < n and words[i] == "^":
                            if i + 1 >= n:
                                raise self._error("'chain' has a dangling '^'", code="core-chain-has-a-dangling")
                            items.append("^" + words[i + 1])
                            i += 2
                        else:
                            if i >= n:
                                raise self._error("'chain' requires at least one property", code="core-chain-requires-at-least-one-property")
                            items.append(words[i])
                            i += 1
                        if i < n and words[i] == ",":
                            i += 1
                            continue
                        break
                    value_text = ",".join(items)
                else:  # pragma: no cover -- allowed_keywords is always a subset handled above
                    raise self._error(f"internal error: unhandled clause keyword {w!r}", code="core-internal-error-unhandled-clause-keyword")
                clauses.append((w, value_text))
                continue
            if _CHARACTERISTIC_FLAG_RE.match(w):
                clauses.append(("+flags", w))
                i += 1
                continue
            if i + 1 >= n:
                raise self._error(f"code {w!r} has no value", code="core-code-has-no-value")
            clauses.append((w, words[i + 1]))
            i += 2
        return clauses

    def _apply_generic_clause(self, subject, code: str, value_text: str) -> None:
        lx = _Lexer(value_text, self._line_no)
        self._assert_property_pair(subject, code, lx)
        if not lx.at_end():
            raise self._error(f"unexpected trailing content in clause {code!r}: {value_text!r}", code="core-unexpected-trailing-content-in-clause")

    def _axiom_class(self, rest: str) -> None:
        lx = _Lexer(rest, self._line_no)
        subject = self._resolve_identifier(lx.read_word())
        self.graph.add((subject, RDF.type, OWL.Class))
        words = _split_top_level_words(lx.s[lx.i :])
        for kw, value_text in self._scan_clauses(words, {"=", "<", "!"}):
            if kw == "=":
                self.graph.add((subject, OWL.equivalentClass, _parse_class_expression(self, value_text, self._line_no)))
            elif kw == "<":
                self.graph.add((subject, RDFS.subClassOf, _parse_class_expression(self, value_text, self._line_no)))
            elif kw == "!":
                self.graph.add((subject, OWL.disjointWith, _parse_class_expression(self, value_text, self._line_no)))
            else:
                self._apply_generic_clause(subject, kw, value_text)

    def _read_property_expression_subject(self, lx: _Lexer) -> URIRef:
        """The subject of an '!O' line may itself be a PE (Sec 10.5): a
        leading '^' names ObjectInverseOf(base) rather than a plain
        property, e.g. '!O ^compositeBroaderMapping < precedes' for
        Mork.ttl's Axiom P1 (SubObjectPropertyOf(ObjectInverseOf(...)))."""
        lx.skip_ws()
        if lx.peek_char() == "^":
            lx.i += 1
            base = self._resolve_identifier(lx.read_word())
            node = self._mint_bnode()
            self.graph.add((node, RDF.type, OWL.ObjectProperty))
            self.graph.add((node, OWL.inverseOf, base))
            return node
        return self._resolve_identifier(lx.read_word())

    def _axiom_object_property(self, rest: str) -> None:
        lx = _Lexer(rest, self._line_no)
        subject = self._read_property_expression_subject(lx)
        self.graph.add((subject, RDF.type, OWL.ObjectProperty))
        words = _split_top_level_words(lx.s[lx.i :])
        for kw, value_text in self._scan_clauses(words, {"=", "<", "inv", "dom", "rng", "chain"}):
            if kw == "<":
                self.graph.add((subject, RDFS.subPropertyOf, _parse_property_expression(self, value_text, self._line_no)))
            elif kw == "=":
                self.graph.add((subject, OWL.equivalentProperty, _parse_property_expression(self, value_text, self._line_no)))
            elif kw == "inv":
                self.graph.add((subject, OWL.inverseOf, _parse_property_expression(self, value_text, self._line_no)))
            elif kw == "dom":
                self.graph.add((subject, RDFS.domain, _parse_class_expression(self, value_text, self._line_no)))
            elif kw == "rng":
                self.graph.add((subject, RDFS.range, _parse_class_expression(self, value_text, self._line_no)))
            elif kw == "chain":
                props = [_parse_property_expression(self, t.strip(), self._line_no) for t in value_text.split(",")]
                self.graph.add((subject, OWL.propertyChainAxiom, self._rdf_list(props)))
            elif kw == "+flags":
                for flag in value_text[1:].split("+"):
                    self.graph.add((subject, RDF.type, _OBJECT_PROPERTY_CHARACTERISTICS[flag]))
            else:
                self._apply_generic_clause(subject, kw, value_text)

    def _axiom_data_property(self, rest: str) -> None:
        lx = _Lexer(rest, self._line_no)
        subject = self._resolve_identifier(lx.read_word())
        self.graph.add((subject, RDF.type, OWL.DatatypeProperty))
        words = _split_top_level_words(lx.s[lx.i :])
        for kw, value_text in self._scan_clauses(words, {"=", "<", "dom", "rng"}):
            if kw == "<":
                self.graph.add((subject, RDFS.subPropertyOf, self._resolve_identifier(value_text)))
            elif kw == "=":
                self.graph.add((subject, OWL.equivalentProperty, self._resolve_identifier(value_text)))
            elif kw == "dom":
                self.graph.add((subject, RDFS.domain, _parse_class_expression(self, value_text, self._line_no)))
            elif kw == "rng":
                self.graph.add((subject, RDFS.range, _parse_class_expression(self, value_text, self._line_no)))
            elif kw == "+flags":
                if value_text != "+F":
                    raise self._error(f"datatype property characteristic {value_text!r} is not supported (only +F)", code="core-datatype-property-characteristic-is-not-supported")
                self.graph.add((subject, RDF.type, OWL.FunctionalProperty))
            else:
                self._apply_generic_clause(subject, kw, value_text)

    def _axiom_annotation_property(self, rest: str) -> None:
        lx = _Lexer(rest, self._line_no)
        subject = self._resolve_identifier(lx.read_word())
        self.graph.add((subject, RDF.type, OWL.AnnotationProperty))
        words = _split_top_level_words(lx.s[lx.i :])
        i = 0
        n = len(words)
        while i < n:
            w = words[i]
            if w in ("<", "dom", "rng"):
                if i + 1 >= n:
                    raise self._error(f"{w!r} requires a value", code="core-requires-a-value")
                target = self._resolve_identifier(words[i + 1])
                pred = {"<": RDFS.subPropertyOf, "dom": RDFS.domain, "rng": RDFS.range}[w]
                self.graph.add((subject, pred, target))
                i += 2
            else:
                if i + 1 >= n:
                    raise self._error(f"code {w!r} has no value", code="core-code-has-no-value")
                self._apply_generic_clause(subject, w, words[i + 1])
                i += 2

    def _axiom_individual(self, rest: str) -> None:
        lx = _Lexer(rest, self._line_no)
        subject = self._resolve_identifier(lx.read_word())
        self._assert_named_individual(subject)
        lx.skip_ws()
        if lx.peek_char() == ":":
            lx.i += 1
            type_list_tok = lx.read_word()
            self._assert_type_list(subject, type_list_tok, allow_bare_local=True)
        self._decode_pairs(subject, lx)

    # -- @opt inv (Sec 5, D8) -------------------------------------------------

    def _materialize_inverses(self) -> None:
        inverse_uris: Dict[URIRef, URIRef] = {}
        for fwd_curie, inv_curie in cb.INVERSE_OF.items():
            inverse_uris[self._resolve_curie(fwd_curie)] = self._resolve_curie(inv_curie)
        additions = []
        for s, p, o in self.graph:
            inv_p = inverse_uris.get(p)
            if inv_p is not None and isinstance(o, (URIRef, BNode)):
                additions.append((o, inv_p, s))
        for triple in additions:
            self.graph.add(triple)

    # -- top-level driver (Sec 13, D1-D9) -------------------------------------

    @staticmethod
    def _assemble_logical_lines(text: str) -> List[Tuple[int, str]]:
        physical = text.split("\n")
        physical = [ln[:-1] if ln.endswith("\r") else ln for ln in physical]
        logical: List[Tuple[int, str]] = []
        for idx, raw in enumerate(physical, start=1):
            stripped = raw.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                continue
            if stripped.startswith(";"):
                if not logical:
                    raise McnSyntaxError("continuation line ';' with no preceding line", idx, raw, code="core-continuation-line-with-no-preceding-line")
                ln, prev = logical[-1]
                logical[-1] = (ln, prev + " " + stripped[1:].strip())
                continue
            logical.append((idx, raw))
        return logical

    def decode(self, text: str) -> Graph:
        for line_no, raw in self._assemble_logical_lines(text):
            self._line_no = line_no
            self._current_line_text = raw
            stripped = raw.strip()
            first = stripped[0]
            if first == "@":
                self._directive(stripped)
            elif first == "%":
                self._block_header(stripped)
            elif first == "!":
                self._axiom_line(stripped)
            else:
                self._node_or_expr_line(stripped)

        if "inv" in self.options:
            self._materialize_inverses()

        if "strict" in self.options:
            findings = lint(self.graph)
            if findings:
                summary = "; ".join(f"[{f.rule_id}] {f.subject}: {f.message}" for f in findings)
                raise McnLintError(f"'@opt strict': {len(findings)} lint finding(s) fired: {summary}", code="core-opt-strict-lint-finding-s-fired")

        return self.graph


# ---------------------------------------------------------------------------
# Sec 12.4 -- canonical decoding
# ---------------------------------------------------------------------------


def canonical_ntriples(graph: Graph) -> str:
    """The canonical decoding of a document (spec Sec 12.4): the N-Triples
    serialisation of the graph, one triple per line, sorted by the byte
    order of (subject, predicate, object), no trailing whitespace, with a
    final newline.

    rdflib's blank-node labels are its own internal identifiers rather
    than the "_:b1, _:b2, ..." labels a decoder assigns during its pass
    (Sec 12.3); since canonical N-Triples sorts by an *unlabelled*
    graph-isomorphism-independent key, we instead sort by a
    structure-based key so that two isomorphic graphs with different
    internal blank-node labels still produce the same output.
    """
    lines = []
    for s, p, o in graph:
        lines.append(_ntriples_line(s, p, o))
    lines.sort()
    return "\n".join(lines) + "\n" if lines else ""


def _ntriples_term(term) -> str:
    if isinstance(term, URIRef):
        return f"<{term}>"
    if isinstance(term, BNode):
        return f"_:{term}"
    if isinstance(term, Literal):
        text = str(term).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t")
        if term.language:
            return f'"{text}"@{term.language}'
        if term.datatype:
            return f'"{text}"^^<{term.datatype}>'
        return f'"{text}"'
    raise TypeError(f"unexpected RDF term type: {type(term)!r}")


def _ntriples_line(s, p, o) -> str:
    return f"{_ntriples_term(s)} {_ntriples_term(p)} {_ntriples_term(o)} ."


# ---------------------------------------------------------------------------
# Sec 14.2 -- lint rules
# ---------------------------------------------------------------------------


@dataclass
class LintFinding:
    """One Sec 14.2 lint rule firing against a decoded graph.

    ``severity`` is always "warning": every Sec 14.2 rule is advisory by
    spec design, and a document that trips one is only rejected outright
    under "@opt strict" (which raises McnLintError instead of returning
    findings -- see lint()'s caller in decode()). The field exists, fixed
    at "warning", so consumers built against the same
    kind/code/line/message/severity shape as McnSyntaxError.code (e.g. a
    pluggable Diagnostic adapter) don't need a special case for lint vs.
    decode-time failures. ``line`` is reserved for future source-position
    tracking -- lint runs on the decoded graph, which today carries no
    provenance back to the originating MCN line, so it is always None.
    """

    rule_id: str
    subject: URIRef
    message: str
    mirrors: str = ""
    severity: str = "warning"
    line: Optional[int] = None

    @property
    def code(self) -> str:
        """Alias for ``rule_id``, matching McnSyntaxError.code's name."""
        return self.rule_id


def lint(graph: Graph) -> List[LintFinding]:
    """Runs the Sec 14.2 lint rules against a decoded graph. These are
    heuristics that mirror Mork.ttl's GCIs and completeness axioms so a
    generator's mistakes surface cheaply; ontology/mork/shapes/constraints.ttl and
    an OWL reasoner remain the source of truth (Sec 14.3)."""
    findings: List[LintFinding] = []
    findings.extend(_lint_datum_without_deferred(graph))
    findings.extend(_lint_applicative_without_rbox(graph))
    findings.extend(_lint_aboxcat_composite_without_rbox(graph))
    findings.extend(_lint_rboxcat_composite_without_abox(graph))
    findings.extend(_lint_supersedes_without_effective_from(graph))
    findings.extend(_lint_generative_completeness(graph))
    findings.extend(_lint_transform_provenance(graph))
    findings.extend(_lint_targeting_spec_no_mode(graph))
    findings.extend(_lint_provenance_missing_creator_created(graph))
    findings.extend(_lint_shape_and_rule_together(graph))
    findings.extend(_lint_cn_and_ap_same_object(graph))
    findings.extend(_lint_governance_without_identity(graph))
    findings.extend(_lint_uncertain_without_hypothesis_or_recommendation(graph))
    return findings


def _subjects_of_type(graph: Graph, cls: URIRef):
    return set(graph.subjects(RDF.type, cls))


def _lint_datum_without_deferred(graph: Graph) -> List[LintFinding]:
    out = []
    for s in _subjects_of_type(graph, MORK.Datum):
        if (s, MORK.deferredMapping, None) not in graph:
            out.append(LintFinding("datum-without-deferred", s, "mork:Datum with no mork:deferredMapping", "Axiom 2.7a"))
    return out


def _lint_applicative_without_rbox(graph: Graph) -> List[LintFinding]:
    out = []
    for s in graph.subjects(MORK.broaderApplicative, None):
        if (s, MORK.exactRBoxMatch, None) not in graph and (s, MORK.inverseRBoxMatch, None) not in graph:
            out.append(LintFinding("applicative-without-rbox", s, "mork:broaderApplicative with no exactRBoxMatch/inverseRBoxMatch", "GCI 2.14a"))
    return out


def _lint_aboxcat_composite_without_rbox(graph: Graph) -> List[LintFinding]:
    out = []
    for s in graph.subjects(MORK.broadABoxCategoryMatch, None):
        if (s, MORK.compositeBroaderMapping, None) in graph:
            if (s, MORK.exactRBoxMatch, None) not in graph and (s, MORK.inverseRBoxMatch, None) not in graph:
                out.append(LintFinding("aboxcat-composite-without-rbox", s, "broadABoxCategoryMatch + compositeBroaderMapping with no exactRBoxMatch/inverseRBoxMatch", "GCI 2.14b"))
    return out


def _lint_rboxcat_composite_without_abox(graph: Graph) -> List[LintFinding]:
    out = []
    for s in graph.subjects(MORK.broadRBoxCategoryMatch, None):
        if (s, MORK.compositeBroaderMapping, None) in graph:
            if (s, MORK.exactABoxMatch, None) not in graph and (s, MORK.broadABoxCategoryMatch, None) not in graph:
                out.append(LintFinding("rboxcat-composite-without-abox", s, "broadRBoxCategoryMatch + compositeBroaderMapping with no exactABoxMatch/broadABoxCategoryMatch", "GCI 2.14d"))
    return out


def _lint_supersedes_without_effective_from(graph: Graph) -> List[LintFinding]:
    out = []
    for s in graph.subjects(MORK.supersedes, None):
        if (s, MORK.effectiveFrom, None) not in graph:
            out.append(LintFinding("supersedes-without-effective-from", s, "mork:supersedes with no mork:effectiveFrom", "GCI 5.10a"))
    return out


_GENERATIVE_PROVENANCE_PROPERTY = {
    MORK.ShapeMapping: MORK.hasConstraintProvenance,
    MORK.RuleMapping: MORK.hasRuleProvenance,
    MORK.ProjectionMapping: MORK.hasProjectionProvenance,
}


def _lint_generative_completeness(graph: Graph) -> List[LintFinding]:
    out = []
    for cls, provenance_prop in _GENERATIVE_PROVENANCE_PROPERTY.items():
        for s in _subjects_of_type(graph, cls):
            missing = []
            if (s, MORK.hasTargetingSpec, None) not in graph:
                missing.append("mork:hasTargetingSpec")
            if (s, MORK.hasParameterBinding, None) not in graph and (s, MORK.paramBinding, None) not in graph:
                missing.append("mork:hasParameterBinding")
            if (s, provenance_prop, None) not in graph:
                missing.append(str(provenance_prop))
            if missing:
                out.append(
                    LintFinding(
                        "generative-mapping-incomplete",
                        s,
                        f"{cls.split('#')[-1]} missing: {', '.join(missing)}",
                        "Sec 5.6 / Sec 6.13.6 completeness GCIs",
                    )
                )
    return out


def _lint_transform_provenance(graph: Graph) -> List[LintFinding]:
    out = []
    for s in _subjects_of_type(graph, MORK.TransformMapping):
        if (s, MORK.hasTransformProvenance, None) not in graph:
            out.append(LintFinding("transform-mapping-incomplete", s, "mork:TransformMapping with no mork:hasTransformProvenance", "TransformMapping completeness"))
    return out


def _lint_targeting_spec_no_mode(graph: Graph) -> List[LintFinding]:
    out = []
    modes = (SH.targetClass, SH.targetObjectsOf, SH.targetSubjectsOf, SH.targetNode)
    for s in _subjects_of_type(graph, MORK.TargetingSpec):
        if not any((s, m, None) in graph for m in modes):
            out.append(LintFinding("targeting-spec-no-mode", s, "mork:TargetingSpec with none of sh:targetClass/targetObjectsOf/targetSubjectsOf/targetNode", "Axiom 5.6h-i"))
    return out


_PROVENANCE_CLASSES = (MORK.ConstraintProvenance, MORK.RuleProvenance, MORK.TransformProvenance, MORK.ProjectionProvenance)


def _lint_provenance_missing_creator_created(graph: Graph) -> List[LintFinding]:
    out = []
    for cls in _PROVENANCE_CLASSES:
        for s in _subjects_of_type(graph, cls):
            missing = []
            if (s, MORK.provenanceCreator, None) not in graph:
                missing.append("mork:provenanceCreator")
            if (s, MORK.provenanceCreated, None) not in graph:
                missing.append("mork:provenanceCreated")
            if missing:
                out.append(LintFinding("provenance-incomplete", s, f"{cls.split('#')[-1]} missing: {', '.join(missing)}", "Axiom 6.13.7c"))
    return out


def _lint_shape_and_rule_together(graph: Graph) -> List[LintFinding]:
    out = []
    for s in graph.subjects(MORK.generatesShapeDefinition, None):
        if (s, MORK.generatesRuleDefinition, None) in graph:
            out.append(LintFinding("shape-and-rule-together", s, "both mork:generatesShapeDefinition and mork:generatesRuleDefinition on one subject", "ShapeMapping/RuleMapping disjointness"))
    return out


def _lint_cn_and_ap_same_object(graph: Graph) -> List[LintFinding]:
    out = []
    for s in graph.subjects(MORK.broaderApplicative, None):
        ap_targets = set(graph.objects(s, MORK.broaderApplicative))
        cn_targets = set(graph.objects(s, MORK.compositeNarrowerMapping))
        shared = ap_targets & cn_targets
        for t in shared:
            out.append(LintFinding("double-counted-edge", s, f"both compositeNarrowerMapping and broaderApplicative point at {t}", "loan example double-counting hazard"))
    return out


def _lint_governance_without_identity(graph: Graph) -> List[LintFinding]:
    out = []
    for s in graph.subjects(MORK.mappingScheme, None):
        states = list(graph.objects(s, FND.hasGovernanceState))
        if not states:
            continue
        if any(state != FND.Draft for state in states) and (s, FND.hasIdentity, None) not in graph:
            out.append(LintFinding("governance-without-identity", s, "governance state beyond fnd:Draft with no fnd:hasIdentity", "ADR-A22 production gate"))
    return out


def _lint_uncertain_without_hypothesis_or_recommendation(graph: Graph) -> List[LintFinding]:
    out = []
    for s in _subjects_of_type(graph, MORK.UncertainMapping):
        if (s, MORK.hypothesisMapping, None) not in graph and (s, MORK.mappingRecommendation, None) not in graph:
            out.append(LintFinding("uncertain-mapping-incomplete", s, "mork:UncertainMapping with neither hypothesisMapping nor mappingRecommendation", "UncertainMapping equivalence"))
    return out


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def decode(
    text: str,
    *,
    options: Optional[Iterable[str]] = None,
    profiles: Optional[Mapping[str, Profile]] = None,
    source_name: str = "<mcn>",
) -> Graph:
    """Decodes ``text`` (spec Sec 13) into a new rdflib Graph.

    ``options`` seeds the decoder's option set as though every flag had
    been given via an initial "@opt" directive (useful for forcing
    "strict" from calling code without editing the document).
    ``profiles`` is the registry an "@u" directive resolves against.
    """
    decoder = _Decoder(profiles=profiles)
    if options:
        decoder.options.update(options)
    try:
        return decoder.decode(text)
    except McnSyntaxError:
        raise
    except (KeyError, IndexError, ValueError, AssertionError) as exc:
        raise McnSyntaxError(
            f"internal parse failure: {exc}", decoder._line_no, decoder._current_line_text,
            code="core-internal-parse-failure",
        ) from exc
