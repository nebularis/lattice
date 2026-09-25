<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Tools

Python 3.14+. The executable Python tools are sibling projects under `tools/`.
`tools/mork/`, `tools/mork_compilers/`, and `tools/surface/` each own a
`pyproject.toml` and a conventional `src/<package>/` layout. Run everything
from the repository root.

## Python environment

The repository-level development environment is declared in `pyproject.toml`.
For a reproducible core validation environment, create a virtual environment
and install the pinned constraints with:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -c requirements-lock.txt ".[reasoning]"
```

The lock covers RDF parsing, SHACL validation, and OWL/RDFS reasoning. The
optional MORK community dependencies remain separate from the core validation
environment and can be installed with `.[community]` when needed.

## `tools/literate_extract.py`

Regenerates a layer's compiled Turtle from its README, which is the
authoritative specification. Fenced blocks are extracted in document order:
`turtle-spec` → `spec/<layer>.ttl`, `turtle-vocab` → `vocab/<layer>-vocab.ttl`,
`turtle-shapes` → the shape files named on the command line, in order.
`turtle-example` blocks are never extracted. Each output gains the SPDX header
as its first line.

```bash
python3 tools/lattice/literate_extract.py ontology/surface/README.md \
    --layer surface --root . \
    --shapes shapes/structural.ttl shapes/constraints.ttl
```

`--check` writes nothing and exits non-zero if any target differs from what
would be written. Run it in CI: it is the README⇄spec drift check the
governance discipline requires and that nothing currently enforces.

## `tools/surface/` — the surface compiler

Compiles surface contracts into generated module packages. Structure follows
`tools/mork2rml.py`: a `SurfaceGraphAnalyser` that transcribes declarations, a
`SurfaceCompiler` that folds a contract and its read set into a symbol
inventory, and a thin CLI over both.

| Module | Holds |
|---|---|
| `namespaces` | shared namespace bindings |
| `model` | specification dataclasses and `SurfaceGraphAnalyser` |
| `naming` | identifier minting and injectivity checking |
| `canonical` | canonicalisation and content hashing |
| `serialise` | deterministic Turtle output, and file loading |
| `compile` | `SurfaceCompiler` — contract plus read set to symbols |
| `parity` | the ontology/surface/source comparison discharging law `srf:R2` |
| `mork` | lifting to and lowering from `mrk:ProjectionMapping` |

### Compile

```bash
python3 -m surface compile \
    --contracts ontology/surface/examples/employment-job-family.ttl \
    --out ontology/surface/execution \
    --verify-determinism --parity
```

Writes `core.ttl`, `closure.ttl`, `assertions.ttl` and `manifest.ttl` under
`<out>/<contractKey>/`, omitting any module with no content. `--sources` adds
scheme or instance graphs held in separate files; `--contract` restricts the
run to one contract IRI; `--input-surface` supplies generated surfaces read as
input, which is what makes a surface stacked; `--now` fixes the production
timestamp, which is the only non-reproducible value emitted;
`--mork-mapping` additionally writes the `mrk:ProjectionMapping` record.

`--verify-determinism` compiles twice, compares artefact hashes, fails the run
on mismatch, and records a discharge of law `srf:R1` on success. The production
timestamp sits outside the artefact hash precisely so that this comparison
means something.

`--parity` runs the `srf:R2` check before anything is written and records the
discharge on success, so a surface that disagrees with its source never reaches
the output directory.

### Check freshness

```bash
python3 -m surface check \
    --manifest ontology/surface/execution/job-family/manifest.ttl \
    --contracts ontology/surface/examples/employment-job-family.ttl
```

Recomputes the recorded read set against the current sources and names each
entry that has moved. A surface is stale exactly when any entry's hash differs
from the recorded one; no change needs to be classified for that to be decided.
Exits non-zero when stale, so it drops into CI unchanged.

### Parity

```bash
python3 -m surface parity \
    --contracts ontology/surface/examples/employment-job-family.ttl
```

Asks the surface and the source the same question — membership per population
member, closure per member, promoted value per instance — and reports every
disagreement. Where the two differ the surface is wrong by construction: the
source is authoritative and the surface is a restatement of it.

Definition-only forms are reported as **skipped**, with the profile's declared
entailment regime named, rather than silently passed: their memberships are
entailments and rdflib is not a reasoner. Closing that gap needs a reasoner in
the loop, not more code here.

### MORK interoperation

```bash
# lift compiled surfaces into mrk:ProjectionMapping records
python3 -m surface mork \
    --contracts ontology/surface/examples/employment-job-family.ttl \
    --mapping-scheme https://example.org/mappings/employment
