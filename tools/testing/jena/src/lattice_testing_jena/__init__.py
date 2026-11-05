# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""An in-memory Apache Jena ARQ engine for tests, checks and benchmarks (ADR-A125).

It has the methods of ``lattice_testing_oxigraph.OxigraphStore``, so a suite that runs on Oxigraph runs on Jena by
changing the class. It is not a store SPI. The engine is ``platform/sparql-testkit``, a test-only Java program (the
pattern of ADR-A83's reasoning kit) that this module starts once per Python process and talks to over standard input
and output, one JSON request and one JSON answer per line. Build it with ``mise run bootstrap:sparql-testkit``. Where the
jar is missing or there is no ``java``, :func:`available` is false and callers skip. ``LATTICE_SPARQL_TESTKIT`` overrides
the jar's path, and ``LATTICE_SPARQL_TESTKIT_TIMEOUT`` (seconds, default 300) bounds one call, so a stalled JVM fails the
test instead of hanging the run. ``LATTICE_SPARQL_TESTKIT_JVM_OPTIONS`` replaces the JVM options.

One JVM serves every :class:`JenaStore` of the process, and each store has a dataset of its own in it, so two stores
never see each other's data. A call that exceeds the timeout kills the JVM, and a JVM that ends fails the call that finds it gone, since its datasets went
with it. The next call starts another, with every dataset empty.

Unlike ``OxigraphStore``, which speaks pyoxigraph terms, this speaks rdflib terms in and out: the engine is across a
text protocol, and rdflib's terms are what the callers already compare against.

The compiler leaves the caller's parameters as ``$name`` variables. :meth:`JenaStore.update` and the queries fill each
by putting its term text in the query, as ``OxigraphStore`` does, so the two engines see the same text. Jena has an
initial-binding API and this does not use it, since a caller with only a SPARQL endpoint would not have it either.
"""

from __future__ import annotations

import atexit
import json
import os
import queue
import re
import shlex
import shutil
import subprocess
import tempfile
import threading
import weakref
from pathlib import Path
from typing import Iterable, Mapping, NamedTuple

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import XSD

Term = URIRef | Literal | BNode

TIMEOUT = int(os.environ.get("LATTICE_SPARQL_TESTKIT_TIMEOUT", "300"))
JAR_RELATIVE = Path("platform/sparql-testkit/target/sparql-testkit.jar")


class JenaError(RuntimeError):
    """The engine refused a request (a parse or evaluation error), or the process could not answer it."""


def jar() -> Path:
    """The testkit jar. ``LATTICE_SPARQL_TESTKIT`` first, then the repository's build output, found as the catalogue reader
    finds the root (``LATTICE_ROOT``, then the nearest directory at or above the working directory that holds
    ``repository-catalogue.md``), never from this file's location (STD-273)."""
    if os.environ.get("LATTICE_SPARQL_TESTKIT"):
        return Path(os.environ["LATTICE_SPARQL_TESTKIT"])
    if os.environ.get("LATTICE_ROOT"):
        return Path(os.environ["LATTICE_ROOT"]) / JAR_RELATIVE
    here = Path.cwd().resolve()
    for candidate in (here, *here.parents):
        if (candidate / "repository-catalogue.md").is_file():
            return candidate / JAR_RELATIVE
    return here / JAR_RELATIVE


def available() -> bool:
    return jar().is_file() and shutil.which("java") is not None


def jvm_options() -> list[str]:
    """The reasoning kit's options (ADR-A83): a class-data archive beside the jar, built by the JVM on first use, a serial
    collector and C1-only compilation. Logging is off so that a stale archive or an unwritable directory just runs without it."""
    override = os.environ.get("LATTICE_SPARQL_TESTKIT_JVM_OPTIONS")
    if override is not None:
        return shlex.split(override)
    return ["-XX:+AutoCreateSharedArchive", f"-XX:SharedArchiveFile={jar().with_suffix('.jsa')}", "-XX:+UseSerialGC", "-XX:TieredStopAtLevel=1", "-Xlog:disable"]


class _Server:
    """One testkit JVM running ``serve``, started on first use. Calls are serialised by a lock."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._process: subprocess.Popen | None = None
        self._lines: queue.Queue | None = None
        self._stderr = None
        self.starts = 0

    def _start(self) -> None:
        if not available():
            raise JenaError(f"the SPARQL testkit is not built ({jar()}): run mise run bootstrap:sparql-testkit")
        self._stderr = tempfile.TemporaryFile()
        self._process = subprocess.Popen(
            ["java", *jvm_options(), "-jar", str(jar()), "serve"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self._stderr, text=True, encoding="utf-8", bufsize=1)
        self._lines = lines = queue.Queue()
        self.starts += 1

        def pump(stream=self._process.stdout) -> None:
            for line in stream:
                lines.put(line)
            lines.put(None)

        threading.Thread(target=pump, daemon=True).start()

    def _stderr_tail(self) -> str:
        try:
            self._stderr.seek(0)
            return self._stderr.read().decode(errors="replace")[-2000:]
        except (OSError, ValueError, AttributeError):
            return ""

    def _discard(self) -> None:
        process, self._process = self._process, None
        if process is not None:
            if process.poll() is None:
                process.kill()
            process.wait()
            for stream in (process.stdin, process.stdout):
                try:
                    stream.close()
                except OSError:
                    pass

    def ask(self, request: dict):
        line = json.dumps(request)
        with self._lock:
            if self._process is not None and self._process.poll() is not None:
                # every dataset went with it, so say so rather than answer from an empty one
                detail = self._stderr_tail()
                self._discard()
                raise JenaError(f"the SPARQL testkit ended before {request['op']}, and its datasets with it: {detail}")
            if self._process is None:
                self._start()
            try:
                self._process.stdin.write(line + "\n")
                self._process.stdin.flush()
                answer = self._lines.get(timeout=TIMEOUT)
            except queue.Empty:
                self._discard()
                raise JenaError(f"the SPARQL testkit did not answer {request['op']} in {TIMEOUT}s") from None
            except OSError:
                answer = None
            if answer is None:
                detail = self._stderr_tail()
                self._discard()
                raise JenaError(f"the SPARQL testkit ended while answering {request['op']}: {detail}")
            answer = json.loads(answer)
            if "error" in answer:
                raise JenaError(answer["error"])
            return answer

    def stop(self) -> None:
        """Ends the JVM by closing its standard input, which lets it write its class-data archive."""
        with self._lock:
            process = self._process
            if process is None:
                return
            try:
                process.stdin.close()
                process.wait(timeout=30)
            except (OSError, subprocess.TimeoutExpired):
                pass
            self._discard()


_SERVER = _Server()
atexit.register(_SERVER.stop)
_COUNTER = iter(range(1, 1 << 62))


def _drop(name: str) -> None:
    try:
        if _SERVER._process is not None:
            _SERVER.ask({"op": "drop", "dataset": name})
    except Exception:  # a finaliser must not raise
        pass


def iri(value: str) -> URIRef:
    return URIRef(value)


def literal(value, datatype: str | None = None) -> Literal:
    """A literal. An int gets ``xsd:integer`` unless a datatype is given."""
    if datatype is None and isinstance(value, int) and not isinstance(value, bool):
        datatype = str(XSD.integer)
    return Literal(str(value), datatype=URIRef(datatype)) if datatype else Literal(str(value))


def bind_parameters(text: str, parameters: Mapping[str, Term], strict: bool = True) -> str:
    """Replace each ``$name`` and ``?name`` for the given parameters with its term as SPARQL text.

    SPARQL treats ``$x`` and ``?x`` as one variable, so both spellings are replaced. With ``strict`` a parameter that
    never appears in the text is an error, since a misspelt name would otherwise leave the real variable silently
    unbound. The substitution is textual and does not look inside string literals, IRIs or comments."""
    if not parameters:
        return text
    pattern = re.compile(r"[$?](%s)\b" % "|".join(re.escape(n) for n in parameters))
    used: set[str] = set()

    def substitute(match: re.Match) -> str:
        used.add(match.group(1))
        return parameters[match.group(1)].n3()

    bound = pattern.sub(substitute, text)
    if strict and (missing := sorted(set(parameters) - used)):
        raise ValueError(f"parameter(s) {', '.join(missing)} do not appear in the update")
    return bound


def from_json(term: Mapping) -> Term:
    """One term of a SPARQL 1.1 JSON result as the rdflib term."""
    kind, value = term["type"], term["value"]
    if kind == "uri":
        return URIRef(value)
    if kind == "bnode":
        return BNode(value)
    if "xml:lang" in term:
        return Literal(value, lang=term["xml:lang"])
    if term.get("datatype") and term["datatype"] != str(XSD.string):
        return Literal(value, datatype=URIRef(term["datatype"]))
    return Literal(value)


def _nquads(term: Term) -> str:
    """A term as N-Quads text. rdflib's ``n3()`` writes a multi-line literal in triple quotes, which N-Quads does not allow."""
    if not isinstance(term, Literal):
        return term.n3()
    text = '"' + str(term).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r") + '"'
    if term.language:
        return f"{text}@{term.language}"
    return f"{text}^^<{term.datatype}>" if term.datatype else text


class Quad(NamedTuple):
    subject: Term
    predicate: Term
    object: Term
    graph: Term | None
    """The graph's name, or None for the default graph."""


class JenaStore:
    """An in-memory quad store that runs SPARQL 1.1 Update and Query on Jena ARQ."""

    def __init__(self) -> None:
        self.name = f"store-{next(_COUNTER)}"
        _SERVER.ask({"op": "reset", "dataset": self.name})  # starts the JVM, so a missing jar fails here
        self._finalizer = weakref.finalize(self, _drop, self.name)

    def close(self) -> None:
        self._finalizer()

    def __enter__(self) -> "JenaStore":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def _ask(self, op: str, **fields):
        return _SERVER.ask({"op": op, "dataset": self.name, **fields})

    def load(self, data: str, format: str = "nquads") -> None:
        """N-Quads or TriG text, in one write transaction. A blank node label is the same node in every load."""
        self._ask("load", format=format, data=data)

    def add(self, subject: Term, predicate: Term, obj: Term, graph: Term | None = None) -> None:
        """Add one quad. ``graph=None`` is the default graph."""
        self.add_all([(subject, predicate, obj, graph)])

    def add_all(self, quads: Iterable[tuple]) -> None:
        lines = []
        for subject, predicate, obj, *rest in quads:
            graph = rest[0] if rest else None
            lines.append(" ".join([_nquads(subject), _nquads(predicate), _nquads(obj), *([_nquads(graph)] if graph is not None else []), "."]))
        if lines:
            self.load("\n".join(lines) + "\n")

    def reset(self) -> None:
        """Remove every quad of every graph."""
        self._ask("reset")

    def remove_graph(self, graph: Term | None) -> None:
        """Remove every quad of one graph (``None`` for the default graph)."""
        self.update("CLEAR DEFAULT" if graph is None else f"CLEAR GRAPH {graph.n3()}")

    def update(self, text: str, parameters: Mapping[str, Term] | None = None, strict: bool = True) -> None:
        """A SPARQL 1.1 update request, in one write transaction, so one that fails leaves the dataset as it was."""
        self._ask("update", text=bind_parameters(text, parameters or {}, strict))

    def _query(self, text: str, parameters: Mapping[str, Term] | None):
        return self._ask("query", text=bind_parameters(text, parameters or {}))

    def solutions(self, text: str, parameters: Mapping[str, Term] | None = None) -> tuple[list[str], list[dict[str, Term]]]:
        """The variables of a SELECT in the order it names them, and its solutions, each a dict of the variables it binds."""
        answer = self._query(text, parameters)
        if answer["form"] != "select":
            raise JenaError(f"select was given a {answer['form']} query")
        result = answer["result"]
        return result["head"]["vars"], [{name: from_json(value) for name, value in binding.items()} for binding in result["results"]["bindings"]]

    def select(self, text: str, parameters: Mapping[str, Term] | None = None) -> list[dict[str, Term]]:
        """The solutions of a SELECT, each as a dict of the variables it binds. An unbound variable is absent."""
        return self.solutions(text, parameters)[1]

    def ask(self, text: str, parameters: Mapping[str, Term] | None = None) -> bool:
        answer = self._query(text, parameters)
        if answer["form"] != "ask":
            raise JenaError(f"ask was given a {answer['form']} query")
        return answer["result"]["boolean"]

    def construct(self, text: str, parameters: Mapping[str, Term] | None = None) -> Graph:
        """The graph a CONSTRUCT or DESCRIBE returns."""
        answer = self._query(text, parameters)
        if answer["form"] != "graph":
            raise JenaError(f"construct was given a {answer['form']} query")
        return Graph().parse(data=answer["result"], format="nt")

    def quads(self, graph: Term | None = None, default: bool = False) -> list[Quad]:
        """Every quad, or those in one named graph, or with ``default=True`` those in the default graph."""
        pattern = "{ ?s ?p ?o BIND(<urn:x-lattice:none> AS ?g) } UNION { GRAPH ?g { ?s ?p ?o } }"
        if default:
            pattern = "{ ?s ?p ?o BIND(<urn:x-lattice:none> AS ?g) }"
        elif graph is not None:
            pattern = f"{{ GRAPH {graph.n3()} {{ ?s ?p ?o }} BIND({graph.n3()} AS ?g) }}"
        rows = self.select(f"SELECT ?s ?p ?o ?g WHERE {{ {pattern} }}")
        return [Quad(r["s"], r["p"], r["o"], None if r["g"] == URIRef("urn:x-lattice:none") else r["g"]) for r in rows]

    def count(self, predicate: str, graph: Term | None = None) -> int:
        return sum(1 for q in self.quads(graph) if str(q.predicate) == predicate)


__all__ = ["JenaStore", "JenaError", "Quad", "available", "jar", "bind_parameters", "from_json", "iri", "literal", "Term"]
