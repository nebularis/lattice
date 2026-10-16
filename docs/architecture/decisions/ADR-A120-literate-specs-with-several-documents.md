<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A120: Literate specs with several documents

**Status:** Accepted 2026-10-08, with our assent in the request that raised it
**Date:** 2026-10-08
**Related:** [ADR-A106](ADR-A106-behaviour-configuration-runtime-occasions-and-records.md) (Behaviour's
configuration and runtime documents), [ADR-A86](ADR-A86-ontology-semantic-versioning.md) (semantic
versioning), [ADR-A113](ADR-A113-breaking-changes-at-major-version-zero.md), technical debt TD-16

## Context

A literate layer's `README.md` is its source. `tools/literate_extract.py` concatenates every
`turtle-spec` block into one document, `spec/<layer>.ttl`. ADR-A106 split Behaviour into a
configuration document and a runtime document. The extractor could write only the first, so
`spec/behaviour-runtime.ttl` is authored by hand, outside the README, and nothing checks that it
agrees with the README. Another layer is about to need a second spec document.

## Decision

1. **A directive on a block's first line.** A `turtle-spec` block whose first line is

   ```turtle-spec
   # @output-file "spec/behaviour-runtime.ttl"
   ```

   is written to that file, a `.ttl` path relative to the layer directory, which must stay inside
   it. The directive is read only on the first line, and is not written out. A block without it goes
   to `spec/<layer>.ttl`, as before. Several blocks may name the same file. They concatenate in
   document order.
2. **Shared prefixes.** A redirected document gains the `@prefix` lines of `spec/<layer>.ttl`'s
   blocks, after its SPDX header. Its own blocks state its ontology header (its name, version IRI
   and imports) and its content.
3. **One version per layer.** All of a layer's spec documents carry the same version, and move
   together. The extractor fails if their `owl:versionIRI` versions differ. A change to either
   document bumps both, as one release.
4. **Scope.** `turtle-spec` only. Vocab and shape blocks keep their current targets.

## Consequences

- `--check` covers every spec document a README produces, so a hand-authored second document can
  become literate. Behaviour's runtime document moves into its README in a follow-up.
- A layer releases all its spec documents together, even when only one changed. That overhead is
  deliberate. Independent versions would need per-document cascades and release rows, and no layer
  needs them yet. A layer that does can supersede decision 3.
- The developer contract changes: the authoring skill, the developer guide, the versioning policy
  and `tools/README.md` describe the directive.

## Addendum (2026-10-13, AIR-2.0, Proposed until the applied-insurance-reference trip merges)

Decision 4 widens. The applied insurance domain's modules sit below `ontology/applied/`, nest more
than one segment deep, and some (the peril vocabulary) need several vocabulary documents
(`peril-vocab.ttl`, `peril-intensity.ttl`, `peril-collections.ttl`), not only several spec
documents.

1. **Nested module paths.** `--layer` accepts a path under `ontology/` of more than one segment,
   for example `applied/insurance/peril`. Its last segment names the module's default documents
   (`spec/peril.ttl`, `vocab/peril-vocab.ttl`). A single-segment `--layer` behaves exactly as
   before.
2. **The directive on `turtle-vocab` blocks too.** The same `# @output-file "…"` directive, read on
   a `turtle-vocab` block's first line, must name a `.ttl` path under the module's `vocab/`. A
   redirected vocabulary document gains the default vocabulary document's `@prefix` lines, exactly
   as a redirected spec document does (decision 2).
3. **One version per module, independently for spec and vocabulary.** A module's vocabulary
   documents all carry one `owl:versionIRI` version and move together, the same rule decision 3
   gives the spec documents, but the two version lines are independent of each other: bumping the
   vocabulary need not bump the spec, or vice versa.

The consequences of decision 3 (above) apply equally to a module's vocabulary documents under this
addendum.
