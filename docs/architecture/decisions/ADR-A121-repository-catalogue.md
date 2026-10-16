<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A121: The repository catalogue

**Status:** Accepted, 2026-10-17
**Date:** 2026-10-16
**Supersedes:** none
**Related:** [ADR-A01](ADR-A01-layer-dependency-order.md) (layer order),
[ADR-A29](ADR-A29-repository-toolchain-and-environment-boundary.md) (`mise`),
[ADR-A77](ADR-A77-repository-topology-and-documentation-governance.md) (topology),
[ADR-A88](ADR-A88-ontology-import-resolution-for-consumers.md) (the XML catalog),
[ADR-A117](ADR-A117-agent-guidance-and-skill-library.md) (agent guidance),
[ADR-A126](ADR-A126-literate-specification-layout-and-grammar.md) (README layout),
[ADR-A127](ADR-A127-published-architecture-decisions.md) (published decisions and the site)

## Context

Code, tests, `mise` tasks, documents and agent skills each carry their own copy of where things live in
the repository. Each copy is written by hand, and nothing checks that the copies agree or that the paths
still exist. Measured on 2026-10-09, there were 144 Python path constructions naming `ontology` in 50
files, 45 `mise.toml` lines naming an `ontology/` or `tools/` path, and 474 Markdown references of the form
`ontology/<module>/<spec|shapes|vocab|examples>` in 126 files.

Some of this is a contract that lives nowhere authoritative.

- **Extraction contracts.** `literate_extract.py` writes `turtle-shapes` blocks to shape files named on
  its command line, so Instrument's list of three shape files is repeated in four tests.
- **Versioned directories, proof roots and the layer order** are constants in `ontology_version_check.py`,
  `check_formal_freshness.py` and `import_guard.py`.
- **Module layouts differ.** Party has no `examples/`, Vocabulary no `vocab/`, Persistence two spec
  documents and two shape documents, and the applied modules sit two levels below `ontology/applied/`.

Projects built on LATTICE need to find LATTICE's specifications and shapes from outside this repository,
and each would otherwise copy LATTICE's layout into its own code. Both LATTICE and those projects develop in
parallel in several git worktrees, each with its own `.venv`.

The name needs care. ADR-A88's OASIS XML catalog (`ontology/catalog-v001.xml`) maps ontology IRIs to files.
This catalogue answers a different question, where the artefact with a given role lives.

## Decision

1. **One catalogue in two kinds of file.** A root file, `repository-catalogue.md`, holds the repository's
   roots, the conventional layout of an ontology module and of a tool package, the layer import order,
   tool packages, documentation areas, generated outputs and the site's sections. Each module's own entry
   sits in section 3 of its README (ADR-A126), beside the specification it describes. A module that is not
   literate has an entry too. Prose explains, and fenced blocks tagged `` ```toml repository-catalogue ``
   carry the data. Blocks merge in a fixed order, the root file first and then the modules in the order the
   root file lists them. A key defined twice, or a key the schema does not know, is an error.
2. **What an entry describes.** A module entry states its path, its kind, the artefact roles it has, any
   departure from the conventional layout, its extraction contract (its spec documents, vocab document and
   shape files in extraction order), which of its roles are versioned, and which modules it may import. The
   import rules are flexible enough for any mix of imports an applied ontology needs. The substrate's order
   is still decided by ADR-A01. The catalogue is where tools read it, and a change to the substrate's order
   there needs an amendment to ADR-A01.
3. **Roles and directories, not inventories.** The catalogue names a module's spec, its shapes in order and
   its examples directory. It does not list each example or fixture. A test that needs one names the file
   inside the directory the catalogue gives it. Where a module departs from the convention, the entry names
   the extra role, for example a second spec document.
4. **One reader.** `tools/lattice_repo_catalogue.py`, using the standard library only (`tomllib`), is the
   only code that finds the repository root and reads the catalogue. It resolves a role to a path, or to an
   ordered tuple of paths, and fails with an error that names the missing key and where to declare it. It
   also offers a command line (`path`, `paths`, `check`, `dump --json`) for `mise` tasks, continuous
   integration and other runtimes. It finds the root, first match winning, from an explicit argument, the
   `LATTICE_ROOT` environment variable, or the nearest directory at or above the working directory holding
   `repository-catalogue.md`. It never counts parents of `__file__` and never asks git. Each checkout runs it
   with its own interpreter against its own tree, so parallel worktrees, each with its own `.venv`, read
   their own catalogues.
5. **A check.** `mise run check:catalogue`, part of `mise run check`, fails when a block does not parse or
   breaks the schema, when a declared path does not exist (unless it is marked generated), when a directory
   under `ontology/` that holds a module is not declared, when a tool package is not declared, and when code
   outside the reader builds a path to a catalogued root. That last scan starts in report-only mode with a
   list of known exceptions, each with a reason. The check fails on a listed exception that no longer
   occurs, so the list only shrinks, and the scan fails rather than reports once the tools have moved to the
   reader.
6. **Generated from it.** The "Where things are" table in `AGENTS.md` is generated from the root file's
   roots by `mise run build:agent-guidance`.
7. **Downstream projects can extend it.** A downstream project's catalogue declares that it extends
   LATTICE's, and entries are then qualified by catalogue, for example `lattice:instrument`. The schema
   rejects unknown top-level keys from the start, so the extension key can be added without ambiguity.
8. **The reader becomes a package when a downstream project needs it.** It is promoted to a package,
   `lattice-repo-catalogue` (module `lattice_repo_catalogue`), installable into any worktree's own `.venv`
   and pinned to a version, so different branches of a downstream project can use different versions at
   once.
9. **The name.** Documents say "repository catalogue" in full, and "XML catalog" for ADR-A88's.

## Consequences

- `literate_extract.py` reads its extraction contract from the module's entry, so its `--shapes` argument
  and the copies of shape lists in tests go away. The per-layer `--check` tests keep testing the same
  property.
- `import_guard.py`, `ontology_version_check.py` and `check_formal_freshness.py` read their constants from
  the reader.
- A module is added, moved or removed by editing its README's section 3 and, for a new module, the root
  file's list. The design, ontology authoring, toolchain, architecture and lifecycle skills say so when the
  catalogue lands.
- Other runtimes read `dump --json` until one needs a native reader. That is a deferral, not a decision
  against one.
- The XML catalog is unchanged by this decision. Release and version management may later be read from the
  repository catalogue, and the XML catalog folded into it, by a decision that supersedes the relevant parts
  of ADR-A88.
- Root discovery assumes callers run from the repository root or below it, as `mise`, pytest and continuous
  integration do. A tool started elsewhere sets `LATTICE_ROOT`, and the reader's error says so.

## Provenance

Proposed in the [repository catalogue sketch](../../developer/sketches/repository-catalogue.md), whose
questions RC-Q1 to RC-Q8 were answered on 2026-10-16, and planned in the
[`improved-ontology-documentation` plan](../../developer/plans/improved-ontology-documentation.md)
(slices RC1 to RC6, decisions OD-D14, OD-D16 and the RC rows).
