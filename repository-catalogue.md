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
