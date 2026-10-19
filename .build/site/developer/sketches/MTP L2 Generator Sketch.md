# MTP L2/L3 Generator: lenses and cassettes

Design for the tooling that produces the nine doctrine **lenses** and the **cassette** library, plus three derived artefacts that fall out of the same pipeline.

---

## 1. What is being produced

| Artefact | Count | Budget each | Curated fraction |
|---|---|---|---|
| `out/lenses/L-*.txt` | 9 | 300–800 tok | ~40% (`Q`, `RULES`, `SMELLS`) |
| `out/cassettes/C-*.txt` | 30–60 | 150–400 tok | ~15% (`nl`, `why`, focus declaration) |
| `out/routing.yaml` | 1 | — | signals curated, coverage gated |
| `out/diagnostics.json` | 1 | — | **0%** — feeds the §5 repair loop |
| `out/eval/*.json` | ≥18 | — | **0%** — held-out tasks |
| `out/partition.md`, `out/stats.md` | 2 | — | proof artefacts for CI |

The last three are free by-products. That matters: the repair table and the eval suite were separate line items in the original plan, and this pipeline generates both, because it already has to know which mistake produces which diagnostic and which examples are gold.

---

## 2. The load-bearing idea: mutation-derived ground truth

Hand-written teaching material rots in a specific way: the *"caught by"* column goes stale, and prose warns about mistakes the machine now catches for free while staying silent about mistakes nothing catches.

So don't write it. **Derive it by breaking correct examples on purpose.**

```
gold cassette (verified real example)
      │
      ├─ apply mutation operator (swap cb→ap, drop df, retype MD→M, …)
      │
      └─ decode → lint (§14.2) → SHACL (constraints.ttl) → OWL reasoner
             │
             ├─ diagnostic produced  ⇒ record it. This is the "caught by" cell,
             │                          and the repair-loop fragment, and the
             │                          negative half of the minimal pair.
             │
             └─ NOTHING produced    ⇒ **finding.** Nothing downstream will catch
                                      this mistake. It needs prose (a SMELL), it
                                      gets teaching priority, and it files a gap
                                      report against constraints.ttl.
```

Two consequences worth stating plainly:

- **Teaching budget is allocated by evidence, not taste.** A distinction the lint set catches needs one line and a pointer, because the repair loop handles the tail. A distinction nothing catches needs a smell test, a cassette and a place in the lens. The `silent` set *is* the priority list.
- **The mutation matrix is regenerated when `constraints.ttl` changes.** Tighten a shape and previously-silent mutations become caught; the lens's `CAUGHT`/`UNCAUGHT` lines move automatically and the human is told which `SMELLS` entries are now redundant.

`cb` vs `ap` is caught (GCI 2.14a). `df` vs `dp` is **not** — both are legal, they differ in whether you may consume the parent's output, and no axiom distinguishes them. That asymmetry is invisible when you write doctrine by hand and obvious the moment you run the mutations.

---

## 3. Inputs

| # | Input | Form | Owner | Role |
|---|---|---|---|---|
| I1 | `Mork.ttl` (+ imports) | Turtle | ontology | terms, axioms, fingerprints (reuses `mtp.facts`) |
| I2 | `codebook.yaml` | YAML | build | code ↔ IRI (reuses `mtp.codebook`) |
| I3 | `constraints.ttl` | SHACL | ontology | validation ground truth |
| I4 | MCN decoder + lint | executable / importable | compiler team | verification; **pluggable**, see §5.1 |
| I5 | MCN encoder (§15) | executable / importable | compiler team | optional; auto-derives gold MCN |
| I6 | Example corpus | `ontology/mork/examples/**/*.ttl`, real mapping schemes | repo | source of cassettes + frequency stats |
| I7 | `lenses/L-*.yaml` | YAML | curator | `Q`, `RULES`, `SMELLS`, partition claims, `covers` |
| I8 | `cassettes/C-*.yaml` | YAML | curator | NL prompt, source pointer, focus, mutations, split |
| I9 | `partition.yaml` | YAML | curator | term → lens assignment rules |
| I10 | `routing.yaml` (src) | YAML | curator | task/signal → lens+cassette |
| I11 | `pins.lock.json` | JSON | generated | term fingerprints, lens membership hashes, diagnostic pins |
| I12 | `config.yaml` | YAML | build | paths, budgets, adapter config, policy |

The corpus (I6) is the input people underestimate. Cassettes must be *real*, because a hand-invented example teaches an idiom nobody uses and silently omits the awkward structure that real data forces. Every cassette is traceable to a file in the repository and proved isomorphic to it.

---

## 4. Pipeline

```
S1 facts        I1,I2        → terms, axioms, MCN-rendered GCIs        (existing mtp.facts)
S2 corpus       I6           → predicate freq, co-occurrence, unused codes
S3 partition    I1,I9        → term → lens, exhaustive & disjoint      [GATE]
S4 fidelity     I6,I8,I4,I5  → gold MCN per cassette, decode ≅ source  [GATE]
S5 minimise     S4,I4        → ddmin to teaching core, lint-clean      [GATE]
S6 mutate       S5,I3,I4     → diagnostic matrix; silent-set findings   [GATE]
S7 select       S2,S6        → minimal cassette set covering claims
S8 render lens  S3,S6,I7     → L-*.txt/.json                            [GATE budget]
S9 render cass  S5,S6,I8     → C-*.txt/.json
S10 routing     I10,S3       → routing.yaml, reachability               [GATE]
S11 eval        I8 split     → out/eval/*.json, leakage check           [GATE]
S12 repair tbl  S6           → diagnostics.json
S13 manifest    all          → hashes, budgets, provisional flag
```

Determinism throughout: sorted iteration, fixed-seed selection, canonical N-Triples for every comparison.

---

## 5. Code

### 5.1 `mtp/mcnio.py` — pluggable decoder adapter

The generator must not hard-depend on the decoder's packaging. One protocol, three adapters, graceful degradation.

```python
"""Adapter boundary to the MCN decoder / encoder / lint / SHACL stack.

The generator is useless without verification, but must not be blocked on how
the decoder is packaged. Anything satisfying MCNTool works.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable

from rdflib import Graph
from rdflib.compare import isomorphic, to_isomorphic

@dataclass(frozen=True)
class Diagnostic:
    kind: str          # decode | lint | shacl | owl
    code: str          # canonical id, e.g. lint.MD-no-df, shacl.DatumTBoxShape
    line: int | None
    message: str
    severity: str = "error"

    def key(self) -> str:
        return f"{self.kind}.{self.code}"

@dataclass
class DecodeResult:
    ok: bool
    graph: Graph | None
    diagnostics: tuple[Diagnostic, ...] = ()

    def codes(self) -> tuple[str, ...]:
        return tuple(sorted({d.key() for d in self.diagnostics}))

@runtime_checkable
class MCNTool(Protocol):
    def decode(self, mcn: str) -> DecodeResult: ...
    def lint(self, g: Graph) -> tuple[Diagnostic, ...]: ...
    def shacl(self, g: Graph) -> tuple[Diagnostic, ...]: ...
    def encode(self, g: Graph, hints: dict) -> str | None: ...   # None if unsupported

class InProcessTool:
    """Preferred: the decoder is importable."""

    def __init__(self, shapes: Path, reasoner: bool = False):
        import mcn  # noqa: F401  (compiler team's package)
        self._mcn = __import__("mcn")
        self._shapes = Graph().parse(str(shapes), format="turtle")
        self._reasoner = reasoner

    def decode(self, mcn: str) -> DecodeResult:
        try:
            g = self._mcn.decode(mcn)
        except Exception as e:                       # decoder errors are data, not crashes
            return DecodeResult(False, None, (Diagnostic("decode", _err_code(e), _err_line(e), str(e)),))
        return DecodeResult(True, g, ())

    def lint(self, g: Graph) -> tuple[Diagnostic, ...]:
        return tuple(Diagnostic("lint", w.code, w.line, w.message, w.severity)
                     for w in self._mcn.lint(g))

    def shacl(self, g: Graph) -> tuple[Diagnostic, ...]:
        from pyshacl import validate
        conforms, results, _ = validate(g, shacl_graph=self._shapes,
                                        advanced=True, inference="rdfs" if self._reasoner else "none")
        if conforms:
            return ()
        return tuple(_shacl_diagnostics(results))

    def encode(self, g: Graph, hints: dict) -> str | None:
        enc = getattr(self._mcn, "encode", None)
        return enc(g, **hints) if enc else None

class SubprocessTool:
    """Fallback: the decoder is a CLI. Contract: JSON on stdout."""

    def __init__(self, cmd: list[str], shapes: Path):
        self._cmd, self._shapes = cmd, shapes

    def decode(self, mcn: str) -> DecodeResult:
        p = subprocess.run(self._cmd + ["decode", "--json"], input=mcn,
                           capture_output=True, text=True)
        payload = json.loads(p.stdout or "{}")
        diags = tuple(Diagnostic(**d) for d in payload.get("diagnostics", []))
        if p.returncode != 0 or "ntriples" not in payload:
            return DecodeResult(False, None, diags or
                                (Diagnostic("decode", "decode.failed", None, p.stderr.strip()),))
        g = Graph().parse(data=payload["ntriples"], format="nt")
        return DecodeResult(True, g, diags)
    # lint/shacl/encode analogous

class NullTool:
    """No decoder available. Every build is marked provisional."""

    def decode(self, mcn: str) -> DecodeResult:
        return DecodeResult(False, None,
                            (Diagnostic("decode", "adapter.absent", None, "no MCN tool configured"),))

    def lint(self, g): return ()
    def shacl(self, g): return ()
    def encode(self, g, hints): return None

def graphs_equal(a: Graph, b: Graph, ignore: set | None = None) -> tuple[bool, str]:
    """Isomorphism modulo a predicate ignore-set (owl:NamedIndividual typing, etc.)."""
    ignore = ignore or set()

    def strip(g: Graph) -> Graph:
        out = Graph()
        for s, p, o in g:
            if p in ignore or o in ignore:
                continue
            out.add((s, p, o))
        return out

    ga, gb = strip(a), strip(b)
    if isomorphic(ga, gb):
        return True, ""
    ia, ib = to_isomorphic(ga), to_isomorphic(gb)
    only_a = sorted(f"+ {s} {p} {o}" for s, p, o in (ia - ib))
    only_b = sorted(f"- {s} {p} {o}" for s, p, o in (ib - ia))
    return False, "\n".join(only_a[:12] + only_b[:12])
```

`NullTool` exists so the repository can build the *curated* halves before the decoder lands; the manifest carries `"provisional": true` and CI refuses to publish such a pack.

---

### 5.2 `mtp/mcnline.py` — just enough MCN structure to mutate

Full parsing belongs to the decoder. Mutation needs only to locate and edit `code value-list` pairs, which means a delimiter-aware tokeniser.

