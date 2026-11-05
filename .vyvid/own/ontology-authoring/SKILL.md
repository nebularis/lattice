---
name: lattice-ontology-authoring
description: How to change a LATTICE ontology and model well in it. Use when editing anything under ontology/ (a layer README, spec, vocab, shapes, projection or examples), moving the release number or an applied module's version IRI, writing a SHACL or SHACL-SPARQL shape, declaring a domain or range, simplifying a model, or naming a new technical term, in LATTICE or an applied ontology built on it.
---

# Authoring LATTICE ontologies

This skill's tasks span the activities ontology-design, conceptual-data-modelling, logical-data-modelling, schema-design, identity-design, temporal-modelling, scenario-and-test-data and release-and-versioning, and a task often needs several of them, named together and separated by commas. `--activity`, `--quality` and `--tech` raise matching entries and hide none, while `--kind` filters exactly, so leave `--kind` off unless only one kind of entry will do. The index finds the rules this skill does not mention, and the entries related to the ones it does.


The modelling rules are in the skill `lattice-ontology-modelling`, which also holds the LATTICE rules for the layers, and the rules for SHACL-SPARQL shapes are in the skill `lattice-query-writing`.

## Changing an ontology document

Follow every step for any change to `ontology/**/spec/`, `ontology/**/vocab/`, or a `shapes/` or
`projection/` directory. Read the
[versioning policy](https://github.com/nebularis/lattice/blob/main/docs/architecture/ontology-versioning-policy.md)
(ADR-A129, ADR-A86, ADR-A113) first. A skipped step breaks consumers silently, and has done so before.

**Version bumps and `release:prepare` are a merge-time operation, never a branch-time one.** Steps 2
to 6 below move every release member's `owl:versionIRI` to a new shared number (ADR-A129), which
touches every substrate document whether or not its own content changed, and cascades
into every applied module that pins the release. Nobody consumes a long-lived development branch's
version numbers before it merges, so bumping mid-branch re-pins dozens of files for no reader, and
the real bump still has to happen again, once, when the branch actually merges. A branch pins its
imports to `main`'s versions at the branch point and never re-pins them itself, precisely as the
Applied Insurance Reference lanes document states for machine S's branch
(`docs/developer/plans/applied-insurance-reference-lanes.md` §1, §3: "Imports of LATTICE layers stay
pinned to the versions of `main` at the branch point, and S never re-pins them... R re-pins the
branch to `main`'s layer versions once, at the merge"). A new document a branch adds, such as a new
layer's first README, cites the *current* release number throughout (matching whatever `main` is
pinned to when the branch started), not a bumped one, and stays that way until the person merging
runs the bump, once, for the whole branch's accumulated changes. Follow steps 2 to 6 only when
the maintainer is actually preparing a merge into `main`, never as part of an ordinary slice.

1. **Find the source of truth.** A literate layer's `README.md` is its source. Its fenced
   `turtle-spec`, `turtle-vocab` and `turtle-shapes` blocks generate the `.ttl` files, and
   `turtle-example` blocks are illustration only. Edit the README, never the generated file, then
   regenerate:

   ```bash
   mise exec -- python tools/literate_extract.py ontology/<layer>/README.md --layer <layer> --root .
   ```

   - `turtle-shapes` blocks go, in order, to the shape files named in the layer's entry in the
     [repository catalogue](https://github.com/nebularis/lattice/blob/main/repository-catalogue.md),
     in its README. Adding, removing or reordering a shape block is an edit to that entry.
   - All `turtle-spec` blocks concatenate, in order, into `spec/<layer>.ttl`, and all `turtle-vocab`
     blocks into `vocab/<layer>-vocab.ttl`. The ontology header is itself a block, so a version bump
     is a README edit.
   - A `turtle-spec` block whose **first** line is `# @output-file "spec/<file>.ttl"` goes to that
     file instead, which gains `spec/<layer>.ttl`'s `@prefix` lines (ADR-A120). It states its own
     ontology header. All of a layer's spec documents share one version, bumped together even when
     only one changed. The extractor refuses them otherwise. The same directive works on a
     `turtle-vocab` block, for a module with several vocabulary documents, with its own
     one-shared-version rule independent of the spec documents' version (ADR-A120 addendum). A
     nested module path (`--layer applied/insurance/peril`) is also accepted, its last segment
     naming the default documents.
   - Add `--check` to compare without writing. Run it **before** relying on a README. If the layer
     already drifts, the README is not yet its source (technical debt TD-16). Compare the extracted
     and committed graphs (`rdflib.compare.graph_diff` over `to_isomorphic` graphs) before
     regenerating, and either restore the README or record the drift. A regeneration over a
     drifting layer can silently discard hand-maintained content.
   - A module whose README has no extracted blocks is not literate, and its `.ttl` is edited directly. Persistence and the
     insurance applied modules are literate. Check a README for `turtle-spec` blocks or a `generated` region before editing.
   - A README migrated to the layout of ADR-A126 follows
     [literate-specifications.md](https://github.com/nebularis/lattice/blob/main/docs/architecture/literate-specifications.md):
     a term's axioms are written once, in its Description Logic Encoding section, and markers hide a
     block, exclude text or send a region to another file.
   - **A literate README never says "this document".** One README generates several documents, a
     spec, a vocabulary, shape files and sometimes several spec documents (ADR-A120), and section 1
     becomes the `dct:description` of more than one of them. A sentence such as "this document is the
     configuration half of the layer" is wrong in every generated document but one, and confuses a
     reader of the README itself. Describe the layer and its concepts. Where the split into documents
     matters, it belongs in section 2's document table and section 3's extraction contract, which
     name each file, never in prose that will be extracted.
   - **A README, its examples and its shapes name no delivery identifier**, such as a slice, a plan
     question or a technical debt item, and no delivery phrasing such as "this slice". Skill
     `lattice-publication-hygiene`, "Delivery identifiers stay in working documents", has the rule.
2. **Know which versioning applies.** The modules of the kinds listed in the repository catalogue's `[conventions.release]` (`substrate`, the layers of ADR-A01's order) are one release with one number, held there (ADR-A129). Their shapes and projection directories have no `.version` file. The standalone modules (MORK, SPC, Surface and Persistence), the applied modules and the examples keep their own versions and pin a release (ADR-A86, and ADR-A129's 2026-10-26 addendum). Look the kind up before every bump, in the module README's `[module]` block or from `mise run check:ontology-versioning -- --base-ref main`, whose `HOW` line names each flagged module's kind and how it is bumped, and never assume a module's version follows the release because its number matches.
3. **Bump with `mise run version:bump`, never by hand.** Without `--layer-target` it moves the substrate release through `release:prepare`. With `--layer-target <module>` it moves one standalone or applied module: all of its spec documents to one number, since they move in unison (STD-230, ADR-A120, which the extractor enforces), never one document alone, and its vocab documents not at all, being a unit of their own (STD-222). `--increment major|minor|patch` or `--new-version X.Y.Z` sets the number, and at major version zero a breaking change is a minor (ADR-A113). `--with-shapes` moves the module's `shapes/.version`, one number for every shapes file, by the same increment from its own number, and `--only-shapes` moves it alone. It renames the README's `- **Unreleased**.` lead to the number, extracts each README it changed, regenerates the XML catalogs and the release register, and prints what is left, such as a module whose imports it re-pinned and the tags to create. The mechanics are in `tools/bump_version.py` and `tools/extract_bumped.py`. Read them to answer a detailed question rather than restating them.
4. **A re-pin is a bump of its own.** A substrate release re-pins the imports of every module that imports a member, and each such module then takes its own bump, at the imported change's level (ADR-A86), with `--layer-target`. A pin of this module by another module is that module's to move.
5. **Tests.** `release:prepare` leaves tests alone, since they assert history as well as the present.
   Tests also build IRIs from fragments, such as `LATTICE + "behaviour/0.18.0"`. Move a test that
   locates the current document to the new version, and keep a test that asserts history, a release
   row or a release note. Leave alone `docs/architecture/ontology-releases.md` (generated),
   `tools/test_ontology_releases.py` and `tools/fixtures/import_guard/`.
6. **Record.** `version:bump` has run `build:ontology-catalog` and `build:ontology-releases`, which adds the register rows and prints the tags to create: one `ontologies-vX.Y.Z` for a substrate release, and one `<name>-vX.Y.Z` per document of a module released on its own. The tags are the maintainer's (skill `lattice-lifecycle`). It has renamed each changed README's `- **Unreleased**.` release-note lead to the new number, or said that a README has none to write. Check that every sub-bullet under it opens with its class, *changes meaning*, *may invalidate* or *no effect* (ADR-A129), the form the versioning policy states. A change is written under `Unreleased` when it is made, on its branch, never first at the merge. Its note may cite the Proposed decision it rests on while on the branch, and that decision is accepted before the merge, since a migrated README cites only published decisions (skill `lattice-publication-hygiene`).
7. **Check:** `mise run check:full-sweep` runs all of these but the literate checks, one line each. Or singly: `mise run check:ontology-catalog`, `check:ontology-versioning`, `check:import-guard`, `build:mtp`, `check:mtp`, `check:persistence`, `check:python-root`, `check:vocabulary`, `check:mork-compilers`, and the literate `--check` for every literate layer touched. `build:mtp` rewrites `ontology/mork/mtp/data/pins.lock.json` when MORK's version changes, so commit it. If Persistence's spec, examples or templates changed, run `mise run build:persistence-execution`.
8. **Check the code under test is this checkout's** (skill `lattice-toolchain`).
