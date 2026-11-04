# SPDX-License-Identifier: MPL-2.0
"""The JOLT backend (ADR-A148 decision 4): a plan over a JSON source as a chain of four JOLT operations whose output is
expanded JSON-LD.

1. A `shift` builds each node object where it will sit in the output, a root's under `r<n>` and a child's beneath its
   parent under the glue property, or under `@reverse` when the child is the subject. Each value is a value object, and
   the keys and positions an identity reads are kept in temporary keys `_k<n>` and `_p`.
2. A `modify-overwrite-beta` forms each node's `@id` from them with `concat`.
3. A `remove` takes the temporary keys away.
4. A `shift` gathers the roots' nodes under `@graph`.

JOLT reads `.`, `#`, `$`, `&`, `@`, `*`, `[`, `]` and `|` in a key as its own syntax, so every text from a mapping or a
source is escaped with a backslash. A value is written as JSON-LD reads it, so a JSON number is an xsd:integer or an
xsd:double, and a JSON boolean an xsd:boolean, where the XSLT backend writes the text of an XML value as a string."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Optional

from rdflib import Literal, URIRef
from rdflib.namespace import XSD

from mork_rdf.model import Finding, Severity

from .paths import SourcePath
from .plan import Constant, Datum, Plan, Positional, Ref, Table

_SPECIAL = re.compile(r"([\\.#$&@*\[\]|])")
_UNSAFE_IN_CONCAT = re.compile(r"[',()@=]")


def esc(text: str) -> str:
    return _SPECIAL.sub(r"\\\1", text)


class _Refusal(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


@dataclass
class _Node:
    """A datum's node objects: where its element is matched in the shift, and where it is written."""

    datum: Datum
    parent: Optional["_Node"]
    loc: list                 # the shift's keys to the element
    star: Optional[int]       # the depth of the `*` that matches each element, None when one element only
    keys: list                # the output keys from the parent's node object to this node's array, escaped
    raw: list                 # the same keys as `remove` matches them, unescaped
    used: set = field(default_factory=set)  # (reverse, property) already written on the node

    def index(self, depth: int) -> str:
        return f"[&{depth - self.star}]" if self.star is not None else "[0]"