```python
"""Minimal structural view of an MCN node line: enough to mutate, not to decode."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

_TYPE_TOK = re.compile(r"^\+?[A-Z][A-Za-z]?(\+[A-Za-z:][\w:]*)*$")

def tokenise(line: str) -> list[str]:
    """Split on whitespace, respecting quotes and nesting of [] {}."""
    toks, buf, depth, q, esc = [], [], 0, False, False
    for ch in line:
        if esc:
            buf.append(ch); esc = False; continue
        if ch == "\\" and q:
            buf.append(ch); esc = True; continue
        if ch == '"':
            q = not q; buf.append(ch); continue
        if q:
            buf.append(ch); continue
        if ch in "[{":
            depth += 1; buf.append(ch); continue
        if ch in "]}":
            depth -= 1; buf.append(ch); continue
        if ch in " \t" and depth == 0:
            if buf:
                toks.append("".join(buf)); buf = []
            continue
        buf.append(ch)
    if buf:
        toks.append("".join(buf))
    return toks

@dataclass
class Pair:
    code: str
    values: list[str]          # list members, annotations kept attached to the member

    def render(self) -> str:
        return f"{self.code} {','.join(self.values)}"

@dataclass
class NodeLine:
    subject: str
    types: list[str] = field(default_factory=list)
    pairs: list[Pair] = field(default_factory=list)
    raw: str = ""

    def codes(self) -> set[str]:
        return {p.code for p in self.pairs}

    def get(self, code: str) -> Pair | None:
        return next((p for p in self.pairs if p.code == code), None)

    def drop(self, code: str) -> bool:
        n = len(self.pairs)
        self.pairs = [p for p in self.pairs if p.code != code]
        return len(self.pairs) != n

    def rename(self, old: str, new: str) -> bool:
        hit = False
        for p in self.pairs:
            if p.code == old:
                p.code, hit = new, True
        return hit

    def render(self) -> str:
        head = " ".join([self.subject] + (["+".join(self.types)] if self.types else []))
        return " ".join([head] + [p.render() for p in self.pairs])

def parse_node_line(line: str) -> NodeLine | None:
    """None for directives, blocks, axiom lines, expression lines."""
    s = line.strip()
    if not s or s[0] in "@%!#":
        return None
    toks = tokenise(s)
    if len(toks) >= 2 and toks[1] == "=":
        return None                                   # expression line
    nl = NodeLine(subject=toks[0], raw=line)
    i = 1
    if i < len(toks) and all(_TYPE_TOK.match(t) for t in toks[i].split("+")) \
            and not toks[i].islower():
        nl.types = toks[i].split("+"); i += 1
    while i + 1 <= len(toks) - 1:
        code, val = toks[i], toks[i + 1]
        nl.pairs.append(Pair(code, _split_list(val)))
        i += 2
    return nl

def _split_list(value: str) -> list[str]:
    """Split a value-list on top-level commas (annotations/brackets protected)."""
    out, buf, depth, q = [], [], 0, False
    for ch in value:
        if ch == '"':
            q = not q
        if not q:
            if ch in "[{":
                depth += 1
            elif ch in "]}":
                depth -= 1
            elif ch == "," and depth == 0:
                out.append("".join(buf)); buf = []; continue
        buf.append(ch)
    if buf:
        out.append("".join(buf))
    return out

class Document:
    """An MCN document as a line list, with structural access to node lines."""

    def __init__(self, text: str):
        self.lines = text.rstrip("\n").split("\n")

    def nodes(self):
        for idx, line in enumerate(self.lines):
            nl = parse_node_line(line)
            if nl:
                yield idx, nl

    def replace(self, idx: int, nl: NodeLine) -> "Document":
        d = Document("\n".join(self.lines))
        d.lines[idx] = nl.render()
        return d

    def without(self, idxs: set[int]) -> "Document":
        return Document("\n".join(l for i, l in enumerate(self.lines) if i not in idxs))

    def text(self) -> str:
        return "\n".join(self.lines) + "\n"
```

---

### 5.3 `mtp/corpus.py` — evidence for ordering

```python
"""Frequency and co-occurrence statistics over the real MORK corpus.

Purpose: order lenses and cassettes by what practitioners actually write, and
identify codes that appear nowhere (L5-only; do not spend L2 budget on them).
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from rdflib import Graph, URIRef
from rdflib.namespace import RDF

@dataclass
class CorpusStats:
    files: tuple[str, ...]
    triples: int
    predicate_freq: Counter = field(default_factory=Counter)
    type_freq: Counter = field(default_factory=Counter)
    cooccurrence: Counter = field(default_factory=Counter)   # (p1,p2) on same subject
    subject_shapes: Counter = field(default_factory=Counter) # frozenset of codes
    per_file_predicates: dict = field(default_factory=dict)

    def rank(self, iri: str) -> int:
        order = [p for p, _ in self.predicate_freq.most_common()]
        return order.index(iri) if iri in order else 10_000

    def unused(self, all_iris) -> list[str]:
        return sorted(set(all_iris) - set(self.predicate_freq) - set(self.type_freq))

def scan(paths, mork_ns: str) -> CorpusStats:
    files, total = [], 0
    pf, tf, co, shapes, perfile = Counter(), Counter(), Counter(), Counter(), {}

    for p in sorted(Path(x) for x in paths):
        g = Graph().parse(str(p), format="turtle")
        files.append(str(p)); total += len(g)
        local = Counter()

        for s in set(g.subjects()):
            preds = {str(pr) for pr in g.predicates(s, None)
                     if str(pr).startswith(mork_ns)}
            for pr in preds:
                pf[pr] += 1; local[pr] += 1
            for a in sorted(preds):
                for b in sorted(preds):
                    if a < b:
                        co[(a, b)] += 1
            if preds:
                shapes[frozenset(preds)] += 1
            for t in g.objects(s, RDF.type):
                if str(t).startswith(mork_ns):
                    tf[str(t)] += 1
        perfile[str(p)] = local

    return CorpusStats(tuple(files), total, pf, tf, co, shapes, perfile)

def report(stats: CorpusStats, cb, all_iris) -> str:
    rows = ["# Corpus statistics", "",
            f"files: {len(stats.files)}  triples: {stats.triples}", "",
            "## Predicate frequency", "", "| rank | code | predicate | subjects |", "|---|---|---|---|"]
    for i, (iri, n) in enumerate(stats.predicate_freq.most_common(), 1):
        rows.append(f"| {i} | `{cb.code_for(iri) or '-'}` | {iri.rsplit('#',1)[-1]} | {n} |")
    unused = stats.unused(all_iris)
    rows += ["", "## Never used in corpus (L5-only candidates)", ""]
    rows += [f"- `{cb.code_for(i) or '-'}` {i.rsplit('#',1)[-1]}" for i in unused] or ["(none)"]
    return "\n".join(rows) + "\n"
```

The "never used" list is a real budget decision: `narrowNavigableConceptRole`, `collectionElementScalarValue`, `epv` and friends can be documented in L5 only. Spending L2 tokens on them is measurable waste.

---

### 5.4 `mtp/partition.py` — every term has exactly one lens

```python
"""Assign every MORK term to exactly one lens. Exhaustive and disjoint, gated."""
from __future__ import annotations

import fnmatch
import hashlib
from dataclasses import dataclass

import yaml
from pathlib import Path

@dataclass
class Partition:
    assign: dict[str, str]                # iri -> lens id
    by_lens: dict[str, list[str]]
    problems: list

    def membership_hash(self, lens: str) -> str:
        blob = "\n".join(sorted(self.by_lens.get(lens, [])))
        return hashlib.sha256(blob.encode()).hexdigest()[:12]
```

```yaml
# partition.yaml
lenses: [L-REP, L-TAX, L-IND, L-GEN, L-TPL, L-INT, L-EGR, L-UNC, L-TBX]
default: L-TBX                # shadow declarations, OwlAxiom proxies

rules:                        # first match wins; evaluated in order
  - lens: L-INT
    subtree: [mork:IntentNode, mork:IntentScheme]
    glob: ["*Intent*", "*constraint*", "*scope*", "*temporal*", "*referenceIdentifier*"]
  - lens: L-GEN
    subtree: [mork:GenerativeMapping, mork:TargetingSpec, mork:ParameterBinding,
              mork:ConstraintProvenance, mork:RuleProvenance, mork:TransformProvenance,
              mork:ProjectionProvenance, mork:ShapeTemplate, mork:RuleTemplate,
              mork:QueryTemplate, mork:CompilationMode, mork:ConstraintScheme, mork:RuleScheme]
    glob: ["*generates*", "*Provenance*", "*param*", "*jurisdiction*", "*effective*",
           "*compilationMode*", "*Severity*", "*llm*", "*review*", "*impactScope*"]
  - lens: L-TPL
    subtree: [mork:TemplateExpression, mork:TemplateBinding]
    glob: ["*template*", "*Template*", "*interpolation*", "*concat*", "*lookup*",
           "*placeholder*", "*Interpolation*", "*Lookup*"]
  - lens: L-EGR
    explicit: [mork:egressProjection, mork:TransformMapping,
               mork:generatesTransformDefinition, mork:supersedes, mork:deprecationReason]
  - lens: L-UNC
    explicit: [mork:UncertainMapping, mork:WeightedMatch, mork:weighting,
               mork:hypothesisMapping, mork:Hypothesis, mork:mappingRecommendation,
               mork:possibleMatch, mork:lexicalMatch, mork:semanticMatch,
               mork:structuralMatch, mork:partialMatch, mork:incompleteMapping,
               mork:userDeclined]
  - lens: L-IND
    subtree: [mork:Datum, mork:DeferredContext, mork:precedes]
    glob: ["*deferred*", "*dependent*", "*Deferred*", "*precede*", "*Identity*",
           "*yieldConcept*", "*composite*Mapping*", "*Applicative*", "*mappingIndex*"]
  - lens: L-REP
    subtree: [mork:Representation, mork:RepresentationScheme, mork:SerializationFormat]
    glob: ["*Collection*", "*Element*", "*Items*", "*identifier*", "*path*", "*format*"]
  - lens: L-TAX
    subtree: [mork:DataConcept, mork:TaxonomyScheme, mork:Objectification]
    glob: ["*ConceptRole*", "*Category*Match*", "*exact*Match*", "*concept*"]

overrides:                    # break ties the rules get wrong
  mork:conceptName: L-IND     # naming minted axioms is an individuation concern
  mork:identifier: L-REP
  mork:mappingNote: L-UNC     # evidence discipline lives with uncertainty
```

```python
def build(facts, cb, cfg_path: Path) -> Partition:
    from .doctrine import Problem
    spec = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    lenses = list(spec["lenses"])
    assign, problems = {}, []

    overrides = {cb.expand(k): v for k, v in (spec.get("overrides") or {}).items()}
    for lens, iri in ((v, k) for k, v in overrides.items()):
        pass  # validated below

    def match(term) -> str | None:
        if term.iri in overrides:
            return overrides[term.iri]
        local = term.iri.rsplit("#", 1)[-1]
        for rule in spec["rules"]:
            for e in (rule.get("explicit") or []):
                if cb.expand(e) == term.iri:
                    return rule["lens"]
            for root in (rule.get("subtree") or []):
                r = cb.expand(root)
                if term.iri == r or term.iri in facts.descendants(r):
                    return rule["lens"]
            for g in (rule.get("glob") or []):
                if fnmatch.fnmatch(local, g):
                    return rule["lens"]
        return None

    mork_ns = cb.prefixes["mork"]
    for iri, term in sorted(facts.terms.items()):
        if not iri.startswith(mork_ns):
            continue
        lens = match(term) or spec["default"]
        if lens not in lenses:
            problems.append(Problem("error", "partition.unknown-lens",
                                    f"{iri} assigned to unknown lens '{lens}'"))
        assign[iri] = lens

    by_lens = {l: sorted(i for i, v in assign.items() if v == l) for l in lenses}
    for l, members in sorted(by_lens.items()):
        if not members:
            problems.append(Problem("error", "partition.empty",
                                    f"lens {l} owns no terms: delete it or fix partition.yaml"))
    return Partition(assign, by_lens, problems)

def check_pins(part: Partition, lock: dict):
    """Membership drift: absorbed terms warn, vanished explicit terms error."""
    from .doctrine import Problem
    out, pinned = [], lock.get("lens_membership", {})
    for lens, members in sorted(part.by_lens.items()):
        h = part.membership_hash(lens)
        prev = pinned.get(lens)
        if prev is None:
            out.append(Problem("error", "partition.unpinned",
                               f"lens {lens} has no membership pin", "run `mtp update-pins`"))
        elif prev["hash"] != h:
            added = sorted(set(members) - set(prev.get("members", [])))
            removed = sorted(set(prev.get("members", [])) - set(members))
            sev = "error" if removed else "warn"
            out.append(Problem(sev, "partition.membership-changed",
                f"{lens} membership changed (+{len(added)} / -{len(removed)})",
                "confirm the lens prose still covers: " + ", ".join(
                    x.rsplit('#',1)[-1] for x in (added + removed)[:8])))
    return out
```

---

### 5.5 `mtp/mutate.py` — the engine

