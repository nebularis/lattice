<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: SVA-O6, one reader of node shapes for the forms and the drawing

**Unit:** [`studio-visual-authoring`](../status/studio-visual-authoring.md), slice SVA-O6, a follow-up to [SVA-O2](SVA-O2.md), built on 2026-11-15 in autonomous mode.

## Invariant

Which node shape targets which class, and which of its property shapes count, is decided in one place, `shapeTargets` and `plainPath` in `src/rdf/shapes.ts`, and the forms and the ontology drawing both read it. A shape targets the classes it names with `sh:targetClass` and itself when it is a named class. A property shape counts when its `sh:path` is a plain IRI. The drawing's behaviour and the forms' merged constraints are as they were.

## What changed

- **`src/rdf/shapes.ts`.** Adds `shapeTargets`, `plainPath` and `readNodeShapes`. `readNodeShapes` gives each node shape that targets a class, with its IRI where it has one, its targets, and each plain-path property shape with its `sh:class` values, its `sh:node` values and the classes those target, all sorted. `readShapes` is unchanged in behaviour and calls the two shared helpers. It was not rebuilt on `readNodeShapes`, since its merge takes the first value of a constraint in the order of the triples, which a sorted reading would change.
- **`src/rdf/ontologyGraph.ts`.** Its own copy of the targeting rule and its own walk over `sh:property` are gone. `shapeEdges` reads `readNodeShapes`.

## Tests

| ID | Given / When / Then | Level | Pass |
|---|---|---|---|
| O6-T1 | a named shape with `sh:targetClass` and a property shape with `sh:class` / `readNodeShapes` / its name, target, path and class | L1, positive | Expected shape |
| O6-T2 | a named class that carries `sh:property` / `readNodeShapes` / the class is the shape and its own target | L1, positive | Expected target |
| O6-T3 | a blank node shape / `readNodeShapes` / no name, the target kept | L1, positive | Name absent |
| O6-T4 | a shape with no target / `readNodeShapes` / left out | L1, negative | Empty |
| O6-T5 | `sh:node` to a named shape with two targets / `readNodeShapes` / the node and its targets, sorted | L1, positive | Expected targets |
| O6-T6 | `sh:node` to a class and to a blank shape / `readNodeShapes` / the targets of each | L1, positive | Expected targets |
| O6-T7 | an inverse path beside a plain one / `readNodeShapes` / only the plain one | L1, negative | One property |
| O6-T8 | several targets, one of them the shape itself, and several classes / `readNodeShapes` / sorted with no repeats | L1, positive | Expected lists |
| O6-T9 | named and blank shapes / `readNodeShapes` / named first, each in order | L1, positive | Expected order |
| O6-T10 | the same triples shuffled six ways / `readNodeShapes` / identical results | L1, positive | Equal results |
| O6-T11 | two shapes for one property / `readShapes` / merged as before | L1, positive | Expected merge |
| O6-T12 | the ontology drawing tests and the vocabulary tests, unchanged / the unit suite / none changes | L1, positive | All pass |
| O6-T13 | the browser suite, unchanged / the fake service / none changes | L3, positive | 31 tests pass |

**The one command:** `mise exec -- yarn workspace @lattice/config-studio exec vitest run src/rdf/shapes.test.ts src/rdf/ontologyGraph.test.ts`, from the repository root. `mise exec -- yarn workspace @lattice/config-studio exec tsc --noEmit` checks the types, and `mise run test:config-studio` runs the browser suite.

## Deliberate non-coverage

- **A shape found only through `sh:node`.** A shape that has no `sh:property` and no target of its own is not listed. It appears only as a target of a `sh:node` link.
- **The forms' constraints.** `readShapes` still reads its own constraint values. Only the targeting rule and the path rule are shared.
- **Shape inheritance and `sh:and`, `sh:or`.** Neither was read before and neither is now.

## Results

What the builder ran on 2026-11-15, in autonomous mode:

- `vitest run`, the whole unit suite, printed 20 files and 319 tests passed, 308 before and the 11 new ones. `ontologyGraph.test.ts` and `vocabulary.test.ts` were not edited. A first run failed on a type slip in `shapes.ts`, fixed before the final run.
- `tsc --noEmit` for `@lattice/config-studio` printed nothing.
- The browser suite, with a temporary Playwright config that points at the Chromium already on this machine, deleted afterwards, printed `31 passed`.
- `git diff --stat -- apps/config-studio/src/rdf/ontologyGraph.test.ts` printed nothing.
- Not run: `mise run check:config-studio` as written, and any run against the live stack.