class _Writer:
    def __init__(self, plan: Plan):
        self.plan = plan
        self.shift: dict = {}
        self.modify: dict = {}
        self.remove: dict = {}
        self.findings: list[Finding] = []

    # --- the shift's tree --------------------------------------------------------------------------------------------

    def put(self, keys: list, rhs: str) -> None:
        """Adds an output path for what `keys` matches. A matched value copied where its key also descends is written
        with JOLT's `@`."""
        node = self.shift
        for key in keys[:-1]:
            node = node.setdefault(key, {})
        last = keys[-1]
        if last.startswith(("#", "$")):
            node.setdefault(last, []).append(rhs)
        else:
            node.setdefault(last, {}).setdefault("@", []).append(rhs)

    @staticmethod
    def rendered(node):
        if isinstance(node, list):
            return node[0] if len(node) == 1 else node
        # A copied value keeps JOLT's `@`, which counts as a level, as every `&` this writer forms assumes.
        return {k: _Writer.rendered(v) for k, v in node.items()}

    def out(self, node: _Node, depth: int, *tail: str) -> str:
        """The output path of `node` for an output path written at shift depth `depth`, with `tail` beneath it."""
        text = ".".join(".".join(step.keys) + step.index(depth) for step in reversed(_chain(node)))
        return ".".join([text, *tail]) if tail else text

    # --- walking the plan --------------------------------------------------------------------------------------------

    def steps(self, path: SourcePath, start: list) -> tuple[list, Optional[int]]:
        keys, star = list(start), None
        for step in path.steps:
            if step.kind == "each":
                if star is not None:
                    raise _Refusal("PathNotCarried", f"{path.text!r} iterates twice, and a JOLT chain carries one [*] for each datum or value")
                keys.append("*")
                star = len(keys)
            else:
                keys.append(esc(step.name))
        return keys, star

    def datum(self, datum: Datum, parent: Optional[_Node], root: int) -> None:
        if parent is None:
            loc, star = self.steps(datum.path, [])
            node = _Node(datum, None, loc, star, ["r%d" % root], ["r%d" % root])
        else:
            if datum.glue is None:
                raise _Refusal("NoGlue", "a child datum is written beneath its parent in JSON-LD, so it names the property that joins them")
            prop, parent_is_subject = datum.glue
            key = (not parent_is_subject, str(prop))
            if key in parent.used:
                raise _Refusal("SharedProperty", f"another mapping writes {prop.n3()} on the same node, which this backend does not merge")
            parent.used.add(key)
            if datum.path is None:
                loc, star = list(parent.loc), None
            else:
                if datum.path.absolute:
                    raise _Refusal("PathNotCarried", "a child's path starts at its parent's focus")
                loc, star = self.steps(datum.path, parent.loc)
            reverse = [] if parent_is_subject else ["@reverse"]
            node = _Node(datum, parent, loc, star, [esc(k) for k in reverse] + [esc(str(prop))], reverse + [str(prop)])
        depth = len(loc)
        if node.star is not None:
            self.put(loc + ["$"], self.out(node, depth + 1, "_p"))
        for t in datum.types:
            self.put(loc + ["#" + esc(str(t))], self.out(node, depth + 1, "\\@type[]"))
        self.identity(node)
        if node.star is not None:
            self.at(self.remove, node)["_p"] = ""
        for assertion in datum.assertions:
            try:
                self.assertion(node, assertion)
            except _Refusal as refusal:
                self.findings.append(Finding(refusal.code, assertion.mapping, refusal.message))
        for child in datum.children:
            try:
                self.datum(child, node, root)
            except _Refusal as refusal:
                self.findings.append(Finding(refusal.code, child.mapping, refusal.message))

    def value(self, node: _Node, ref: SourcePath) -> tuple[list, Optional[int]]:
        if ref.absolute:
            raise _Refusal("PathNotCarried", f"{ref.text!r} starts at the document, and a JOLT chain reads a value from its focus")
        return self.steps(ref, node.loc)

    def identity(self, node: _Node) -> None:
        identity = node.datum.identity
        depth = len(node.loc)
        if isinstance(identity, Constant):
            self.put(node.loc + ["#" + esc(str(identity.term))], self.out(node, depth + 1, "\\@id"))
            return
        pieces = []
        if isinstance(identity, Positional):
            pieces.append(self.literal(identity.prefix, node))
            segments = []
            for ancestor in _chain(node):
                parts = []
                for step in (ancestor.datum.path.steps if ancestor.datum.path is not None else ()):
                    parts.append(f"@({self.up(node, ancestor)},_p)" if step.kind == "each" else self.literal(step.name, node))
                segments = parts + segments
            pieces += [p for i, s in enumerate(segments) for p in ((self.literal("/", node),) if i else ()) + (s,)]
        else:
            for n, piece in enumerate(identity.pieces):
                if isinstance(piece, str):
                    pieces.append(self.literal(piece, node))
                    continue
                keys, star = self.value(node, piece.path)
                if star is not None:
                    raise _Refusal("PathNotCarried", f"{piece.path.text!r} reads several values, and an identity reads one")
                self.put(keys, self.out(node, len(keys) + 1, f"_k{n}"))
                pieces.append(f"@(1,_k{n})")
                if piece.encode:
                    self.findings.append(Finding("KeyNotEncoded", node.datum.mapping, f"JOLT has no URI encoding, so the value {piece.path.text!r} reads is written into the IRI as it is", Severity.WARNING))
        self.at(self.modify, node)["\\@id"] = "=concat(" + ", ".join(pieces) + ")"
        for n, piece in enumerate(getattr(identity, "pieces", ())):
            if not isinstance(piece, str):
                self.at(self.remove, node)[f"_k{n}"] = ""

    def literal(self, text: str, node: _Node) -> str:
        if _UNSAFE_IN_CONCAT.search(text):
            raise _Refusal("LiteralNotCarried", f"{text!r} holds a character JOLT's concat cannot take in a literal")
        return f"'{text}'"

    @staticmethod
    def up(node: _Node, ancestor: _Node) -> int:
        """How many levels `@(n, key)` climbs from inside `node`'s object to `ancestor`'s."""
        levels, n = 1, node
        while n is not ancestor:
            levels += len(n.keys) + 1
            n = n.parent
        return levels

    def at(self, tree: dict, node: _Node) -> dict:
        """The spec object for `node`'s objects in `modify`, whose keys are escaped, or in `remove`, whose keys are not."""
        raw = tree is self.remove
        for step in reversed(_chain(node)):
            for key in (step.raw if raw else step.keys):
                tree = tree.setdefault(key, {})
            tree = tree.setdefault("*", {})
        return tree

    def assertion(self, node: _Node, assertion) -> None:
        key = (assertion.inverse, str(assertion.prop))
        if key in node.used:
            raise _Refusal("SharedProperty", f"another mapping writes {assertion.prop.n3()} on the same node, which this backend does not merge")
        node.used.add(key)
        prop = ("\\@reverse." if assertion.inverse else "") + esc(str(assertion.prop))
        depth, value = len(node.loc), assertion.value
        if isinstance(value, Constant):
            term = value.term
            if isinstance(term, URIRef):
                self.put(node.loc + ["#" + esc(str(term))], self.out(node, depth + 1, prop + "[0]", "\\@id"))
                return
            self.put(node.loc + ["#" + esc(str(term))], self.out(node, depth + 1, prop + "[0]", "\\@value"))
            if term.language:
                self.put(node.loc + ["#" + esc(term.language)], self.out(node, depth + 1, prop + "[0]", "\\@language"))
            elif term.datatype is not None and term.datatype != XSD.string:
                self.put(node.loc + ["#" + esc(str(term.datatype))], self.out(node, depth + 1, prop + "[0]", "\\@type"))
            return
        keys, star = self.value(node, value.path)
        index = (lambda d: f"[&{d - star}]") if star is not None else (lambda d: "[0]")
        if isinstance(value, Ref):
            self.put(keys, self.out(node, len(keys) + 1, prop + index(len(keys) + 1), "\\@value"))
            return
        for source, target in value.rows:
            d = len(keys) + 2
            self.put(keys + [esc(source), "#" + esc(str(target))], self.out(node, d, prop + index(d), "\\@id"))

    def chain(self) -> list:
        for n, datum in enumerate(self.plan.roots):
            try:
                self.datum(datum, None, n)
            except _Refusal as refusal:
                self.findings.append(Finding(refusal.code, datum.mapping, refusal.message))
        ops = [{"operation": "shift", "spec": self.rendered(self.shift)}]
        if self.modify:
            ops.append({"operation": "modify-overwrite-beta", "spec": self.modify})
        if self.remove:
            ops.append({"operation": "remove", "spec": self.remove})
        ops.append({"operation": "shift", "spec": {k: {"*": "\\@graph[]"} for k in self.shift_roots()}})
        return ops

    def shift_roots(self) -> list:
        return [f"r{n}" for n in range(len(self.plan.roots))]


def _chain(node: Optional[_Node]) -> list:
    """The node and its ancestors, the node first."""
    out = []
    while node is not None:
        out.append(node)
        node = node.parent
    return out


def compile_jolt(plan: Plan) -> tuple[str, tuple[Finding, ...]]:
    """The chain of a plan whose source is JSON, as JSON text, and what the backend found it cannot carry."""
    if plan.format != "json":
        raise ValueError("the JOLT backend reads a plan over a JSON source")
    writer = _Writer(plan)
    ops = writer.chain()
    return json.dumps(ops, indent=1, sort_keys=True), tuple(sorted(set(writer.findings)))