```python
"""Mutation operators over MCN documents, and diagnostic capture.

Each operator has a precondition, a transform, and a claim about what the
distinction teaches. The diagnostic it provokes is discovered, never asserted.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .mcnline import Document, NodeLine
from .mcnio import DecodeResult, Diagnostic, MCNTool

@dataclass(frozen=True)
class Mutation:
    id: str                      # "swap:cb->ap"
    teaches: str                 # doctrine unit id, e.g. "pair.cb-ap"
    description: str

@dataclass
class MutantOutcome:
    mutation: Mutation
    applied: bool
    line_before: str = ""
    line_after: str = ""
    diagnostics: tuple[Diagnostic, ...] = ()
    verdict: str = "not-applicable"     # caught-decode|caught-lint|caught-shacl|caught-owl|silent

    def primary(self) -> str | None:
        order = {"decode": 0, "lint": 1, "shacl": 2, "owl": 3}
        ds = sorted(self.diagnostics, key=lambda d: order.get(d.kind, 9))
        return ds[0].key() if ds else None

Operator = Callable[[Document], list[tuple[Document, str, str]]]   # (mutant, before, after)

def _swap(a: str, b: str) -> Operator:
    def op(doc: Document):
        out = []
        for idx, nl in doc.nodes():
            if a in nl.codes():
                before = nl.render()
                nl2 = _clone(nl); nl2.rename(a, b)
                out.append((doc.replace(idx, nl2), before, nl2.render()))
        return out
    return op

def _drop(code: str) -> Operator:
    def op(doc: Document):
        out = []
        for idx, nl in doc.nodes():
            if code in nl.codes():
                before = nl.render()
                nl2 = _clone(nl); nl2.drop(code)
                out.append((doc.replace(idx, nl2), before, nl2.render()))
        return out
    return op

def _retype(a: str, b: str) -> Operator:
    def op(doc: Document):
        out = []
        for idx, nl in doc.nodes():
            if a in nl.types:
                before = nl.render()
                nl2 = _clone(nl)
                nl2.types = [b if t == a else t for t in nl2.types]
                out.append((doc.replace(idx, nl2), before, nl2.render()))
        return out
    return op

def _both_directions(child: str, parent: str) -> Operator:
    """Add the inverse edge that the loan example warns double-counts."""
    def op(doc: Document):
        out = []
        for idx, nl in doc.nodes():
            p = nl.get(child)
            if not p:
                continue
            for target in p.values:
                tgt = target.split("{")[0]
                for j, other in doc.nodes():
                    if other.subject != tgt:
                        continue
                    before = other.render()
                    o2 = _clone(other)
                    o2.pairs.append(type(p)(parent, [nl.subject]))
                    out.append((doc.replace(j, o2), before, o2.render()))
        return out
    return op

def _add_pair(code: str, value: str) -> Operator:
    def op(doc: Document):
        out = []
        for idx, nl in doc.nodes():
            if code in nl.codes():
                continue
            before = nl.render()
            nl2 = _clone(nl)
            from .mcnline import Pair
            nl2.pairs.append(Pair(code, [value]))
            out.append((doc.replace(idx, nl2), before, nl2.render()))
        return out
    return op

def _clone(nl: NodeLine) -> NodeLine:
    from .mcnline import Pair
    return NodeLine(nl.subject, list(nl.types),
                    [Pair(p.code, list(p.values)) for p in nl.pairs], nl.raw)

# --------------------------------------------------------------------------- #
# catalogue: one entry per teachable distinction
# --------------------------------------------------------------------------- #

CATALOGUE: dict[str, tuple[Mutation, Operator]] = {
    "swap:cb->ap":   (Mutation("swap:cb->ap", "pair.cb-ap",
                     "treat a component as an applicative context"), _swap("cb", "ap")),
    "swap:ap->cb":   (Mutation("swap:ap->cb", "pair.cb-ap",
                     "treat a contextual application as mere composition"), _swap("ap", "cb")),
    "drop:xr":       (Mutation("drop:xr", "pair.cb-ap",
                     "applicative context without the joining relation"), _drop("xr")),
    "drop:df":       (Mutation("drop:df", "inv.order",
                     "individuate without establishing the class"), _drop("df")),
    "swap:df->dp":   (Mutation("swap:df->dp", "pair.df-dp",
                     "hard prerequisite where context consumption was meant"), _swap("df", "dp")),
    "swap:dp->df":   (Mutation("swap:dp->df", "pair.df-dp",
                     "consume output of a mapping that only had to run first"), _swap("dp", "df")),
    "swap:xt->bt":   (Mutation("swap:xt->bt", "pair.xt-bt",
                     "mint a class that already exists"), _swap("xt", "bt")),
    "swap:bt->xt":   (Mutation("swap:bt->xt", "pair.xt-bt",
                     "match a class that does not exist yet"), _swap("bt", "xt")),
    "swap:xr->xi":   (Mutation("swap:xr->xi", "pair.xr-xi",
                     "traverse a relation backwards"), _swap("xr", "xi")),
    "swap:xa->ba":   (Mutation("swap:xa->ba", "pair.xa-ba",
                     "A-Box category match without the relation"), _swap("xa", "ba")),
    "swap:kn->cn":   (Mutation("swap:kn->cn", "pair.kn-cn",
                     "compose concepts with a mapping property"), _swap("kn", "cn")),
    "retype:MD->M":  (Mutation("retype:MD->M", "inv.order",
                     "drop the individuation claim"), _retype("MD", "M")),
    "retype:MU->M":  (Mutation("retype:MU->M", "inv.uncertainty",
                     "assert a guess as certain"), _retype("MU", "M")),
    "retype:MS->MR": (Mutation("retype:MS->MR", "pair.ms-mr",
                     "confuse validation with inference"), _retype("MS", "MR")),
    "drop:pv":       (Mutation("drop:pv", "lens:L-GEN",
                     "ungoverned generative mapping"), _drop("pv")),
    "drop:tg":       (Mutation("drop:tg", "lens:L-GEN",
                     "artefact with no target scope"), _drop("tg")),
    "drop:pb":       (Mutation("drop:pb", "lens:L-GEN",
                     "artefact with no parameter binding"), _drop("pb")),
    "drop:mr":       (Mutation("drop:mr", "inv.uncertainty",
                     "uncertain mapping with no recommendation"), _drop("mr")),
    "drop:w":        (Mutation("drop:w", "inv.uncertainty",
                     "unweighted uncertain match"), _drop("w")),
    "both:cb+cn":    (Mutation("both:cb+cn", "inv.one_direction",
                     "assert both directions of an inverse pair"), _both_directions("cb", "cn")),
    "add:gr":        (Mutation("add:gr", "pair.ms-mr",
                     "one mapping generating both shape and rule"),
                     _add_pair("gr", '"A(?x)->B(?x)"')),
    "drop:ss-ef":    (Mutation("drop:ss-ef", "lens:L-EGR",
                     "supersede without an effective date"), _drop("ef")),
}

def run(doc: Document, tool: MCNTool, only: list[str] | None = None,
        run_shacl: bool = True) -> list[MutantOutcome]:
    outcomes = []
    for mid in sorted(only or CATALOGUE):
        mut, op = CATALOGUE[mid]
        variants = op(doc)
        if not variants:
            outcomes.append(MutantOutcome(mut, applied=False))
            continue
        mutant, before, after = variants[0]          # deterministic: first match
        res = tool.decode(mutant.text())
        diags = list(res.diagnostics)
        if res.ok and res.graph is not None:
            diags += list(tool.lint(res.graph))
            if run_shacl:
                diags += list(tool.shacl(res.graph))
        verdict = _verdict(diags)
        outcomes.append(MutantOutcome(mut, True, before, after, tuple(diags), verdict))
    return outcomes

def _verdict(diags) -> str:
    kinds = {d.kind for d in diags if d.severity != "info"}
    for k in ("decode", "lint", "shacl", "owl"):
        if k in kinds:
            return f"caught-{k}"
    return "silent"
```

The catalogue is the *teaching surface*. Adding a distinction means adding an operator, not writing prose — and the tool then tells you whether prose is even needed.

---

### 5.6 `mtp/minimise.py` — ddmin to the teaching core

```python
"""Delta-debugging over MCN lines: smallest document that still teaches.

The teaching predicate is explicit so minimisation cannot quietly remove the
construct the cassette exists to demonstrate.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from rdflib import URIRef
from .mcnline import Document
from .mcnio import MCNTool

@dataclass
class Focus:
    predicates: tuple[str, ...] = ()      # IRIs that must survive
    subjects: tuple[str, ...] = ()         # local ids that must survive
    types: tuple[str, ...] = ()            # class IRIs that must survive
    lint_clean: bool = True

def teaches(doc: Document, tool: MCNTool, focus: Focus, base: str) -> bool:
    res = tool.decode(base + doc.text())
    if not res.ok or res.graph is None:
        return False
    g = res.graph
    if focus.lint_clean and any(d.severity == "error" for d in tool.lint(g)):
        return False
    for p in focus.predicates:
        if (None, URIRef(p), None) not in g:
            return False
    for t in focus.types:
        if not any(g.subjects(URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"), URIRef(t))):
            return False
    present = {str(s) for s in set(g.subjects())}
    for s in focus.subjects:
        if not any(str(x).endswith("#" + s) or str(x).endswith("/" + s) for x in present):
            return False
    return True

def ddmin(doc: Document, tool: MCNTool, focus: Focus, base: str,
          protected: set[int] | None = None) -> Document:
    """Classic ddmin over removable line indices; header lines are protected."""
    protected = protected or set()
    removable = [i for i, l in enumerate(doc.lines)
                 if i not in protected and l.strip() and not l.lstrip().startswith(("@", "%"))]
    n = 2
    current = doc
    while len(removable) >= 2:
        chunk = max(1, len(removable) // n)
        groups = [removable[i:i + chunk] for i in range(0, len(removable), chunk)]
        reduced = False
        for grp in groups:
            candidate = current.without(set(grp))
            if teaches(candidate, tool, focus, base):
                current = candidate
                removable = [i for i in removable if i not in set(grp)]
                # reindex after removal
                current = Document(current.text())
                removable = [i for i, l in enumerate(current.lines)
                             if i not in protected and l.strip()
                             and not l.lstrip().startswith(("@", "%"))]
                n = max(2, n - 1)
                reduced = True
                break
        if not reduced:
            if n >= len(removable):
                break
            n = min(len(removable), 2 * n)
    return _drop_pairs(current, tool, focus, base, protected)

def _drop_pairs(doc: Document, tool: MCNTool, focus: Focus, base: str, protected):
    """Second pass: within surviving lines, drop individual code/value pairs."""
    from .mcnline import parse_node_line
    current = doc
    changed = True
    while changed:
        changed = False
        for idx, nl in list(current.nodes()):
            for code in sorted(nl.codes()):
                trial = parse_node_line(current.lines[idx])
                if trial is None or not trial.drop(code):
                    continue
                cand = current.replace(idx, trial)
                if teaches(cand, tool, focus, base):
                    current, changed = cand, True
                    break
            if changed:
                break
    return current
```

Two passes matter: line-level ddmin removes irrelevant nodes, pair-level removal strips incidental properties from the nodes that remain. Without the second pass cassettes carry noise like `p contract.signatories...` that teaches nothing about deferral.

---

### 5.7 `mtp/cassette.py` — fidelity, minimisation, rendering

```yaml
# cassettes/C-IND-01.yaml
id: C-IND-01
lens: L-IND
title: A datum needs the class mapping it defers to
teaches: [inv.order, pair.df-dp]
source: ontology/mork/examples/Mork2RML/loan_mapping.ttl
gold: auto                # auto | inline
mcn: null                 # populated by `mtp cassette build` when gold: auto
focus:
  predicates: [mork:deferredMapping, mork:exactTBoxMatch]
  types: [mork:Datum]
  subjects: [Map_Loan]
nl: |
  Loan records arrive as JSON with loanId and principal. Map the loan itself
  into fin:Loan.
why: >
  MD individuates; it cannot do so before the class axiom exists, so it defers
  to the mapping that establishes the T-Box (Axiom 2.7a).
mutations: [drop:df, retype:MD->M, swap:df->dp]
split: teach
```

