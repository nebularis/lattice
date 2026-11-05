<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A152: The knowledge index and the work board run on Вивід, installed and pinned, with LATTICE keeping a thin layer of its own

**Status:** Proposed, 2026-11-05
**Date:** 2026-11-05
**Supersedes:** none
**Related:** [ADR-A134](ADR-A134-knowledge-index-and-design-shape-vocabulary.md) (the knowledge index), [ADR-A151](ADR-A151-the-work-board.md) (the work board), [ADR-A133](ADR-A133-git-hooks.md) (the hooks and their moments), [ADR-A117](ADR-A117-agent-guidance-and-skill-library.md) (AGENTS.md and the skills), [ADR-A29](ADR-A29-repository-toolchain-and-environment-boundary.md) (`mise` as the one entry point)
**Unit:** [`vyvid-migration`](../../developer/plans/vyvid-migration.md)

## Context

The knowledge index of ADR-A134 and the work board of ADR-A151 were built in LATTICE as about 8,200 lines of Python under `tools/`, of which about 280 derive something only LATTICE has, its architectural quanta and the catalogue's owners. The rest, registers whose header is their schema, facets as SKOS schemes, a derived index ranked by meaning, identifiers resolved on a normalised key, and the board read across every branch, serves any project that keeps its rules in Markdown. [Вивід](https://github.com/nebularis/vyvid), `vyd` at the command line, is that core extracted into a framework of its own, with scopes layered from general to project, domains carrying registers and skills, and a project file binding a repository. Its bake-off ranks LATTICE's 48 questions identically to LATTICE's own tooling, hit@5 0.884 and MRR 0.806 on the 43 scored. The triple-store record of ADR-A128 and the thirty query-writing standards serve any project that runs SPARQL, and Вивід's `vyvid-triple-stores` domain already holds them, citing no project. Keeping LATTICE's copy of the core means maintaining it twice.

## Decision

1. **The knowledge index and the work board are Вивід's.** LATTICE declares itself as a project of Вивід in `vyvid.toml` at the repository root, its families, extractors, moves, recipes and work settings, and keeps its additions to the domains' skills and the skills wholly its own under `.vyvid/`. These two are the root entries this decision admits. A maintainer's user configuration may add an entry for the paths only one machine knows.
2. **Вивід is installed by `mise run bootstrap` as a `uv` tool at the version `mise.toml` pins**, moved deliberately like any other pinned tool, and never installed over a copy that already reports that version.
3. **`mise` stays the one entry point** (ADR-A29). Every `vyd` command an agent is told to run is a `mise` task under the name it has today, `graph:ask`, `build:knowledge`, `check:identifiers`, `work:board`, `build:work`, `build:roadmap`, `work:here` and the rest, so no skill text and no habit changes, and `mise run vyd -- <args>` passes anything else through.
4. **A hook or task whose tool is absent or fails skips with a message naming what it skipped and how to install it, and never blocks a commit.** Windows is proven after the switch, so this is what protects a contributor there in the meantime. A check that says it did not run is a skip, never a failure.
5. **The skills are composed from the domains plus LATTICE's additions by `vyd install --project` and committed**, each opening on the index-first header Вивід writes, so a clone without `vyd` has them. `vyd check skills` holds the committed copies to their sources, and a skill of today is removed only once that check, given the old file and its coverage map, proves every line of it has a home.
6. **LATTICE's knowledge tests pass against the store `vyd build` writes before any test or module is deleted.** `check:knowledge` proves the whole knowledge base consistent, and only the tests that duplicate Вивід's own suite go.
7. **The triple-store record and the query-writing standards move to the `vyvid-triple-stores` domain by declared moves, pinned to the LATTICE commit they were read at.** From the declaration, a moved family resolves to the domain while LATTICE's copy is still present and the copy is no longer indexed, so `vyd move check` is what catches drift between them. The copies are removed last, after every branch has been compared, and a page at the record's old path says what each finding means for LATTICE, keyed to the domain's identifiers and pinned to a tag of the domain, since published documents link that path.
8. **ADR-A134 and ADR-A151 stand**, their vocabulary, families, board shape, grammar, hook checks and generated regions unchanged in meaning, and each takes a dated addendum pointing here for the tool that now implements it.

## Consequences

LATTICE maintains about 500 lines for its index and board, the extractor for quanta and owners and the tests that stay, instead of about 8,200. A rule about asking the index lives once, in the general scope `vyd context` prints, and AGENTS.md keeps only what is LATTICE's. A rule about `mise`, probing a store or writing a query lives in a domain skill plus LATTICE's additions, composed and committed. A contributor without `vyd` has the build, the hooks and the committed skills, and no index or board, and every check tells them so. `bootstrap` reaches the network for one more tool. A `vyvid.toml` edit lapses the maintainer's trust of it, after which no extractor runs until `vyd trust` is run again in a terminal, so edits to it are batched. The move of the record is the one irreversible edge, a public URL, met by the page at the old path.

## Provenance

The sketch [vyvid-migration](../../developer/sketches/vyvid-migration.md) holds the facts, the table of what moves and what stays, and the answered questions VM-Q1 to VM-Q6. The plan [vyvid-migration](../../developer/plans/vyvid-migration.md) holds the decisions and the slices VM-1 to VM-6. Вивід's own plan names the switch as its slice VYD-2b.