```

`lift` writes the mapping record accounting for a compiled surface, so a
generated class traces back through a mapping to an intent to the source text.
`lower` goes the other way, turning a proposed `mrk:ProjectionMapping` into a
`srf:` contract declaration — the path a MORK-proposed projection takes to
become a governed contract. MORK never generates symbols; generation sits
downstream of its validation gate and is fully deterministic.

Under `srf:WrappedSymbols` the lifted record wraps each generated class in an
`mrk:OwlClass` individual linked by `owl:sameAs`, matching MORK's existing
convention for toolchains that reject punning. Under `srf:PunnedSymbols` the
class IRI is referenced directly.

### Tests

```bash
python3 -m unittest surface.test_surface -v
```

Covers canonicalisation, naming, population enumeration, path evaluation,
closure, compilation, parity, MORK round-tripping, and the six deliberate-defect
fixtures in `ontology/surface/test/`. **Not yet executed** — the environment this
revision was written in has neither rdflib nor network access, so treat the
first run as part of review.

### What the compiler refuses

Refusals are deliberate and each names its law. Two population members minting
one identifier (`srf:S6`); a cyclic closure basis (`srf:R5`); a population over
its budget (`srf:S4`); a lossy promotion onto a property outside the contract's
target namespace, or a definition-only promotion onto an authored property
(`srf:X6`); both read-path forms declared at once, or neither (`srf:S1`); a
closure form without a basis, or a basis without a closure form (`srf:S3`); a
nominal-class definition over a read path containing an inverse step, which
would leave OWL 2 EL; a closure relation over a multi-hop path, which should
promote first and index the promoted property; a stack depth above the
profile's permitted depth (`srf:S10`).

## `tools/vocabulary/` — the scoped/temporal binding resolver

Reference resolver for the Vocabulary layer's scoped and temporal
`voc:SchemeBinding` resolution law (`ontology/vocabulary`, [ADR-A85](../docs/architecture/decisions/ADR-A85-vocabulary-scoped-temporal-binding-resolution.md)).
`vocabulary.resolver.resolve(graph, contract, context, at)` returns the one
`voc:ConceptScheme` that applies given a caller-supplied active context and
resolution time, or raises a named exception (`BindingConflictError`,
`NoApplicableBindingError`) rather than choosing silently. See
[`tools/vocabulary/README.md`](vocabulary/README.md) for the full precedence
law and what this package deliberately leaves to SHACL instead.

```bash
mise exec -- python -m pip install -e ./tools/vocabulary[test]
python -m pytest tools/vocabulary/tests -q
```

**Not yet executed** — this sandbox has no network access to install
`rdflib`/`pyshacl`/`pytest` (see `docs/developer/status/vocabulary-temporal-binding.md`);
treat the first run as part of review, same as `tools/surface`'s own test
suite above.


## `tools/test_eligibility_examples.py` — Eligibility example checks

Validates each example under `ontology/eligibility/examples/` against the
layer's shape files, with the layer's spec as ontology graph so class targets
reach subclass instances, and expects no result at all. Probe cases remove a
declared concept and check that `elg:ConceptConditionDeclarationShape` warns
where [ADR-A87](../docs/architecture/decisions/ADR-A87-eligibility-concept-inclusion-and-exclusion.md)
says it should, and nowhere else.

```bash
mise run check:eligibility-examples
```

## `tools/ontology_catalog.py` — import resolution

Generates `ontology/catalog-v001.xml` and the stub catalogs in every `spec/`
and `vocab/` directory, checks that every `owl:imports` target under
`ontology/` resolves, and loads an import closure into `rdflib` through a
catalog chain ([ADR-A88](../docs/architecture/decisions/ADR-A88-ontology-import-resolution-for-consumers.md)).
Pre-existing defects are listed in `KNOWN_DEFECTS` and reported without
failing. The check fails once a listed defect is fixed, so the entry is
removed in the same change.

```bash
mise run build:ontology-catalog
mise run check:ontology-catalog
python tools/ontology_catalog.py closure https://www.nebularis.org/neuro-semantic/behaviour
```

## `tools/ontology_version_check.py` — version hygiene

Fails when an ontology document's content changed without its version IRI,
or when a document under `spec/` or `vocab/` has no version IRI
([ADR-A86](../docs/architecture/decisions/ADR-A86-ontology-semantic-versioning.md)).

```bash
mise run check:ontology-versioning
```