```python
"""Cassette construction: fidelity proof, minimisation, mutation, rendering."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from rdflib import Graph
from rdflib.namespace import OWL, RDF

from . import minimise, mutate
from .mcnio import MCNTool, graphs_equal
from .mcnline import Document

IGNORE = {OWL.NamedIndividual}          # both sides assert this; not informative

@dataclass
class Cassette:
    spec: dict
    mcn_full: str = ""
    mcn_min: str = ""
    fidelity: str = "unverified"        # exact | diff | unverified
    fidelity_detail: str = ""
    outcomes: list = field(default_factory=list)
    problems: list = field(default_factory=list)

    @property
    def id(self) -> str: return self.spec["id"]
    @property
    def lens(self) -> str: return self.spec["lens"]
    @property
    def split(self) -> str: return self.spec.get("split", "teach")

def build(spec_path: Path, tool: MCNTool, cfg, cb) -> Cassette:
    from .doctrine import Problem
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    c = Cassette(spec)
    src = Path(spec["source"])
    gold = Graph().parse(str(src), format="turtle")

    # ---- 1. obtain MCN ------------------------------------------------- #
    if spec.get("gold", "auto") == "inline":
        c.mcn_full = spec["mcn"]
    else:
        enc = tool.encode(gold, spec.get("encode_hints", {}))
        if enc is None:
            c.problems.append(Problem("error", "cassette.no-encoder",
                f"{c.id}: gold=auto but the adapter has no encoder",
                "set gold: inline and paste verified MCN, or supply an encoder"))
            return c
        c.mcn_full = enc

    # ---- 2. fidelity: the MCN must denote the real example -------------- #
    res = tool.decode(c.mcn_full)
    if not res.ok:
        c.fidelity = "unverified"
        c.problems.append(Problem("error", "cassette.decode-failed",
            f"{c.id}: full MCN does not decode: {res.codes()}"))
        return c
    same, diff = graphs_equal(res.graph, gold, IGNORE)
    c.fidelity = "exact" if same else "diff"
    c.fidelity_detail = diff
    if not same and not spec.get("allow_source_diff"):
        c.problems.append(Problem("error", "cassette.not-isomorphic",
            f"{c.id}: decoded MCN differs from {src}", diff))
        return c

    # ---- 3. minimise to the teaching core ------------------------------ #
    focus = minimise.Focus(
        predicates=tuple(cb.expand(p) for p in spec["focus"].get("predicates", [])),
        types=tuple(cb.expand(t) for t in spec["focus"].get("types", [])),
        subjects=tuple(spec["focus"].get("subjects", [])),
    )
    doc = Document(c.mcn_full)
    header = {i for i, l in enumerate(doc.lines) if l.lstrip().startswith(("@", "%"))}
    base = ""
    minimised = minimise.ddmin(doc, tool, focus, base, protected=header)
    c.mcn_min = minimised.text()
    if not minimise.teaches(minimised, tool, focus, base):
        c.problems.append(Problem("error", "cassette.minimise-broke-focus",
            f"{c.id}: minimised form no longer satisfies focus"))
        return c

    # ---- 4. mutate ------------------------------------------------------ #
    c.outcomes = mutate.run(minimised, tool, only=spec.get("mutations"),
                            run_shacl=cfg.get("run_shacl", True))
    for o in c.outcomes:
        if not o.applied:
            c.problems.append(Problem("error", "cassette.mutation-inapplicable",
                f"{c.id}: mutation {o.mutation.id} matched nothing in the minimised MCN",
                "the cassette does not exercise that distinction; drop it or pick another source"))
        elif o.verdict == "silent" and "smell" not in spec:
            c.problems.append(Problem("warn", "cassette.silent-mutation",
                f"{c.id}: {o.mutation.id} produces NO diagnostic",
                f"nothing downstream catches '{o.mutation.description}'. "
                f"Add a `smell:` to lens {c.lens}, or a shape to constraints.ttl."))
    return c

def render(c: Cassette, cb) -> str:
    lines = [f"{c.id}  {c.spec['title']}",
             "NL: " + " ".join(c.spec["nl"].split()),
             "MCN:"]
    lines += ["  " + l for l in c.mcn_min.rstrip("\n").split("\n") if l.strip()]
    lines.append("WHY: " + " ".join(c.spec["why"].split()))
    for o in c.outcomes:
        if not o.applied:
            continue
        tag = o.primary() or "NOT CAUGHT"
        lines.append(f"NOT: {o.mutation.id} -> {tag}")
    return "\n".join(lines) + "\n"

def select(cassettes, claims: set[str], stats, per_lens_cap: int = 6) -> list:
    """Greedy set cover: fewest cassettes covering every teaching claim,
    tie-broken by corpus frequency of the predicates they exercise."""
    chosen, remaining = [], set(claims)
    pool = [c for c in cassettes if c.split == "teach"]

    def value(c):
        got = set(c.spec.get("teaches", [])) & remaining
        freq = sum(stats.predicate_freq.get(p, 0)
                   for p in c.spec["focus"].get("predicates", []))
        return (len(got), freq, -len(c.mcn_min))

    per_lens = {}
    while remaining and pool:
        pool.sort(key=value, reverse=True)
        pick = next((c for c in pool if per_lens.get(c.lens, 0) < per_lens_cap), None)
        if pick is None or not (set(pick.spec.get("teaches", [])) & remaining):
            break
        chosen.append(pick)
        per_lens[pick.lens] = per_lens.get(pick.lens, 0) + 1
        remaining -= set(pick.spec.get("teaches", []))
        pool.remove(pick)
    return chosen, sorted(remaining)
```

Rendered output, ~150 tokens:

```
C-IND-01  A datum needs the class mapping it defers to
NL: Loan records arrive as JSON with loanId and principal. Map the loan itself into fin:Loan.
MCN:
  %M MS
  Map_Loan_Class xt :Loan
  Map_Loan MD df Map_Loan_Class c Loan r loanId
WHY: MD individuates; it cannot do so before the class axiom exists, so it defers to the mapping that establishes the T-Box (Axiom 2.7a).
NOT: drop:df -> lint.MD-no-df
NOT: retype:MD->M -> NOT CAUGHT
NOT: swap:df->dp -> NOT CAUGHT
```

`NOT CAUGHT` appearing twice here is the tool telling you where the lens prose has to work. Neither dropping the individuation claim nor swapping deferral for dependency is machine-detectable, so `L-IND` must carry both as smells.

---

### 5.8 `mtp/lens.py` — render, with the derived halves derived

```yaml
# lenses/L-IND.yaml
id: L-IND
title: Individuation, deferral, precedence
order: 2                      # display order; also prompt-assembly priority
question: When does a datum become an individual, and what must happen first?
anchors: [mork:Datum, mork:deferredMapping, mork:dependentMapping,
          mork:broaderApplicative, mork:precedes, mork:yieldConcept]
covers:                       # satisfies the L0 generator's coverage gate
  - "gci:Datum-requires-TBox"
  - "subprop_inverse:*"
rules:
  - A Datum claims "this record becomes an individual". Everything else follows.
  - "df points at whatever establishes the class: xt or bt, possibly transitively."
  - Composition is structural (cb/cn); applicative is contextual (ap). ap needs xr/xi.
  - "dp means: run first, but I will not consume your output. Reach it via y."
  - Never assert pr/sp/rif. They are derived from the structure you wrote.
smells:
  - two nodes each df the other (df is symmetric; you probably meant dp)
  - a Datum whose df chain never reaches a T-Box match
  - ap and cn pointing at the same node (double-counts the edge)
  - MD dropped to M because "the class already exists" (it still individuates)
  - df used where dp was meant; nothing detects this, so state your intent in a note
```

```python
"""Lens rendering. Curated: question, rules, smells. Derived: everything else."""
from __future__ import annotations

from pathlib import Path

import yaml

from . import template

def load(dir_path: Path) -> list[dict]:
    return sorted((yaml.safe_load(p.read_text(encoding="utf-8"))
                   for p in sorted(dir_path.glob("L-*.yaml"))),
                  key=lambda d: (d.get("order", 99), d["id"]))

def codes_line(lens_id: str, part, cb, facts, stats) -> str:
    """Codes this lens owns, grouped by kind, ordered by corpus frequency."""
    members = part.by_lens.get(lens_id, [])
    types, obj, data = [], [], []
    for iri in members:
        code = cb.code_for(iri)
        t = facts.terms.get(iri)
        if not code or not t or t.deprecated:
            continue
        rank = stats.predicate_freq.get(iri, 0) + stats.type_freq.get(iri, 0)
        bucket = types if code[0].isupper() or code.startswith(".") else \
                 (data if "data_property" in t.kinds else obj)
        bucket.append((-rank, code))
    fmt = lambda b: " ".join(c for _, c in sorted(b))
    parts = [p for p in (fmt(types), fmt(obj), fmt(data)) if p]
    return "CODES: " + " | ".join(parts)

def cooccurrence_lines(lens_id: str, part, facts, cb) -> list[str]:
    """MUST CO-OCCUR rows, read off GCIs whose mentions this lens owns."""
    rows = []
    owned = set(part.by_lens.get(lens_id, []))
    for aid, ax in sorted(facts.axioms.items(), key=lambda kv: kv[1].mcn):
        if ax.kind not in ("gci", "completeness"):
            continue
        mentioned = [m for m in ax.mentions if m in owned]
        if not mentioned:
            continue
        if len(set(ax.mentions) & owned) < max(1, len(ax.mentions) // 3):
            continue                                  # peripheral mention; skip
        rows.append("  " + ax.mcn)
    return rows

def caught_lines(lens_id: str, cassettes) -> tuple[list[str], list[str]]:
    caught, silent = {}, {}
    for c in cassettes:
        if c.lens != lens_id:
            continue
        for o in c.outcomes:
            if not o.applied:
                continue
            (silent if o.verdict == "silent" else caught) \
                .setdefault(o.mutation.id, o.primary() or o.mutation.description)
    return (sorted(f"{k} -> {v}" for k, v in caught.items()),
            sorted(f"{k} ({v})" for k, v in silent.items()))

def render(spec: dict, part, cb, facts, stats, cassettes, ctx) -> str:
    T = lambda s: template.render(s, ctx)
    caught, silent = caught_lines(spec["id"], cassettes)
    mine = [c.id for c in cassettes if c.lens == spec["id"] and c.split == "teach"]

    out = [f"{spec['id']}  {spec['title']}",
           "Q: " + T(spec["question"]),
           codes_line(spec["id"], part, cb, facts, stats),
           "RULES"]
    out += [f" {i}. {T(r)}" for i, r in enumerate(spec["rules"], 1)]

    co = cooccurrence_lines(spec["id"], part, facts, cb)
    if co:
        out += ["MUST CO-OCCUR"] + co
    if spec.get("smells"):
        out += ["SMELLS"] + [f" - {T(s)}" for s in spec["smells"]]
    if caught:
        out += ["CAUGHT: " + "; ".join(caught)]
    if silent:
        out += ["NOT CAUGHT (state your intent in a note): " + "; ".join(silent)]
    if mine:
        out += ["SEE: " + " ".join(sorted(mine))]
    return "\n".join(out) + "\n"

def check(spec: dict, part, cassettes, silent_ids: set[str]):
    """Every silent mutation in this lens must be addressed by a smell."""
    from .doctrine import Problem
    problems = []
    smell_blob = " ".join(spec.get("smells", [])).lower()
    for mid in sorted(silent_ids):
        token = mid.split(":")[-1].replace("->", " ").lower()
        if not any(t in smell_blob for t in token.split()):
            problems.append(Problem("error", "lens.silent-unaddressed",
                f"{spec['id']}: mutation {mid} is undetectable and no smell mentions it",
                "add a SMELLS entry, or add a SHACL shape so the machine catches it"))
    if not any(c.lens == spec["id"] and c.split == "teach" for c in cassettes):
        problems.append(Problem("error", "lens.no-cassette",
            f"{spec['id']} has no teaching cassette"))
    return problems
```

