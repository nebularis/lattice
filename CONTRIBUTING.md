# Contributing to LATTICE

## Licensing model

LATTICE uses two licences, split by content type:

| Content | Licence | Applies to |
|---|---|---|
| Ontology artefacts | [MPL 2.0](LICENSE) | every `.ttl` file, and everything under `tools/` |
| Documentation and specifications | [CC BY-SA 4.0](LICENSE-DOCS.md) | every `.md` file, including each layer's `README.md` and the planning docs inside `execution/` |

Both are the same shape of licence: permissive to build on, copyleft only on the file itself. You can use LATTICE — ontologies, shapes, vocabulary-inclusion mechanism, reference implementation, specification text — as the foundation of a commercial product, a hosted service, or an internal tool, without any obligation to open-source what you build. The obligation runs the other way: if you take a file from this repository, modify it, and redistribute that modified file, the modification has to carry the same licence forward. Building something that merely *uses* an unmodified LATTICE file, however extensively, never triggers this.

By opening a pull request, you're contributing under the licence that already governs the file or directory you're changing. There's no separate contributor agreement to sign at this stage — see [Contributor License Agreement](#contributor-license-agreement) below for when that might change.

---

## AI-assisted contributions

Using generative AI tooling to help draft ontology content, documentation, or reference-implementation code is welcome. It carries disclosure obligations that are not optional where AI-generated content appears in what you submit: a required commit trailer, a required PR description section, and — for ontology content specifically — a check that the content holds the same domain-neutral line as anything drafted by hand.

**Read [GENAI_CONTRIBUTION.md](GENAI_CONTRIBUTION.md) before opening a PR that includes AI-assisted content.** It covers what has to be disclosed, how, the checks to run before you submit, and how this interacts with the licensing representation above given LATTICE has no CLA to carry it instead.

---

## SPDX headers — required on every file

Every file in this repository needs a one-line `SPDX-License-Identifier` header as its first non-blank line, following the [REUSE specification](https://reuse.software/). This is what lets tooling — and anyone auditing the repository — determine the licence of any given file without cross-referencing a table.

**Ontology files (`.ttl`):**

```turtle
# SPDX-License-Identifier: MPL-2.0
```

**Documentation and specification files (`.md`), including layer READMEs and the planning docs under `execution/`:**

```markdown
<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
```

**Reference implementation source files (`tools/`):** use the header convention native to the language — a `#` comment for Python, `//` for JavaScript/TypeScript, and so on — with the same `MPL-2.0` identifier.

A CI check (`reuse lint`) runs on every pull request and fails the build if a file is missing its header or carries one that doesn't match its location. Add the header when you create the file, not as a cleanup step afterward — it's one line and it's much easier to get right the first time than to retrofit across a growing tree.

---

## Where new content belongs

Each layer follows the shared template described in the top-level README. Two boundaries are worth being explicit about, because they're easy to blur without realising it:

**`vocab/` is for mechanism-intrinsic enumerations only.** Trigger kind, composition-rule type, role type — small, closed sets that are part of how the mechanism works, not what any particular domain calls things. If you find yourself adding a concept that names a business or industry category — a peril type, a jurisdiction list, a product line — it doesn't belong in any layer's `vocab/` folder. That's exactly what `vocabulary/`'s governance-contracts mechanism exists to let a downstream implementation supply on its own, without a pull request against this repository at all. If a proposed `vocab/` addition is hard to justify as mechanism rather than domain, that difficulty is the signal, not something to reason past.

**`spec/`, `shapes/`, `vocab/`, and `projection/` never contain executable code.** These directories are ontology content — Turtle, SHACL, SPARQL — governed by MPL 2.0 as data, not as software. Compilation logic, extraction pipelines, and anything else that runs belongs in `tools/`, licensed the same way but kept in a directory a build process can point at cleanly. CI checks for this boundary and will fail a PR that puts a script inside a layer's ontology directories.

**`applied/` is the place for new domain ontologies.** If you wish to contribute a new domain, put it under here.

---

## Pull request process

1. Add the SPDX header to any new file as you create it.
2. Add or update tests in the relevant layer's `test/` directory for any change to `spec/`, `shapes/`, or `projection/`.
3. If the change affects `execution/` output for a layer, update that layer's `invalidation-policy.md` note if the regeneration behaviour itself has changed — not for every routine regeneration, only when the policy is different.
4. If any content in the PR was AI-drafted or AI-assisted, add the `Generated-by:` commit trailer and the AI provenance section to the PR description — see [GENAI_CONTRIBUTION.md](GENAI_CONTRIBUTION.md).
5. `reuse lint` and the layer's own test suite need to pass before review.

---

## Contributor License Agreement

None is required to contribute at this stage. MPL 2.0's own terms govern every contribution to `.ttl` files and `tools/`; CC BY-SA 4.0 governs every contribution to documentation. This may change specifically for `tools/` if a dual-licensed build of the reference implementation is introduced later, in which case contributors to that directory would be asked to sign a CLA at that point — prospectively, not retroactively applied to anything already merged.

The absence of a CLA is also why [AI-assisted contributions](#ai-assisted-contributions) carry their own explicit disclosure requirement rather than relying on a signed agreement to cover the question — see [GENAI_CONTRIBUTION.md](GENAI_CONTRIBUTION.md) for how that representation works without one.
