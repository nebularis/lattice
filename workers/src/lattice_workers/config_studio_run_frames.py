# SPDX-License-Identifier: MPL-2.0
"""The frames of a run (contracts/config-studio/README.md, Runs, and ADR-A154 decision 3), as the run worker's `RunFrames` builds them.

A run's result is cut into parts and each part into frames of at most `MAX_TEXT_BYTES` bytes as UTF-8, never inside a character, and a result
that needs more than `MAX_FRAMES` frames is one failed frame instead. The frames are a function of the result alone, so the same result gives
the same frames. Nothing here reads a clock, a random source or the broker, so the rules of a frame are tested alone and held to the
contract's `run-frame.schema.json`."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

MAX_TEXT_BYTES = 49_152
MAX_FRAMES = 128
TOO_LARGE = "the result is too large for one run, so narrow what is run"

SH = "http://www.w3.org/ns/shacl#"
CST = "https://www.nebularis.org/neuro-semantic/lattice/config-studio#"


class Severity(Enum):
    """How serious a finding is, as the report's `sh:resultSeverity` names it."""

    VIOLATION = "Violation"
    WARNING = "Warning"
    INFO = "Info"


@dataclass(frozen=True)
class Finding:
    """One finding of a run, on a mapping or a scheme, or on nothing when `focus` is None."""

    severity: Severity
    message: str
    code: str
    focus: Optional[str] = None


@dataclass(frozen=True)
class Output:
    """What one mapping wrote at one stratum, as N-Triples lines in code point order, at the path a mapping dry run's artefact has."""

    group: str
    step: int
    path: str
    ntriples: str


@dataclass(frozen=True)
class Result:
    """What a run did, apart from how it is told. `failure` is None for a run that finished, and else says why it did not. `engine`, where
    given, is what evaluated the mapping, and the report says it (ADR-A154, addendum of 2026-11-20, decision 4)."""

    failure: Optional[str] = None
    findings: tuple[Finding, ...] = ()
    outputs: tuple[Output, ...] = ()
    engine: Optional[str] = None

    @property
    def conforms(self) -> bool:
        return not any(f.severity is Severity.VIOLATION for f in self.findings)


def failed(run: str, message: str) -> list[dict[str, Any]]:
    """One failed last frame at `seq` 0, for a run that cannot start or must stop."""
    frame = _frame(run, 0, True)
    frame["status"] = "failed"
    frame["message"] = message
    return [frame]


def of(run: str, result: Result) -> list[dict[str, Any]]:
    """The frames of a `sample` run's result, or the one failed frame of a run that failed or is too large. The report comes first, and
    then each output in the order of its mapping, its step and its path, so a repeat gives the same frames."""
    if result.failure is not None:
        return failed(run, result.failure)
    frames: list[dict[str, Any]] = []
    index = _part(frames, run, 0, "report", "text/turtle", None, None, None, report_turtle(run, result))
    for output in sorted(result.outputs, key=lambda o: (o.group, o.step, o.path)):
        index = _part(frames, run, index, "artefact", "application/n-triples", output.group, output.step, output.path, output.ntriples)
        if len(frames) >= MAX_FRAMES:
            break
    if len(frames) + 1 > MAX_FRAMES:
        return failed(run, TOO_LARGE)
    last = _frame(run, len(frames), True)
    last["status"] = "succeeded"
    last["conforms"] = result.conforms
    frames.append(last)
    return frames


def encode(frame: dict[str, Any]) -> str:
    """A frame as the JSON text published as a CloudEvent's data."""
    return json.dumps(frame, ensure_ascii=False, separators=(",", ":"))


def cut(text: str) -> list[str]:
    """The text in pieces of at most `MAX_TEXT_BYTES` bytes as UTF-8. A cut never falls inside a character, and the pieces joined are the text."""
    data = text.encode("utf-8")
    pieces: list[str] = []
    start = 0
    while start < len(data):
        end = min(start + MAX_TEXT_BYTES, len(data))
        # A byte of the form 10xxxxxx continues a character, so a cut before one would split it. Move the cut back to the start.
        while end < len(data) and (data[end] & 0xC0) == 0x80:
            end -= 1
        pieces.append(data[start:end].decode("utf-8"))
        start = end
    return pieces or [""]


def report_turtle(run: str, result: Result) -> str:
    """The report of a finished run, as Turtle: an `sh:ValidationReport` minted under the run's IRI, written statement by statement in a fixed
    order, since a run's output is a function of its input alone (ADR-A154 decision 1)."""
    t = [f"@prefix sh: <{SH}> .\n@prefix cst: <{CST}> .\n\n"]
    findings = result.findings
    results = " , ".join(f"<{run}#result-{n}>" for n in range(1, len(findings) + 1))
    t.append(f"<{run}#report> a sh:ValidationReport ;\n")
    if result.engine is not None:
        t.append(f"    cst:engine {_literal(result.engine)} ;\n")
    t.append(f"    sh:conforms {'true' if result.conforms else 'false'}")
    t.append(" .\n" if not findings else f" ;\n    sh:result {results} .\n")
    for n, f in enumerate(findings, start=1):
        t.append(f"\n<{run}#result-{n}> a sh:ValidationResult ;\n")
        if f.focus is not None and ":" in f.focus:
            t.append(f"    sh:focusNode <{_iri(f.focus)}> ;\n")
        t.append(f"    sh:resultMessage {_literal(f.message)} ;\n")
        t.append(f"    sh:resultSeverity sh:{f.severity.value} ;\n")
        t.append(f"    cst:code {_literal(f.code)} .\n")
    return "".join(t)


def _iri(value: str) -> str:
    """An IRI written between angle brackets, with each character that may not be in one written as a numeric escape."""
    return "".join(c if c not in '<>"{}|^`\\' and ord(c) > 0x20 else f"\\u{ord(c):04X}" for c in value)


def _literal(value: str) -> str:
    """A string literal as N-Triples writes it, so it is also Turtle."""
    out = []
    for c in value:
        if c == "\\":
            out.append("\\\\")
        elif c == '"':
            out.append('\\"')
        elif c == "\n":
            out.append("\\n")
        elif c == "\r":
            out.append("\\r")
        elif c == "\t":
            out.append("\\t")
        elif ord(c) < 0x20 or ord(c) == 0x7F:
            out.append(f"\\u{ord(c):04X}")
        else:
            out.append(c)
    return '"' + "".join(out) + '"'


def _part(
    frames: list[dict[str, Any]], run: str, index: int, role: str, media_type: str, group: Optional[str], step: Optional[int],
    path: Optional[str], text: str,
) -> int:
    """Adds the frames of one part and returns the index of the next."""
    pieces = cut(text)
    for i, piece in enumerate(pieces):
        frame = _frame(run, len(frames), False)
        if i == 0:
            part: dict[str, Any] = {"index": index, "role": role, "mediaType": media_type}
            if path is not None:
                part["path"] = path
            if group is not None:
                part["group"] = group
                part["step"] = step if step is not None else 0
            frame["part"] = part
        if piece:
            frame["text"] = piece
        if i < len(pieces) - 1:
            frame["more"] = True
        frames.append(frame)
    return index + 1


def _frame(run: str, seq: int, last: bool) -> dict[str, Any]:
    return {"run": run, "seq": seq, "last": last}
