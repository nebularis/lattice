<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: OD7, Vocabulary

**Unit:** [`improved-ontology-documentation`](../status/improved-ontology-documentation.md), slice OD7
([plan](../plans/improved-ontology-documentation.md#od7-vocabulary)).
**Implements:** ADR-A126 for Vocabulary, with OD-D60, and closes Vocabulary's part of TD-16.
**Built autonomously**, 2026-10-19 (OD-D62).

## Invariant

Vocabulary's README is in the 13-section layout and is the source of its spec document and all three shape
files. Every generated file is the same graph as at `ef9c62cf` except for the four differences in
[OD7-reconciliations.txt](OD7-reconciliations.txt), the document's `dct:description`, `dct:creator` and their
declarations.

## What changed

- `ontology/vocabulary/README.md`, migrated:
  - **§2:** header, prefix and creator tables. The header imports SKOS and Foundation 0.4.0, as the file did.
  - **§3:** the extraction contract, and the catalogue entry now naming the three shape files.
  - **§4 Overview:** a short account of contracts, bindings and resolution, and the generated class diagram.
  - **§5 Detailed Design:** today's design decisions and the worked examples.
  - **§6:** 4 class and 7 property entries, each with its definition and utility as the file states them, the
    restriction tables, `**All disjoint.**` in the file's order, `**Disjoint.**` for `skos:Concept` and
    `voc:ConceptScheme` in the file's direction, and `rdf:Property a owl:Class` in 6.6 (OD-D60).
  - **§7:** structural shapes generated from the tables, and the constraints and the comment-only rules file as
    hidden blocks naming their files.
  - **§8 to §13:** examples, Not applicable twice, dependencies, release notes rebuilt from git history, and the
    open items that still hold.
- `tools/test_literate_extract.py`. AIR20-05 checks Vocabulary too.

## Decisions taken alone, for the maintainer

1. **Utility text is the file's**, where the README's prose had drifted from it, for example ConceptScheme's
   utility ending "to record its review status".
2. **The SKOS alignment sits in the entry**, as `**Subclass of.** ... skos:ConceptScheme`, since the layout
   states a term's axioms once, in its entry. Today's §3 note about stating alignments only in an Alignments
   section is retired with it.
3. **Two comments in the hidden constraints block** referred to a sketch and to a guide section. They are
   reworded, since a hidden block is user-facing and comments are not part of the graph.
4. **Old open items dropped:** the version note about `vocabulary/0.0.2`, the note that the Turtle was never
   parsed, and Foundation's alignment tidy-up, which belongs to Foundation's migration. The resolution shapes item
   is narrowed to strict-superset precedence, which the constraints cannot decide.
5. **Prose semicolons** in moved text are rewritten. Two remain inside `fnd:utility` literals, where changing them
   changes the graph, so they wait for a release.
6. **The constraints' messages cite "README §4 invariant" numbers** that no longer exist. Listed as an open issue
   for the same reason.

## Test cases

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| OD7-T1 | the migrated README / the migration check against `ef9c62cf` with the reconciliations / passes, 4 reconciled | L5 | + |
| OD7-T2 | the migrated README / the extractor with `--check` / 4 artefacts and the README's regions consistent | L4 | + |
| OD7-T3 | the layer / AIR20-05, Vocabulary's own tests, the catalogue and sources checks / pass | L3 | + |

## Commands

```bash
mise run check:literate-migration -- vocabulary ef9c62cf --reconciliations docs/developer/validation/OD7-reconciliations.txt
```

```bash
mise run check:vocabulary
```

## Results

2026-10-19: OD7-T1 passes with 4 reconciled differences. OD7-T2: 4 artefacts consistent. `check:vocabulary` 16
passed. `check:catalogue` and `check:published-decisions` pass, with no sources failure. The extraction, catalogue
and Eligibility suites: 204 passed.

## Deliberate non-coverage

- The class diagram was not rendered in a browser. It uses only constructs OD5 and OD6 rendered.
- Versions. OD-REL releases the layer at 0.18.0.