Generated `out/lenses/L-IND.txt`:

```
L-IND  Individuation, deferral, precedence
Q: When does a datum become an individual, and what must happen first?
CODES: MD MX | df cb cn ap dp hy tp it y | c ix
RULES
 1. A Datum claims "this record becomes an individual". Everything else follows.
 2. df points at whatever establishes the class: xt or bt, possibly transitively.
 3. Composition is structural (cb/cn); applicative is contextual (ap). ap needs xr/xi.
 4. dp means: run first, but I will not consume your output. Reach it via y.
 5. Never assert pr/sp/rif. They are derived from the structure you wrote.
MUST CO-OCCUR
  !C MD < df>(xt>.T | bt>.T)
  !G ap>M & ~xr>.T < .N
SMELLS
 - two nodes each df the other (df is symmetric; you probably meant dp)
 - a Datum whose df chain never reaches a T-Box match
 - ap and cn pointing at the same node (double-counts the edge)
 - MD dropped to M because "the class already exists" (it still individuates)
 - df used where dp was meant; nothing detects this, so state your intent in a note
CAUGHT: drop:df -> lint.MD-no-df; drop:xr -> lint.ap-no-xr; both:cb+cn -> lint.cn-ap-same-node
NOT CAUGHT (state your intent in a note): retype:MD->M (drop the individuation claim); swap:df->dp (hard prerequisite where context consumption was meant)
SEE: C-IND-01 C-IND-02 C-IND-03
```

~330 tokens, and the only hand-written parts are `Q`, `RULES` and `SMELLS`.

---

### 5.9 `mtp/routing.py` and `mtp/evalset.py`

```python
"""Routing table: task/signal -> lenses + cassettes, with reachability gates."""
from __future__ import annotations

from pathlib import Path
import yaml

def build(src: Path, lenses, cassettes, cfg):
    from .doctrine import Problem
    spec = yaml.safe_load(src.read_text(encoding="utf-8"))
    ids = {l["id"] for l in lenses}
    problems, table = [], {"tasks": {}, "signals": {}}

    for name, entry in sorted((spec.get("tasks") or {}).items()):
        want = list(entry.get("lenses", []))
        for l in want:
            if l not in ids:
                problems.append(Problem("error", "routing.unknown-lens",
                                        f"task '{name}' routes to unknown lens {l}"))
        cs = [c.id for c in cassettes
              if c.lens in want and c.split == "teach"][: cfg.get("cassettes_per_task", 4)]
        if not cs:
            problems.append(Problem("error", "routing.no-cassettes",
                                    f"task '{name}' has no cassettes for {want}"))
        table["tasks"][name] = {"lenses": want, "cassettes": cs,
                               "budget_tokens": entry.get("budget_tokens")}

    for sig, entry in sorted((spec.get("signals") or {}).items()):
        table["signals"][sig] = {"add_lenses": entry.get("add_lenses", [])}

    reachable = {l for t in table["tasks"].values() for l in t["lenses"]}
    reachable |= {l for s in table["signals"].values() for l in s["add_lenses"]}
    for l in sorted(ids - reachable):
        problems.append(Problem("error", "routing.unreachable",
            f"lens {l} is reachable from no task or signal",
            "add a task/signal, or fold the lens into another"))
    table["fallback"] = {"lenses": sorted(ids)}       # degrade to all-lenses
    return table, problems
```

```python
"""Held-out evaluation tasks, emitted from cassettes marked split: eval."""
from __future__ import annotations

import json
from pathlib import Path

def emit(cassettes, out_dir: Path, cfg):
    from .doctrine import Problem
    problems = []
    teach_sources = {c.spec["source"] for c in cassettes if c.split == "teach"}
    out_dir.mkdir(parents=True, exist_ok=True)
    per_lens = {}

    for c in sorted((x for x in cassettes if x.split == "eval"), key=lambda x: x.id):
        if c.spec["source"] in teach_sources:
            problems.append(Problem("error", "eval.leakage",
                f"{c.id} shares source {c.spec['source']} with a teaching cassette",
                "pick a different source file for the eval cassette"))
        per_lens[c.lens] = per_lens.get(c.lens, 0) + 1
        task = {
            "id": c.id,
            "lens": c.lens,
            "prompt": " ".join(c.spec["nl"].split()),
            "gold_mcn": c.mcn_min,
            "gold_source": c.spec["source"],
            "scoring": {
                "predicate_f1": True,
                "lint_clean_required": True,
                "must_contain_predicates": c.spec["focus"].get("predicates", []),
                "must_not_assert": c.spec.get("must_not_assert", []),
                "unsafe_confidence": c.spec.get("expect_uncertain", False),
            },
        }
        (out_dir / f"{c.id}.json").write_text(
            json.dumps(task, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    minimum = cfg.get("min_eval_per_lens", 2)
    for l, n in sorted(per_lens.items()):
        if n < minimum:
            problems.append(Problem("error", "eval.thin",
                                    f"lens {l} has {n} eval cassettes, minimum {minimum}"))
    return problems
```

---

### 5.10 CLI additions

```python
def cmd_lens_build(args):
    cfg, facts, cb, doc, lock, _ = _load_all(args)
    tool = mcnio.make(cfg)                                   # In-process | Subprocess | Null
    stats = corpus.scan(_glob(cfg["corpus"]), cb.prefixes["mork"])
    part = partition.build(facts, cb, Path(cfg["partition"]))
    lenses = lensmod.load(Path(cfg["lenses_dir"]))

    cassettes, problems = [], list(part.problems)
    problems += partition.check_pins(part, lock)
    for p in sorted(Path(cfg["cassettes_dir"]).glob("C-*.yaml")):
        c = cassette.build(p, tool, cfg, cb)
        cassettes.append(c); problems += c.problems

    claims = {u for l in lenses for u in l.get("covers", [])} | \
             {t for c in cassettes for t in c.spec.get("teaches", [])}
    chosen, uncovered = cassette.select(cassettes, claims, stats,
                                        cfg.get("cassettes_per_lens", 6))
    problems += [docmod.Problem("error", "cassette.claim-uncovered",
                                f"no cassette demonstrates '{u}'") for u in uncovered]

    ctx = render.build_context(facts, cb, cfg)
    silent = {}
    for c in cassettes:
        for o in c.outcomes:
            if o.applied and o.verdict == "silent":
                silent.setdefault(c.lens, set()).add(o.mutation.id)

    counter, exact = make_counter(cfg["budgets"].get("tokenizer", "o200k_base"))
    out = Path(args.out)
    rendered_l, rendered_c = {}, {}
    for spec in lenses:
        problems += lensmod.check(spec, part, cassettes, silent.get(spec["id"], set()))
        text = lensmod.render(spec, part, cb, facts, stats, chosen, ctx)
        n = counter(text)
        if n > cfg["budgets"]["lens_max"]:
            problems.append(docmod.Problem("error", "budget.lens",
                f"{spec['id']} is {n} tokens, budget {cfg['budgets']['lens_max']}"))
        rendered_l[spec["id"]] = (text, n)
    for c in chosen:
        text = cassette.render(c, cb)
        n = counter(text)
        if n > cfg["budgets"]["cassette_max"]:
            problems.append(docmod.Problem("error", "budget.cassette",
                f"{c.id} is {n} tokens, budget {cfg['budgets']['cassette_max']}"))
        rendered_c[c.id] = (text, n)

    table, rp = routing.build(Path(cfg["routing"]), lenses, chosen, cfg); problems += rp
    problems += evalset.emit(cassettes, out / "eval", cfg)

    diagnostics = _diagnostic_table(cassettes, part)
    provisional = isinstance(tool, mcnio.NullTool)
    ...  # write files, manifest with provisional flag, print problems
```

```python
def _diagnostic_table(cassettes, part) -> dict:
    """diagnostic code -> doctrine fragment + wrong/right micro-example.

    This is the repair-loop input: generated, never written by hand.
    """
    table = {}
    for c in sorted(cassettes, key=lambda x: x.id):
        for o in c.outcomes:
            if not o.applied or o.verdict == "silent":
                continue
            key = o.primary()
            entry = table.setdefault(key, {
                "lens": c.lens, "teaches": o.mutation.teaches,
                "fragment": o.mutation.description, "examples": []})
            if len(entry["examples"]) < 2:
                entry["examples"].append({"wrong": o.line_after, "right": o.line_before,
                                          "cassette": c.id})
    return table
```

`out/diagnostics.json`:

```json
{
  "lint.ap-no-xr": {
    "lens": "L-IND",
    "teaches": "pair.cb-ap",
    "fragment": "applicative context without the joining relation",
    "examples": [{
      "wrong": "Map_Principal ap Map_Loan cb Map_Loan c LoanPrincipal r loanId",
      "right": "Map_Principal ap Map_Loan cb Map_Loan xi :principal c LoanPrincipal r loanId",
      "cassette": "C-IND-02"
    }]
  }
}
```

---

## 6. Gates

| Gate | Fires when | Severity |
|---|---|---|
| `partition.empty` / `unknown-lens` | a lens owns no terms | error |
| `partition.membership-changed` | new terms absorbed / explicit term vanished | warn / error |
| `cassette.not-isomorphic` | MCN does not denote the cited source file | error |
| `cassette.decode-failed` | cassette MCN is invalid | error |
| `cassette.minimise-broke-focus` | minimisation removed the construct being taught | error |
| `cassette.mutation-inapplicable` | the cassette does not exercise a claimed distinction | error |
| `cassette.silent-mutation` | a mutation produces no diagnostic | warn → escalates |
| `lens.silent-unaddressed` | silent mutation with no matching smell | **error** |
| `lens.no-cassette` | lens has no worked example | error |
| `cassette.claim-uncovered` | a teaching claim nothing demonstrates | error |
| `routing.unreachable` | a lens no task can load | error |
| `eval.leakage` | eval cassette shares a source with a teaching cassette | error |
| `eval.thin` | fewer than 2 eval cassettes per lens | error |
| `budget.lens` / `budget.cassette` | over token budget | error |
| `adapter.absent` | no decoder → manifest `provisional: true` | error at publish |

`lens.silent-unaddressed` is the interesting one: it makes it impossible to ship a lens that ignores a mistake nothing else catches. Two legitimate ways to satisfy it — write the smell, or write the SHACL shape — and both are improvements.

---

## 7. What re-running does when things change

| Change | Response |
|---|---|
| New object property under an assigned subtree | absorbed silently; `partition.membership-changed` warns with the term name; `CODES:` line updates |
| New GCI mentioning L-GEN terms | new `MUST CO-OCCUR` row in L-GEN; L0's `axiom.unowned` already forced a `covers` decision |
| `constraints.ttl` gains a shape | previously-silent mutation becomes `caught-shacl`; moves from `NOT CAUGHT` to `CAUGHT`; the now-redundant smell is reported as removable |
| A shape is loosened | mutation goes silent; `lens.silent-unaddressed` fails until prose is written |
| Corpus gains a real mapping scheme | frequency reorders `CODES:`; cassette selection may swap a cassette for a more representative one |
| Decoder changes its lint codes | `diagnostics.json` keys change; pinned diagnostic codes mismatch → error with the old/new pair |
| Example file edited | `cassette.not-isomorphic` fails; regenerate or re-pin |

---

## 8. Build order

1. `mcnio` protocol + `NullTool`, `mcnline`, `corpus`. Produces `stats.md` immediately, which tells you which lenses to write first.
2. `partition.yaml` + gate. Cheap, and it immediately proves the L0 generator's `deferrals` are honest.
3. `cassette.build` fidelity path only (no minimisation, `gold: inline`). Three cassettes from `loan_mapping.ttl` and `UncertainMappings.ttl`.
4. `mutate` with six operators (`drop:df`, `drop:xr`, `swap:cb->ap`, `swap:df->dp`, `retype:MU->M`, `both:cb+cn`). **The silent-set report from this step is the most valuable output in the whole design** — it tells you what the machine cannot catch, which is exactly what the prose must cover, and it will very likely surface gaps in `constraints.ttl` on first run.
5. `minimise`. Big token win; needs a working decoder.
6. `lens.render` for L-IND and L-GEN (highest corpus frequency, highest error rate).
7. `routing`, `evalset`, `diagnostics.json`.
8. Remaining seven lenses, cassettes to coverage, all gates on in CI.

