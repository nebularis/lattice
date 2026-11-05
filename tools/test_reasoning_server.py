# SPDX-License-Identifier: MPL-2.0

"""The long-running testkit JVM that `mork_compilers.reasoning.run` sends calls to (ADR-A83, addendum
2026-10-17). The cases that start a JVM skip without the built jar."""

from __future__ import annotations

import functools
import subprocess
import sys
from pathlib import Path

import pytest
from rdflib import Graph

sys.path.insert(0, str(Path(__file__).resolve().parent / "mork_compilers" / "src"))

from mork_compilers import reasoning  # noqa: E402

EX = "https://example.org/reasoning-server#"
CLOSURE = f"""
@prefix owl: <http://www.w3.org/2002/07/owl#> . @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> . @prefix ex: <{EX}> .
ex:A a owl:Class . ex:B a owl:Class ; rdfs:subClassOf ex:A . ex:C a owl:Class ; rdfs:subClassOf ex:B ; owl:disjointWith ex:A .
ex:p a owl:ObjectProperty . ex:x a owl:NamedIndividual ; ex:p ex:y . ex:y a owl:NamedIndividual .
"""
needs_jar = pytest.mark.skipif(not reasoning.available(), reason="reasoning-testkit jar not built")


@functools.cache
def _jar_serves() -> bool:
    """Whether the built jar has the `serve` command. A jar built before it existed prints a usage
    message and exits with status 2, and `run` then falls back to a JVM per call, which is correct
    but leaves nothing for these cases to check."""
    done = subprocess.run(["java", *reasoning.jvm_options(), "-jar", str(reasoning.JAR), "serve"],
                          input="", capture_output=True, text=True, timeout=120)
    return done.returncode == 0


@pytest.fixture
def server(monkeypatch: pytest.MonkeyPatch):
    """A fresh server in place of the module's, stopped afterwards, with the option on."""
    if not _jar_serves():
        pytest.skip("the reasoning-testkit jar was built before `serve` existed: run `mise run bootstrap:reasoning-testkit`")
    monkeypatch.delenv("LATTICE_REASONING_SERVER", raising=False)
    fresh = reasoning._Server()
    monkeypatch.setattr(reasoning, "_SERVER", fresh)
    yield fresh
    fresh.stop()


def _graph() -> Graph:
    return Graph().parse(format="turtle", data=CLOSURE)


@needs_jar
def test_the_server_gives_the_answers_a_jvm_per_call_gives(server, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = [
        ("consistent", ()),
        ("satisfiable", (EX + "A",)),
        ("satisfiable", (EX + "C",)),
        ("subsumes", (EX + "B", EX + "A")),
        ("subsumes", (EX + "A", EX + "B")),
        ("values", (EX + "p",)),
    ]
    served = [reasoning.run(command, *iris, graphs=[_graph()]) for command, iris in calls]
    assert server._process is not None
    monkeypatch.setenv("LATTICE_REASONING_SERVER", "0")
    assert served == [reasoning.run(command, *iris, graphs=[_graph()]) for command, iris in calls]
    assert served[2] is False and served[3] is True and served[5] == [[EX + "x", EX + "y"]]


@needs_jar
def test_calls_share_one_jvm(server) -> None:
    reasoning.run("consistent", graphs=[_graph()])
    first = server._process.pid
    reasoning.run("satisfiable", EX + "A", graphs=[_graph()])
    assert server._process.pid == first and server._process.poll() is None


@needs_jar
def test_a_call_that_fails_does_not_end_the_server(server) -> None:
    reasoning.run("consistent", graphs=[_graph()])
    first = server._process.pid
    with pytest.raises(subprocess.CalledProcessError) as failure:
        reasoning.run("nonsense", graphs=[_graph()])
    assert "unknown command nonsense" in failure.value.stderr
    assert reasoning.run("consistent", graphs=[_graph()]) is True
    assert server._process.pid == first


@needs_jar
def test_a_call_that_times_out_kills_the_jvm_and_the_next_call_starts_another(server, monkeypatch: pytest.MonkeyPatch) -> None:
    reasoning.run("consistent", graphs=[_graph()])
    first = server._process
    # No JVM loads and classifies a new closure in a millisecond.
    monkeypatch.setattr(reasoning, "TIMEOUT", 0.001)
    other = _graph()
    other.parse(format="turtle", data=f"@prefix owl: <http://www.w3.org/2002/07/owl#> . <{EX}Other> a owl:Class .")
    with pytest.raises(subprocess.TimeoutExpired):
        reasoning.run("consistent", graphs=[other])
    assert first.poll() is not None and server._process is None
    monkeypatch.setattr(reasoning, "TIMEOUT", 300)
    assert reasoning.run("consistent", graphs=[_graph()]) is True
    assert server._process.pid != first.pid


@needs_jar
def test_the_option_off_starts_no_server(server, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LATTICE_REASONING_SERVER", "0")
    assert reasoning.run("consistent", graphs=[_graph()]) is True
    assert server._process is None


@needs_jar
def test_stopping_ends_the_jvm(server) -> None:
    reasoning.run("consistent", graphs=[_graph()])
    process = server._process
    server.stop()
    assert process.poll() == 0 and server._process is None


def test_a_jar_that_cannot_serve_makes_the_process_fall_back_to_a_jvm_per_call(server, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    if not reasoning.available():
        pytest.skip("java not available")
    not_a_jar = tmp_path / "not-a-testkit.jar"
    not_a_jar.write_text("not a jar")
    monkeypatch.setattr(reasoning, "JAR", not_a_jar)
    monkeypatch.setenv("LATTICE_REASONING_JVM_OPTIONS", "")
    with pytest.raises(subprocess.CalledProcessError):      # the JVM per call reports the real fault
        reasoning.run("consistent", graphs=[_graph()])
    assert server.unavailable


def test_an_argument_with_a_tab_is_not_sent_to_the_server(tmp_path: Path) -> None:
    with pytest.raises(reasoning._ServerUnavailable):
        reasoning._Server().ask("satisfiable", ("a\tb",), tmp_path / "closure.owl")
