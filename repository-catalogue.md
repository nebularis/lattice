<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Repository catalogue

Where things live in this repository, stated once and read by tools through one module,
`tools/lattice_repo_catalogue.py` ([ADR-A121](docs/architecture/decisions/ADR-A121-repository-catalogue.md)).
People read the prose, and tools read the fenced `toml repository-catalogue` blocks. This file holds the
conventions and the ordered list of modules. Each module's own entry is in its README, in its Extraction
Contract section once the README takes the layout of
[ADR-A126](docs/architecture/decisions/ADR-A126-literate-specification-layout-and-grammar.md).

This is not the XML catalog of [ADR-A88](docs/architecture/decisions/ADR-A88-ontology-import-resolution-for-consumers.md),
`ontology/catalog-v001.xml`, which maps ontology IRIs to files. This catalogue says where the artefact with
a given role lives.

`mise run check:catalogue` fails when the catalogue and the tree disagree. A tool asks the reader for a
location, for example `python tools/lattice_repo_catalogue.py paths instrument shapes` for the files
Instrument's README generates its shapes into, in order.

## Conventions

A **role** is a subdirectory of a module, named for the kind of artefact it holds. A module's entry lists
its roles, and the check confirms they are exactly its subdirectories.

| Role | Holds |
|---|---|
| `spec` | ontology documents, each with its own `owl:versionIRI` |
| `vocab` | vocabulary documents (individuals and schemes), each with its own `owl:versionIRI` |
| `shapes` | SHACL shapes, versioned together by the directory's `.version` |
| `projection` | composition a higher layer declares over a lower one, versioned by the directory's `.version` |
| `examples` | example graphs, written by hand |
| `test` | test fixtures |
| `docs` | design documents of the module |
| `execution` | execution manifests and policies |
| `mtp`, `targets` | MORK's teaching pack and mapping targets |
| `cases` | worked cases of an applied validation package |

Which documents are versioned, and how, is the [versioning policy](docs/architecture/ontology-versioning-policy.md)'s.

A **kind** says where a module stands in the architecture.

| Kind | Modules |
|---|---|
| `substrate` | the layers of ADR-A01's order. Each entry lists the layers it may import |
| `standalone` | modules outside that order: MORK, SPC, Surface and Persistence |
| `applied` | domain modules under `ontology/applied/` |
| `example` | applied validation packages under `ontology/examples/` |
| `scaffold` | a module with no artefacts yet |

```toml repository-catalogue
[conventions]
roles = ["spec", "vocab", "shapes", "projection", "examples", "test", "docs", "execution", "mtp", "targets", "cases"]
versioned = ["spec", "vocab"]
artefact-directories = ["shapes", "projection"]

[conventions.kinds]
substrate = "a layer of ADR-A01's order, whose entry lists the layers it may import"
standalone = "a module outside ADR-A01's order"
applied = "a domain module under ontology/applied/"
example = "an applied validation package under ontology/examples/"
scaffold = "a module with no artefacts yet"
```

**The release.** The substrate and standalone modules are released together, as one set with one number
(OD-D55). Every one of their documents carries that number in its version IRI, and every import of one names it.
Their shape and projection directories have no `.version` file. The applied modules and the examples are not in
the release, keep their own versions, and pin a release. `mise run release:prepare -- <version>` moves the set to a
new number, and the versioning check holds every member to it.

```toml repository-catalogue
[conventions.release]
version = "0.18.0"
kinds = ["substrate", "standalone"]
```

## Modules

A module's name is its path under `ontology/`. The substrate is listed in ADR-A01's order, then the
standalone modules, the applied modules, the examples and the scaffolds.

```toml repository-catalogue
[catalogue]
schema = 1
modules = [
    "foundation", "vocabulary", "quantification", "party", "eligibility", "wording", "behaviour", "instrument",
    "surface", "spc", "mork", "persistence",
    "applied/capacity", "applied/classification",
    "applied/insurance/common", "applied/insurance/peril", "applied/insurance/exposure",
    "examples/insure-o",
    "governance",
]
```

## A module's entry

Each module's README holds one block with a `[module]` table, for example Instrument's below.

```toml
[module]
kind = "substrate"
roles = ["examples", "shapes", "spec", "vocab"]
imports = ["foundation", "vocabulary", "quantification", "party", "eligibility", "wording", "behaviour"]

[module.extract]
spec = ["spec/instrument.ttl", "spec/instrument-acts.ttl"]
vocab = ["vocab/instrument-vocab.ttl"]
shapes = ["shapes/structural.ttl", "shapes/constraints.ttl", "shapes/single-expression.ttl"]
```

- `kind` is one of the kinds above, and `roles` the module's subdirectories.
- `imports` is given for a substrate layer only, and names every module it may import. A module outside
  the order has none, and its imports are not judged. A change to the substrate's order here needs an
  amendment to ADR-A01.
- `extract` is given for a literate module only. It names the files its README generates, each in its
  role's directory, and lists the shape files in the order of the README's shape blocks. The README's
  other shape files are written by hand.
- Paths are relative to the module's directory.

## Roots