CI:

```yaml
- run: python -m mtp.cli check --out out              # L0 drift (existing)
- run: python -m mtp.cli lens-check --out out         # partition, fidelity, gates
- run: python -m mtp.cli lens-build --pack-version ${{ github.ref_name }} --out out
- run: git diff --exit-code out/
- run: python -m mtp.cli eval-report --out out        # regression vs previous pack
```

The last step closes the loop from the original plan: the eval suite and the teaching material are generated from one source, so a pack that teaches better also measures better, and a pack that only *looks* better fails the diff.

----------------------------------
EOF

## Verdict

They are complementary, and mostly so because they act on **different objects**. MORK's community detection, alignment profunctor, projection matrix and convergence theorem are all machinery for learning *the domain mapping* (which field means which ontology element). The Teaching Pack is machinery for learning *the notation* (how to say any mapping at all in MORK). One is object-level, the other meta-level.

But there are three places where they genuinely overlap in mechanism, and five where they contend for the same resources or corrupt each other's signals. The contentions are the interesting part, because most of them are silent failures rather than errors.

---

## The two loops are orthogonal but easily confused

|  | Domain loop (the paper) | Notation loop (the essay) |
|---|---|---|
| What is learned | field → ontology element | MORK vocabulary and structural discipline |
| What accumulates | community weights, projection counts, validated mappings | errata card, cassette corpus, lint→doctrine table |
| Changes when | new source data arrives | `Mork.ttl` changes, or model version bumps |
| Feedback latency | days (human review, Stage 5) | milliseconds (lint / GCI / SHACL) |
| Scope of benefit | per deployment, per domain | amortised across all deployments |
| Metric | ρ(t), fraction of fields needing LLM | first-pass lint-clean rate |
| Cold-start value | low (20–40% per §4 table) | high |
| Mature-state value | high (90–98%) | low, nearly constant |

That last pair is the cleanest statement of complementarity: **the Teaching Pack raises the intercept, convergence raises the slope.** MTP matters most precisely where the convergence theorem gives you least — run 0, no validated mappings, no communities detected, only axiom intent available. Conversely, once ρ(t) is small, MTP investment depreciates because the LLM is invoked rarely. They are temporally staggered, not competing.

---

## Genuine conflicts

**1. Confidence-channel contamination — the most serious.** MORK has one uncertainty vocabulary (`weighting`, `hypothesisMapping`, `UncertainMapping`, `llmConfidence`), and the essay's invariant 6 routes *all* model doubt into it. But there are two unrelated doubts:

- *epistemic-domain*: "I don't know whether `PCIDSS` is a RegulatoryPeril" — this is legitimate evidence, and it must feed the projection matrix and Proposition 2.12's monotonicity.
- *epistemic-notation*: "I don't know whether this is `ap` or `cb`" — this is evidence about the *model*, not the domain.

If the second lowers `weighting`, you corrupt the confidence propagation (Prop 5.4) and, worse, you pollute the convergence signal, since a validated-but-low-weighted mapping is what the projection counts are built from. A rejected notation error also looks, to the projection matrix, like a rejected *mapping hypothesis* — which is straightforwardly wrong: the target was right, the encoding was wrong.

Recommendation: keep `weighting`/`llmConfidence` strictly for domain confidence; express notation uncertainty only through the CURIE escape plus a note, or a separate annotation that the lint layer consumes and the errata pipeline aggregates, and which is *stripped before* any update to projection statistics. The two learning loops must be fed from disjoint signals or both degrade.

**2. Token budget and prompt-cache ordering.** The paper already flags that a moderately complex JSON schema alone is 15–30k tokens, before ontology context. The Graph-RAG section then requires six retrieval families (class profile, property context, community lookup, existing mappings, templates, conflict detection). The essay's 2–4.5k resident pack sits in the same window. Nominally the essay *helps* here — its whole tiering argument is "spend fewer tokens on doctrine so you can spend more on grounding" — but two constraints follow:

- Prefix caching requires the stable bytes first. Retrieved graph context is volatile per-field, so the only viable order is `[frozen pack][profile][lenses][cassettes][retrieved context][task]`. Interleaving retrieved class profiles with doctrine, which is the natural authoring instinct, destroys the cache and the essay's cost argument with it.
- Lens loading and retrieval loading must share one budget with explicit precedence. When they compete, grounding should win: a model that has the actual class axiom profile and is slightly unsure about `br` vs `ba` produces a repairable graph; a model with perfect doctrine and a hallucinated target IRI produces a plausible wrong mapping.

**3. The CURIE escape must not extend to target IRIs.** The essay's escape hatch — "use a CURIE in code position and flag it in a note" — makes partial MORK-vocabulary knowledge safe. That is correct and important. But it must be stated as applying to *MORK meta-vocabulary only*. Invented target-ontology IRIs break Proposition 6.10 (retrieval soundness) and the whole grounding premise; Stage 3 will usually catch them, but an invented IRI that happens to resolve to a real-but-wrong entity will not be caught, and will then be counted as a validated projection. The kernel should read: target entities come from retrieval or from `MU`, never from the escape.

