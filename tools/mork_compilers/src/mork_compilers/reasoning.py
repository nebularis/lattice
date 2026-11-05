# SPDX-License-Identifier: MPL-2.0

"""
Calls the test-only reasoning harness (ADR-A83), ``platform/reasoning-testkit``,
as a subprocess. No reasoner is a dependency of this package: build the jar
with ``mise run bootstrap:reasoning-testkit``, and callers skip when
``available()`` is false. ``LATTICE_REASONING_TESTKIT`` overrides the jar path.
``LATTICE_REASONING_TIMEOUT`` (seconds, default 300) bounds one call, so a stalled JVM fails
the test instead of hanging the run (TD-31).

Each call starts a JVM, and for the closures the tests send, starting it and loading the OWL API
and HermiT classes is about half of a call. ``jvm_options`` shortens that with a class-data
archive that the JVM builds beside the jar on first use, a serial collector, and C1-only
compilation. Over 41 closures from the ontology tests that took 51.8s to 29.9s. The archive
is rebuilt by the JVM when the jar changes. ``LATTICE_REASONING_JVM_OPTIONS`` replaces the
options, for example with an empty string to run the JVM with its defaults.

Starting the JVM is still paid once per call, so by default one JVM is kept per Python process
and sent each call as a line on its standard input (the testkit's ``serve`` command). It holds the
reasoners for its last four distinct closures, by file content, so several questions about one
closure load and classify it once. The JVM ends with the process, or when its standard input is
closed. A call that exceeds ``TIMEOUT`` kills it, and the next call starts another.
``LATTICE_REASONING_SERVER=0`` runs a JVM per call as before. A jar built before ``serve`` existed,
or a JVM that ends before answering its first call, makes the process fall back to a JVM per call.
"""

from __future__ import annotations

import atexit
import json
import os
import queue
import shlex
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Iterable

from rdflib import BNode, Graph
from rdflib.namespace import RDF

from .namespaces import SWRL

JAR = Path(os.environ.get(
    "LATTICE_REASONING_TESTKIT",
    Path(__file__).resolve().parents[4] / "platform/reasoning-testkit/target/reasoning-testkit.jar",
))


TIMEOUT = int(os.environ.get("LATTICE_REASONING_TIMEOUT", "300"))


def jvm_options() -> list[str]:
    """JVM startup options for one testkit call. The archive sits beside the jar, in a
    directory that is build output. Logging is off so that a missing or stale archive, or an
    unwritable directory, does not print anything and the call simply runs without it."""
    override = os.environ.get("LATTICE_REASONING_JVM_OPTIONS")
    if override is not None:
        return shlex.split(override)
    return [
        "-XX:+AutoCreateSharedArchive",
        f"-XX:SharedArchiveFile={JAR.with_suffix('.jsa')}",
        "-XX:+UseSerialGC",
        "-XX:TieredStopAtLevel=1",
        "-Xlog:disable",
    ]


def server_enabled() -> bool:
    """Whether calls go to a long-running JVM. Read on each call, so a test can change it."""
    return os.environ.get("LATTICE_REASONING_SERVER", "1") != "0"


class _ServerUnavailable(Exception):
    """The long-running JVM did not start, or ended before it answered anything."""


class _Server:
    """One testkit JVM running ``serve``, started on first use and sent one request line at a time.

    A request is the command, its IRIs and the closure's file, separated by tabs. An answer is one
    line of JSON. The JVM's standard error goes to a temporary file, for the message of a call that
    fails. Calls are serialised by a lock, since a JVM answers one at a time."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._process: subprocess.Popen | None = None
        self._lines: queue.Queue | None = None
        self._stderr = None
        self._answered = False
        self.unavailable = False

    def _start(self) -> None:
        self._stderr = tempfile.TemporaryFile()
        self._process = subprocess.Popen(
            ["java", *jvm_options(), "--sun-misc-unsafe-memory-access=allow", "-jar", str(JAR), "serve"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self._stderr, text=True, encoding="utf-8", bufsize=1)
        self._lines = lines = queue.Queue()
        self._answered = False

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
        if process is not None and process.poll() is None:
            process.kill()
        if process is not None:
            process.wait()
            for stream in (process.stdin, process.stdout):
                try:
                    stream.close()
                except OSError:
                    pass

    def ask(self, command: str, iris: tuple[str, ...], path: Path):
        fields = [command, *iris, str(path)]
        if any(c in field for field in fields for c in "\t\r\n"):
            raise _ServerUnavailable("an argument holds a tab or a line break")
        shown = " ".join(["reasoning-testkit", *fields])
        with self._lock:
            if self._process is None or self._process.poll() is not None:
                self._discard()
                self._start()
            try:
                self._process.stdin.write("\t".join(fields) + "\n")
                self._process.stdin.flush()
                line = self._lines.get(timeout=TIMEOUT)
            except queue.Empty:
                self._discard()
                raise subprocess.TimeoutExpired(shown, TIMEOUT) from None
            except OSError:
                line = None
            if line is None:
                detail = self._stderr_tail()
                first = not self._answered
                self._discard()
                if first:
                    self.unavailable = True
                    raise _ServerUnavailable(detail)
                raise subprocess.CalledProcessError(1, shown, stderr=detail)
            self._answered = True
            answer = json.loads(line)
            if "error" in answer:
                raise subprocess.CalledProcessError(1, shown, stderr=answer["error"])
            return answer["result"]

    def stop(self) -> None:
        """Ends the JVM by closing its standard input, which lets it write its class-data archive,
        and kills it if it has not ended after 30 seconds."""
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


def available() -> bool:
    return JAR.exists() and shutil.which("java") is not None


def anonymise_rules(graph: Graph) -> Graph:
    """A copy with every named ``swrl:Imp`` moved onto a blank node, the only
    form the OWL API parses as a rule."""
    copy = Graph()
    copy += graph
    for rule in list(copy.subjects(RDF.type, SWRL.Imp)):
        if isinstance(rule, BNode):
            continue
        anonymous = BNode()
        for _, p, o in list(copy.triples((rule, None, None))):
            copy.remove((rule, p, o))
            copy.add((anonymous, p, o))
    return copy


def run(command: str, *iris: str, graphs: Iterable[Graph]):
    """The ``result`` of one testkit command over ``graphs``, passed as one
    merged RDF/XML file: the OWL API parses each file on its own, so a data triple in a
    file without its property's declaration would read as an annotation."""
    merged = Graph()
    for graph in graphs:
        merged += graph
    with tempfile.TemporaryDirectory() as directory:
        # RDF/XML: the OWL API's Turtle parser rejects some closures, and its
        # fallback parser needs JAXB, which Java 11 and later do not ship.
        path = Path(directory) / "closure.owl"
        anonymise_rules(merged).serialize(path, format="xml")
        if server_enabled() and not _SERVER.unavailable:
            try:
                return _SERVER.ask(command, iris, path)
            except _ServerUnavailable:
                pass
        output = subprocess.run(
            ["java", *jvm_options(), "--sun-misc-unsafe-memory-access=allow", "-jar", str(JAR), command, *iris, str(path)], capture_output=True, text=True, check=True, timeout=TIMEOUT
        ).stdout
    return json.loads(output.strip().splitlines()[-1])["result"]