Each top-level root, what it owns and the decisions behind it. A root is a directory at the repository root
that holds one kind of thing. A new root, or a new kind of directory anywhere, needs an accepted ADR.

`owns` is one plain statement for the catalogue. `row` is the text of the root's row in the "Where things are"
table of [AGENTS.md](AGENTS.md), which `mise run build:agent-guidance` generates from these entries. Roots
that share a `group` are one row, written once on the first of them. The documentation areas below follow
the roots in that table.

```toml repository-catalogue
[[roots]]
path = "ontology/"
owns = "semantic assets and their documentation"
adrs = ["ADR-A01", "ADR-A77", "ADR-A121", "ADR-A126"]
row = "semantic assets only: sources, shapes, vocabularies, projections, examples, their documentation"

[[roots]]
path = "tools/"
owns = "executable reference implementations and developer toolchains"
adrs = ["ADR-A29", "ADR-A121", "ADR-A125"]
row = "executable reference implementations and developer toolchains. `tools/testing/` holds test-support packages, used only by tests, checks and benchmarks (ADR-A125)"

[[roots]]
path = "benchmark/"
owns = "checks that measure"
adrs = ["ADR-A124"]
row = "checks that measure, run on demand and never part of `check`. They fail on a wrong result, never on time (ADR-A124)"

[[roots]]
path = "platform/"
owns = "Java services"
adrs = ["ADR-A77"]
group = "services"
row = "services, applications, libraries, data contracts, the local environment, the worker runtime, end-to-end suites, experiments"

[[roots]]
path = "apps/"
owns = "applications"
adrs = ["ADR-A77"]
group = "services"

[[roots]]
path = "packages/"
owns = "libraries"
adrs = ["ADR-A77"]
group = "services"

[[roots]]
path = "contracts/"
owns = "data contracts"
adrs = ["ADR-A77"]
group = "services"

[[roots]]
path = "deployment/"
owns = "the local environment"
adrs = ["ADR-A77"]
group = "services"

[[roots]]
path = "workers/"
owns = "the worker runtime"
adrs = ["ADR-A77"]
group = "services"

[[roots]]
path = "test/"
owns = "end-to-end suites"
adrs = ["ADR-A77"]
group = "services"

[[roots]]
path = "spikes/"
owns = "experiments"
group = "services"
```

## Tool packages

A tool package is a directory under `tools/` with a `pyproject.toml`. The check fails when one on disk is
not declared here. `import-names` are the packages it installs, and `reaches` the paths outside its own tree
that its Python code or tests read or write at run time, named to the second segment, for example
`ontology/eligibility`. A path a docstring or comment only mentions is not reached, nor is a package it
imports. A test derives each package's reaches from its code and compares them. A path under `generated` may
be absent.

```toml repository-catalogue
[[tools]]
name = "mork"
path = "tools/mork"
import-names = ["mork_communities", "mtp", "mcn"]
reaches = ["ontology/mork"]

[[tools]]
name = "mork_compilers"
path = "tools/mork_compilers"
import-names = ["mork_compilers"]
reaches = ["ontology/eligibility", "ontology/mork", "ontology/quantification", "platform/reasoning-testkit"]

[[tools]]
name = "persistence"
path = "tools/persistence"
import-names = ["persistence"]
reaches = ["ontology/persistence", "contracts/identity"]

[[tools]]
name = "reference/eligibility"
path = "tools/reference/eligibility"
import-names = ["reference_eligibility"]

[[tools]]
name = "spc/python"
path = "tools/spc/python"
import-names = ["spc"]

[[tools]]
name = "surface"
path = "tools/surface"
import-names = ["surface"]
reaches = ["ontology/surface", "test/conformance"]

[[tools]]
name = "testing/oxigraph"
path = "tools/testing/oxigraph"
import-names = ["lattice_testing_oxigraph"]

[[tools]]
name = "vocabulary"
path = "tools/vocabulary"
import-names = ["vocabulary"]
reaches = ["ontology/vocabulary"]
```

## Documentation areas

Documentation lives under `docs/`, and agent guidance under `.claude/skills/`. An entry has the same keys as
a root, and its row follows the roots' rows in the "Where things are" table.

```toml repository-catalogue
[[docs]]
path = "docs/architecture/"
owns = "architecture documents and the ADRs"
adrs = ["ADR-A77", "ADR-A127"]
row = "architecture documents and the ADRs, in `decisions/`"

[[docs]]
path = "docs/developer/"
owns = "working documents and durable developer guidance"
adrs = ["ADR-A77", "ADR-A127"]
row = "sketches, plans, status records, review requests, Validation Packs, and durable guidance"

[[docs]]
path = ".claude/skills/"
owns = "agent skills"
adrs = ["ADR-A117"]
row = "the skills below"
```

## Generated outputs

Paths a check may find missing, because a build writes them and a clean checkout does not have them.
Files a module's README generates are not listed here. They stay under that module's `extract`.

```toml repository-catalogue
[generated]
paths = [
    ".build/",
    "docs/_site/",
    "platform/reasoning-testkit/target/reasoning-testkit.jar",
]
```