**4. Metric confounding.** If you change the pack while measuring ρ(t), you cannot attribute improvement. Convergence measurements must hold `mtp-version` fixed; pack evaluations must hold the graph fixed. Both documents already want provenance (`ConstraintProvenance` with `llmModelId`; the essay's `mtp-version`, `profile-hash`, `lenses-loaded`) — these should be a single record, and convergence statistics should be stratified by pack version or they are uninterpretable.

**5. The repair loop cannot teach mapping quality.** The essay's central cost argument — "teach recognition + repair, the checker catches the rest" — is sound for form, and the paper's own Remark 4.2 explains why it does not extend to semantics: the validation gate checks structural well-formedness and ontological consistency, not whether the mapping captures the intended meaning (false-approval rate `p_val > 0`). So there are two feedback loops with latencies differing by five or six orders of magnitude, and only the slow one carries domain truth. Consequence: do not expect repair-loop investment to accelerate convergence, and do not let lint-clean rate stand in for mapping correctness. The essay's eval harness half-acknowledges this with "unsafe-confidence rate", which is the right instinct; it needs a companion metric scored against *human* Stage-5 decisions, not against gold graphs.

---

## Overlaps worth exploiting rather than resolving

**Templates and cassettes are the same idea at two levels.** `templateMapping` / `compositeNarrowerTemplate` exist to reduce generation volume and constrain output space — exactly the stated purpose of cassettes. The natural move is to generate the cassette corpus from human-approved, high-weighted template mappings in the live graph, so pedagogy is downstream of practice. The one thing to preserve is the split the essay insists on: cassettes are frozen and hash-pinned for reproducibility, templates are retrieved live. Never let a frozen cassette be mistaken for a current pattern, or the model will cite superseded structure that `supersedes` chains have already retired.

**The errata card is structurally the projection matrix.** Both are "accumulate validated outcomes and change future behaviour without touching weights." Given that, the errata card should be governed as a MORK artefact in its own right — `ConstraintProvenance`-style creator/created/review status, `supersedes` for revisions, a named graph, and no writes to `:active` without human approval. The essay asks for this implicitly ("provenance, review status, version"); making it literal means the pedagogy inherits the paper's audit guarantees for free, and lets you answer "which teaching configuration produced this class of bad mapping" with the same SPARQL you already use for mappings.

**Minimal pairs are the community acceleration factor for notation.** The paper's argument that recognising one community member bootstraps `M−1` others is exactly why a contrast table beats independent definitions: `cb`/`ap`, `xr`/`xi`, `MS`/`MR` are co-occurring members of a doctrinal community, and learning the boundary teaches both. This is worth stating in the pack because it justifies the format choice rather than leaving it as taste.

**FCA on the repair log validates lens boundaries.** The paper's own apparatus applies directly to its pedagogy: take `G` = repair events, `M` = MORK terms and lint codes, `I` = "term implicated in event". The formal concepts' intents are the empirically coherent doctrine units. Use this as a *diagnostic* on hand-written lenses, not a generator — co-failure is not doctrinal dependency — but the Galois diagnostic transfers cleanly: if `γ(f(L)) ⊃ L`, the lens is missing terms that fail alongside it; if `γ(f(L)) ⊂ L`, the lens is carrying terms nothing ever needs from it. That turns the essay's CI gate ("every term in exactly one lens") from a hand-maintained partition into a checkable one.

**Routing already consumes the alignment pipeline.** The signal `target IRI absent → +L-UNC, +L-TBX` is precisely a read of the paper's thresholding step (gap > δ deterministic / > ε LLM-assisted / else human). The essay is right to keep routing static and non-semantic — there is a bootstrapping problem in using MORK competence to select MORK teaching, and routing must work at cold start before any graph exists — but the *ambiguity type* emitted by the scoring pipeline is a legitimate, deterministic routing input that costs nothing.

**Shard the pack by agent role.** The paper's access-control table constrains each agent's *data* perimeter by named graph; lens routing constrains its *doctrine* perimeter. These should be symmetric and co-specified: Intent-Agent gets `L-INT` and cannot see ontology IRIs *or* box-match doctrine — which structurally enforces Proposition 6.1's layer independence at the pedagogy level, not just the data level. A monolithic pack quietly breaks that: an Intent-Agent that has read the box-match lens will eventually use it.

---

## What the essay supplies that the paper is missing

The paper's Principle 4 bounds LLM non-determinism from the *output* side — structured schemas, validation gates, retry limits. It has nothing on the *input* side: no account of what instruction the model received, no reproducibility of conditioning, and no detection of behaviour change under a frontier model upgrade. Given that the convergence theorem's Assumption A6 and Proposition 2.12 both depend on witnesses not expiring (Prop 2.33: "an observation valid at time t remains valid at t+1"), a silent model-version behaviour change is a direct threat to the theorem's premises, and the essay's eval-harness-on-every-model-bump is the only proposed mechanism that would catch it. That is a real gap filled, not an overlap.

---

The clean separation is: **two orthogonal convergence processes, sharing one provenance record and one token budget, and required to feed from disjoint confidence signals.** The failure modes are all at those three shared points, not in the methods themselves.


# Remediation Plan: MORK Domain Learning × MORK Notation Teaching

## Scope and design constraint

Five conflicts, all located at the three points where the two loops share infrastructure: the confidence channel, the prompt budget, and the provenance record. None require changing the calculus or the pedagogy — they require separating signals that are currently conflated and making two implicit properties checkable.

One constraint shapes every proposal below. The paper's own Limitations section identifies adoption complexity as a live risk: "the vocabulary is inherently complex because the problem it models is inherently complex." Every addition here is therefore justified against a specific silent-failure mode, and the total delta is held to one class, six properties, one enumeration, three Meta-SHACL shapes, one MCN code, and three kernel clauses. Where a documentation change suffices, I have not proposed vocabulary.

| # | Conflict | Core remedy | Primary artefact |
|---|---|---|---|
| R1 | Confidence-channel contamination | Separate domain from notation confidence; typed rejection reasons; explicit projection-update filter | `Mork.ttl`, L0 kernel, Stage 5 |
| R2 | Budget and cache contention | Canonical segment order with declared cache boundary; budget precedence rule; section-scoped schema windows | Prompt assembler, Context Serialiser |
| R3 | CURIE escape over-generalises to target IRIs | Three typed emission positions; retrieval manifest; groundedness shapes | L0 kernel, Meta-SHACL M-family |
| R4 | Metric confounding | Single `GenerationContext` record; stratification policy; two-sided change control | `ConstraintProvenance`, eval harness |
| R5 | Repair loop mistaken for semantic gate | "Lint-clean ≠ correct" invariant; paired metrics against Stage 5; calibration gate; retrospective challenge sweep | L0 kernel, metrics, scheduled job |

---

## R1 — Confidence-channel contamination

### Context from the paper

MORK has one confidence channel and it is load-bearing in three places. `weighting` (xsd:integer, 0–100) carries static confidence; derived confidence propagates as `conf(m) = conf_local(m) × min(conf(m₁)…conf(mₙ))`, with Proposition 5.4 guaranteeing that a composite never exceeds any component. `llmConfidence` (xsd:decimal) sits on `ConstraintProvenance`. Meta-SHACL shape C2 raises a warning when derived confidence falls below threshold.

More importantly, the convergence theorem is built on *validated mapping counts*. Phase 2 computes `P(t | C_j) = (count of validated mappings from C_j members to t + α) / (total + α|T|)`, and Proposition 2.12's monotonicity argument turns on the claim that "each validated mapping confirming C* → t* increases the numerator" while incorrect targets gain nothing. Theorem 4.1(ii) states the negative side explicitly: validated mappings confirm only t*.

### Context from the essay

Invariant 6 of the kernel reads: *"How confident am I? <100 → w, and if guessing, MU."* The stated rationale is strong and correct — MORK's first-class uncertainty "converts hallucination into a reviewable artefact," and the essay judges this single habit "worth more than 20k tokens of vocabulary." The eval harness includes *unsafe-confidence rate*: mappings asserted confidently where `MU` was warranted.

### Why they collide

The kernel routes *all* model doubt into one channel, but the model has two unrelated doubts:

- **Domain doubt** — "I don't know whether `PCIDSS` denotes a RegulatoryPeril." This is legitimate evidence about the world and must reach the projection matrix.
- **Notation doubt** — "I don't know whether this is `ap` or `cb`." This is evidence about the model, and must reach the errata pipeline.

Two consequences, both silent:

1. **Propagation distortion.** Notation doubt lowering `weighting` suppresses derived confidence through the DAG via the `min()` in Prop 5.4, understating a domain-correct mapping and tripping shape C2 into spurious human review — while the actual defect is a structural error the lint layer would have caught for free.
2. **Projection poisoning — the serious one.** A Stage 5 rejection is recorded as a bare `userDeclined` annotation with no reason code. If projection counting reads rejection as "this target was wrong," then a rejection for a *notation* fault teaches the matrix a false negative about a correct `(c, p)` pairing. This inverts Theorem 4.1(ii): the evidence stream now contains negative signal about correct targets, which is precisely the condition the monotonicity proof excludes by assumption.

Note also that `MU` / `UncertainMapping` as defined in the essay's minimal-pair table means *target missing or unknown* — a domain condition. That is correct and should stay in the domain loop. Notation doubt must not produce `MU`.

### Remediation

**1a. Normative narrowing (documentation only).** Add scope notes: `weighting`, `llmConfidence` and `hasIntentConfidence` express confidence in the *semantic claim* — that this source element means this target element. They never express confidence in the MORK encoding of that claim. `UncertainMapping` and `mappingRecommendation` likewise remain domain-side.

**1b. A separate notation channel.** Add one annotation property:

```
mork:notationConfidence  (annotation property, range xsd:decimal [0,1])
```

Annotation property rather than data property, so it carries no OWL semantics and cannot enter confidence propagation by accident. SHACL can still validate and aggregate it — annotation triples are ordinary triples. Textual justification reuses `mappingNote`; no second note property.

MCN gains one code, `nc`, positionally and lexically distinct from `w`, so the two cannot be confused in generation.

**1c. Typed rejection reasons — the actual fix.** `userDeclined` becomes a reason-bearing assertion over a closed enumeration:

| Reason | Meaning | Feeds domain loop? | Feeds notation loop? |
|---|---|---|---|
| `WRONG_TARGET` | correct structure, wrong ontology element | yes (negative evidence) | no |
| `OUT_OF_SCOPE` | field should not be mapped | yes (suppression) | no |
| `WRONG_STRUCTURE` | right target, wrong DAG/precedence/context | no | yes |
| `WRONG_NOTATION` | right target and structure, malformed MORK | no | yes |
| `DATA_QUALITY` | source unreliable | no | no |
| `SUPERSEDED` | replaced via `supersedes` | no | no |

Enforced by a new cross-layer Meta-SHACL shape: any `userDeclined` assertion in `mappings:staging` or `:active` without a reason from the enumeration is a Violation. This is cheap to author and cheap for reviewers — it is one radio button on the Stage 5 UI.

**1d. Explicit projection-update contract.** Write the filter as a first-class, testable rule rather than leaving it implicit in whatever code aggregates validated mappings:

> A Stage 5 outcome updates `P(t | C_j)` if and only if it is an approval, or a rejection with reason `WRONG_TARGET` or `OUT_OF_SCOPE`. All other outcomes are notation-loop telemetry and must not alter any projection count, community weight, or `q_comm` value.

This one paragraph is the boundary between the two learning systems. Everything else in R1 exists to make it enforceable.

### Acceptance test

Take a mapping with a correct target and a missing `xr` under `ap` (GCI 2.14a violation). Repair it. Assert: (i) `weighting` is byte-identical before and after; (ii) no projection count, community weight or `q_comm` value differs between the two runs; (iii) the failure appears in errata telemetry. This test fails today.

---

## R2 — Budget and prompt-cache contention

### Context from the paper

The paper is explicit about the pressure: "A moderately complex JSON schema can easily produce 8,000 lines of MORK concept nodes which, serialised naively as Turtle, consumes 15–30k tokens before existing mappings and target ontology details are even added." It is equally explicit that naive truncation is unsafe: "structural source schema coherence is vital for sufficient structural context to be available when producing mappings that are compositionally correct with respect to the surrounding structure data appear in."

Against that, Graph-RAG mandates six retrieval families — class profile, property context, community lookup, existing mappings, templates, conflict detection — each serialised into the prompt by the Context Serialiser.

### Context from the essay

The tiering scheme exists to solve exactly this, and its cost argument depends on prefix caching: "Because L0+L1+L4 are byte-stable and ordered first, they sit in the provider's prefix cache. Resident teaching becomes near-free after the first call, which removes the usual pressure to under-specify." Prescribed order: `[frozen pack] [deployment profile] [lenses] [cassettes] [task]`.

### Why they collide

That order has no slot for retrieved graph context — it is folded into "task," which is doing two jobs with opposite volatility characteristics. Retrieved context changes per field; the source schema fragment changes per field; doctrine does not. The natural authoring instinct is to place a retrieved class profile next to the lens that explains how to use it, which destroys the prefix and with it the essay's entire cost argument. Separately, nothing arbitrates when lenses plus cassettes plus retrieval plus schema exceed the window.

### Remediation

**2a. Canonical segment order with a declared cache boundary.**

| Seg | Content | Volatility | Cache |
|---|---|---|---|
| 1 | L0 kernel | frozen per pack release | primary prefix |
| 2 | L1 hot codebook (omitted under constrained decoding) | frozen per pack release | primary prefix |
| 3 | L4 errata card | frozen per errata release | primary prefix |
| 4 | Deployment profile + naming policy | frozen per deployment | primary prefix |
| — | **cache boundary** | | |
| 5 | Lenses (routed) | stable per task class | secondary prefix |
| 6 | Cassettes (routed) | stable per task class | secondary prefix |
| 7 | Retrieved graph context | per field | none |
| 8 | Source schema window | per field | none |
| 9 | Task instruction | per field | none |

Segments 1–4 must be byte-identical across runs; 5–6 byte-identical per task class, so they form a secondary cacheable prefix where the provider supports multiple breakpoints. Segments 7–9 are never cacheable and should be ordered last.

**2b. Budget precedence when over window.** Shed in this order:

1. Cassettes (most redundant with lenses)
2. L1 codebook — if and only if constrained decoding is active
3. Lens bodies reduced to *Rules* and *Mandatory co-occurrences* only; drop smell tests and pointers
4. Narrow the source schema window (2c)
5. Retrieved target context for in-scope candidates — **last resort**
6. L0 kernel — never

The ranking follows from asymmetric recoverability. Doctrine failures are lint-repairable at ~40 tokens per round; grounding failures produce confidently wrong mappings that Stage 3 may pass and that then poison the projection matrix. Grounding beats doctrine whenever they compete.

**2c. Section-scoped schema windows.** Rather than serialising the whole schema, for the field under consideration include: its full `compositeNarrower` subtree; the ancestor chain to the root; sibling *names and datatypes only*. This is not a compromise — it is precisely what the paper's own scoring pipeline needs. Definition 2.1's `q_struct` is the containing section, and community assignment operates on the section signature. The window preserves exactly the structural coherence the paper demands, at a fraction of full-schema cost.

**2d. Move conflict detection out of the prompt.** Meta-SHACL shape C1 already performs cross-instance conflict detection deterministically at Stage 3. Including it as prompt context spends volatile tokens to duplicate a free check. Drop it from retrieval; let Stage 3 catch conflicts and the repair loop teach them.

**2e. Instrument per segment.** Report the essay's *tokens per decoded triple* split by segment. A segment with high cost and no measurable effect on first-pass lint-clean or semantic F1 is a candidate for deletion; without per-segment attribution, budget decisions stay guesswork.

### Acceptance test

Two consecutive runs on different fields of the same schema achieve a primary-prefix cache hit on segments 1–4 and a secondary hit on 5–6. An over-budget run degrades according to 2b, logs which tier was shed, and never drops retrieved candidate context while cassettes remain loaded.

---

## R3 — CURIE escape scoping

### Context from the paper

Proposition 6.10 states retrieval soundness: "Every IRI in the serialised context returned by a SPARQL template exists in the knowledge graph… SPARQL queries return only bindings matching existing triples. Templates do not construct new IRIs." Principle 3 requires that "LLM agents do not generate from their training data alone." Stage 3 validates the generated graph against the target ontology.

But note what Prop 6.10 actually guarantees: soundness of *retrieval output*, not of model *input reproduction*. An IRI invented by the model that happens to resolve to a real-but-semantically-wrong entity satisfies every existence check at Stage 3 and proceeds to compilation.

### Context from the essay

The output contract closes with: *"If you need a term you don't have a code for, use a CURIE in code position and flag it in a note — do not approximate with a code that means something else."* The justification is sound and I agree with it: "A model that knows 40 codes and escapes the rest is correct and reviewable. A model that knows 200 codes badly is not."

### Why they collide

The clause says "in code position," but a model generalises the *permission* rather than the *position*. Read at face value alongside invariant 6's "never invent a target IRI to look complete," the instructions are in tension, and the resolution is ambiguous in the one case that matters — because `bt` plus `c "#Name"` legitimately mints target names. Minting is a first-class MORK operation. So "never invent an IRI" is both too blunt and, as stated, contradicted by the vocabulary.

### Remediation

**3a. Three typed emission positions in the kernel.** Replace the single clause with:

> **Code position** (MORK meta-vocabulary). If no code is known, emit a CURIE and a note. Always permitted.
>
> **Reference position** (`xt`, `xr`, `xi`, `xa` — an entity asserted to already exist). Every IRI must have appeared in this run's retrieved context. Nothing may be asserted here from memory. If no candidate was retrieved, emit `MU`.
>
> **Minting position** (`bt`, `br`, `ba` with `c "#Name"` — a new entity). Names are expected here. The parent referenced must come from retrieved context, and the minted local name must not collide with an existing entity.

**3b. Retrieval manifest.** Each run records the set of IRIs served to the model — template id, query hash, bindings returned. This is a by-product of the Context Serialiser, not new work.

**3c. Two new Meta-SHACL shapes (M-family).**

- *Reference groundedness.* Any `exactTBoxMatch` / `exactRBoxMatch` / `exactABoxMatch` on a mapping in `mappings:staging` whose object is absent from the run's retrieval manifest → Violation. This is the shape that closes the real-but-wrong-entity hole. Existence is necessary but not sufficient; retrieval-groundedness is the property Principle 3 actually asserts and that Prop 6.10 was gesturing at without making checkable.
- *Minting hygiene.* Any `broadTBoxCategoryMatch` / `broadRBoxCategoryMatch` with a minted `conceptName` must have a retrieved parent, and the minted name must not collide with an existing ontology entity. A collision almost always means the model meant an exact match — route to review rather than silently creating a near-duplicate.

**3d. Optional supporting property.** If the manifest is not available at validation time, `mork:groundedIn` on the mapping (carrying template id plus query hash) lets the shape run locally. Prefer the manifest; this is a fallback.

**3e. Doctrine fragments** for both lint codes, in the diagnostic→doctrine table, ~40 tokens each.

### Acceptance test

A mapping asserting `xr fnd:hasIdentity` where `fnd:hasIdentity` exists in the ontology but was never retrieved is rejected by the groundedness shape. Today it passes Stage 3 cleanly.

---

## R4 — Metric confounding and split provenance

### Context from the paper

Provenance is thorough on the artefact side. `ConstraintProvenance` carries `provenanceCreator`, `provenanceCreated`, `inputHash` (SHA-256 of the NL source), `llmModelId`, `llmConfidence`, `reviewStatus`, `jurisdiction`, `effectiveFrom`/`Until`; `RuleProvenance` parallels it. Principle 5 demands a complete chain from artefact back to the human-authored text. The convergence claims are reported as ρ(t) and the phase table (0% → 20–40% → 50–70% → 80–90% → 90–98%).

None of that records what *instruction* the model received.

### Context from the essay

This is the essay's strongest contribution and it fills a real gap. Hash-pinned immutable packs; each proposal records `mtp-version`, `profile-hash`, `model-id`, `lenses-loaded`; and eval run "on every pack change **and every model version bump** — the latter is how you detect that a frontier upgrade silently changed behaviour."

The model-bump case deserves emphasis because it threatens the paper's premises directly. Proposition 2.33 rests on witnesses not expiring — "an observation that was valid at time t remains valid at time t+1" — and Assumption A6 requires community stabilisation. A silent behavioural change under a model upgrade violates the first and can disturb the second. The essay's eval harness is the only proposed mechanism that would detect it.

### Why they collide

Two provenance records with no join, and convergence statistics that are not stratified by conditioning. A pack improvement that lifts first-pass quality is indistinguishable, in the ρ(t) series, from genuine domain learning. The measurement of each loop is confounded by uncontrolled change in the other.

### Remediation

**4a. One conditioning record.** Add a class rather than bloating every provenance instance:

```
mork:GenerationContext ⊑ skos:Concept
  mork:teachingPackVersion       xsd:string
  mork:teachingPackHash          xsd:string
  mork:deploymentProfileHash     xsd:string
  mork:lensesLoaded              xsd:string (multi-valued)
  mork:retrievalManifestHash     xsd:string
  mork:repairRounds              xsd:integer
```

One individual per run. `ConstraintProvenance` and `RuleProvenance` gain a single object property to it. `llmModelId` stays where it is; the join gives you the full tuple.

**4b. Stratification policy.** ρ(t), the phase table, and the deterministic-percentage figures are comparable only within a fixed `(teachingPackHash, deploymentProfileHash, llmModelId)` triple. Publish stratified series. Any change to any component opens a new stratum and requires re-baselining on the held-out suite. Cross-stratum comparison is reported with an explicit caveat or not reported.

**4c. Two-sided change control.**

| Trigger | Hold fixed | Measure |
|---|---|---|
| Pack release | domain graph, model | essay eval suite: first-pass lint-clean, repair rounds, tokens/triple, semantic F1, unsafe-confidence |
| Model version bump | pack, profile, domain graph | same suite, plus diff against previous model's per-task results |
| Domain milestone (every *N* validated mappings) | pack, profile, model | ρ(t), deterministic fraction, projection concentration gap |
| Community re-detection | pack, profile, model | full re-baseline — this is an A6 stabilisation boundary |

Never vary both sides simultaneously. The fourth row is easy to forget: re-running Leiden is a stratum boundary even though nothing about the pack or model changed.

**4d. Attribution query.** With the join in place, "which teaching configuration produced this cohort of bad mappings?" is a SPARQL query over existing infrastructure. This extends the paper's audit guarantee from mappings to the thing that generated them — which is what Principle 5 implies but does not currently reach.

### Acceptance test

Given a set of mappings rejected with `WRONG_STRUCTURE`, a single SPARQL query returns the distribution of pack version, lenses loaded, and model id. And: a pack release produces a new stratum in the convergence dashboard rather than a discontinuity in an existing series.

---

## R5 — Repair loop mistaken for a semantic gate

### Context from the paper

Remark 4.2 is unusually candid and is the crux: "the validation gate is SHACL-based and checks structural well-formedness and ontological consistency, but does not check full semantic correctness (whether the mapping captures the intended meaning). The uniqueness guarantee is therefore conditional on the quality of the validation layer." It posits a false-approval rate `p_val > 0` and gives uniqueness with probability `(1 − p_val)ⁿ`. The Dialectica reading adds that a false validation "introduces an invalid witness… [which] may be exposed by future challenges."

Stage 5 human review is the only semantic gate in the pipeline.

### Context from the essay

The central cost argument: "the model does not need recall-level mastery. It needs to be **reliably repairable**… Teaching recognition + repair is an order of magnitude cheaper than teaching recall." Metrics: first-pass lint-clean rate, repair rounds to green, tokens per decoded triple, semantic F1 against gold, unsafe-confidence rate.

### Why they collide

The two feedback loops differ in latency by five or six orders of magnitude, and only the slow one carries domain truth. Optimisation pressure flows to the fast metric with total reliability. Three specific failures follow:

- *Lint-clean as a proxy for correct.* A graph can be lint-clean, GCI-consistent and Meta-SHACL-clean while being a confidently wrong mapping. That is the `p_val` case, and it is exactly the case that poisons the projection matrix.
- *Gold-set F1 is not reviewer agreement.* Semantic F1 against a frozen gold suite detects pack regression, which is its job. It cannot detect that the live domain has moved or that reviewers disagree with the gold set.
- *Passing the gate reads as confirmation.* Nothing currently tells the model otherwise, and "validation passed, therefore I was right" is a natural and wholly unwarranted inference.

### Remediation

**5a. Eighth kernel invariant.** One clause, and probably the highest value-per-token item in this plan:

> **Lint-clean is not correct.** The checker verifies form and consistency; only a human verifies meaning. Never raise confidence because validation passed.

**5b. Paired metrics, measured against Stage 5 rather than gold.** Never report lint-clean rate without its semantic partner. Add:

- **Confident-tail approval rate** — Stage 5 approvals among mappings asserted at `weighting ≥ 90`. A direct empirical estimate of `1 − p_val` on the tail that matters.
- **Silent-error rate** — mappings that passed all of Stage 3 and were then rejected with reason `WRONG_TARGET`. This is the `p_val` estimator proper, and the only number that says whether the fast loop is buying anything semantically. Note that it is only computable once R1's rejection taxonomy exists; R1 is a prerequisite here.

**5c. Calibration gate — this is what protects the convergence theorem.** Plot asserted `weighting` against Stage 5 approval rate. If the curve is flat or non-monotone, `weighting` carries no information and the projection matrix is being fed noise: Proposition 2.12's monotonicity premise fails *empirically* even while holding formally. Make this a gate on the domain loop — while calibration is broken, block bulk promotion from `mappings:staging` to `:active` and require per-mapping review. This converts Remark 4.2's acknowledged weakness from a caveat in prose into an operational control.

**5d. Retrospective challenge sweep.** Remark 4.2 says false validations "may be exposed by future challenges" — new co-occurrence observations, or disjointness axioms not triggered at original validation time. Nothing currently makes that happen. Add a scheduled job: whenever disjointness or cardinality axioms are added to the target ontology, or a section observation reveals co-occurrence inconsistency, re-run Stage 3 over `:active` mappings and reopen anything that now fails, reversing its projection contribution. This is the only mechanism that recovers from a `p_val` event, and it is a direct implementation of the Dialectica argument at Proposition 2.33 — witnesses accumulate, so discriminative power only grows, so retrospective detection is always possible if you actually look.

**5e. Repair rounds are not a quality signal.** Cap them per Principle 4's hard iteration limit and treat exhaustion as a route to human review. Do not optimise the count, and do not read a low count as evidence of correctness.

### Acceptance test

The dashboard cannot display first-pass lint-clean rate without silent-error rate alongside. A deliberately mis-targeted but structurally perfect mapping is counted in silent-error rate, and its projection contribution is reversed on detection.

---

## Sequencing

Ordered by *blocks-a-silent-corruption first*, then by cost.

| Step | Work | Effort | Unblocks |
|---|---|---|---|
| 1 | Kernel text: confidence separation (1a), three emission positions (3a), lint≠correct (5a) | hours | stops the worst contamination immediately |
| 2 | Rejection taxonomy + shape + projection-update contract (1c, 1d) | days | any trustworthy convergence measurement, and 5b |
| 3 | `GenerationContext` + join + stratification policy (4a–4c) | days | all measurement of either loop |
| 4 | Retrieval manifest + groundedness shapes (3b, 3c) | days | R3's hard case |
| 5 | Segment order, budget precedence, section windows (2a–2e) | 1–2 weeks | cost argument; retrieval headroom |
| 6 | `notationConfidence` + `nc` code (1b) | days | errata aggregation by failure type |
| 7 | Calibration gate + silent-error metric + retrospective sweep (5c, 5d) | 2–3 weeks | recovery from `p_val` events |

Steps 1–3 are the plan's spine: step 1 is nearly free and removes the most dangerous inferential habits; step 2 is the actual separation of the two learning systems; step 3 makes either system measurable. Nothing downstream is interpretable without them.

---

## Vocabulary delta

| Addition | Kind | Justifies |
|---|---|---|
| `mork:notationConfidence` | annotation property | separates notation from domain doubt without touching propagation |
| rejection-reason enumeration on `userDeclined` | enumerated annotation value | prevents projection poisoning from notation rejections |
| `mork:GenerationContext` + 6 properties | class + data properties | joins the two provenance records; enables stratification |
| `mork:groundedIn` | data property (optional fallback) | local checkability of retrieval groundedness |
| Reference-groundedness shape | Meta-SHACL (M-family) | closes the real-but-wrong-entity hole |
| Minting-hygiene shape | Meta-SHACL (M-family) | prevents near-duplicate class creation |
| Rejection-reason shape | Meta-SHACL (cross-layer) | enforces the taxonomy |
| `nc` | MCN code | notation doubt, positionally distinct from `w` |
| 3 kernel clauses | L0 text | position typing, channel separation, lint≠correct |

No changes to the calculus, the precedence derivation, the box-match hierarchy, or the lens/cassette structure.

---

## What I would not do

**Do not merge the two confidence channels into a single richer scalar.** The temptation is a vector or a structured confidence object. It would re-open exactly the conflation R1 exists to close, and it would break Proposition 5.4's `min()` propagation, which requires a totally ordered scalar.

**Do not make lens routing semantic.** The essay is right that routing should be a static table on cheap signals. Using MORK competence to select MORK teaching is circular at cold start, when the pack matters most. The one legitimate addition is the ambiguity type already emitted by the thresholding step (gap > δ / > ε / else human), which is deterministic and free.

**Do not fold the errata card into the projection matrix.** They are structurally analogous — both accumulate validated outcomes and change future behaviour without touching weights — and that analogy makes merging them attractive. Resist it. They must feed from disjoint signals, per 1d, and they have different review authorities: errata is a pedagogy artefact reviewed by whoever owns the pack; projections are domain facts reviewed by domain stewards.

**Do not raise `weighting` on validation success.** Worth stating as an explicit prohibition somewhere enforceable, not only as kernel guidance, because it is the mechanical form of the inference 5a forbids and it would inflate the confident tail that 5b and 5c exist to monitor.

