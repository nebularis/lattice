<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Ontology Versioning Policy

Governs every `owl:Ontology` document under `ontology/` — every `spec/<layer>.ttl`
and `vocab/<layer>-vocab.ttl`, plus the directly-authored ontologies
(Persistence, MORK's `Mork.ttl`/`Executable.ttl`, SPC, and applied domain
ontologies) that carry their own `owl:versionIRI`. Decided in
[ADR-A86](decisions/ADR-A86-ontology-semantic-versioning.md); read that ADR
first for the *why*. This document is the *how*: the checklist a human
contributor or an agentic coding assistant applies before committing a change.

Adopts [Semantic Versioning 2.0.0](https://semver.org/) (`X.Y.Z` —
MAJOR.MINOR.PATCH) unmodified. If you have not read `semver.md`'s summary,
read it now; this document only translates its three rules into ontology
terms.

## The versioning unit

**One `owl:versionIRI` per `owl:Ontology` document.** `spec/<layer>.ttl` and
`vocab/<layer>-vocab.ttl` are two independently versioned documents — a
change to one never bumps the other. `shapes/*.ttl` and `projection/*.ttl`
declare no `owl:Ontology` of their own; a change there is covered by whichever
of the layer's `spec` or `vocab` version it motivates a bump of (usually
`spec`, since most SHACL shapes constrain classes and properties `spec`
declares).

## What changes the number

Software semver defines API breakage in terms of function signatures. An
ontology's public API is what a *consumer's data* is checked against: what a
reasoner or a SHACL engine accepts or rejects, and what a term is documented
to mean.

| Bump | An ontology change is this kind when it... | Worked example |
|---|---|---|
| **PATCH** (Z) | Corrects prose or a shape so it matches what was already documented as intended, with no change to what a correctly governed consumer graph experiences. | Fixing an `rdfs:comment` or `fnd:utility` string that misdescribed a term; fixing a SHACL `sh:message`; a Turtle syntax/whitespace fix with no triple-level change; a broken cross-reference. |
| **MINOR** (Y) | Adds something backward compatible: a consumer graph that conformed before still conforms, unchanged in meaning, after. | A new class, property, or `vocab/` individual; a new *optional* SHACL property shape (`sh:minCount 0`) or a `sh:Warning`-severity shape; widening a cardinality restriction; marking a term deprecated while it still works (`semver.md` §7 requires this one). **Worked example from this repository:** the `vocabulary-temporal-binding` unit's `voc:SchemeBinding`, `voc:BindingScope`, and four binding properties (commit `65ac4a85e`) added a wholly new, optional mechanism alongside the existing `voc:boundScheme` — every graph that conformed under the old `voc:SchemeContract` shape still conforms unchanged. That is a MINOR bump of `vocabulary/spec/vocabulary.ttl`, not a PATCH (it adds real new terms) and not a MAJOR (nothing existing narrows or disappears). |
| **MAJOR** (X) | Removes, renames, or narrows something such that a previously conformant consumer graph, or a previously valid statement's meaning, can stop holding. | Removing/renaming a class, property, or individual; narrowing a cardinality restriction; a new `sh:Violation`-severity shape, `sh:closed true`, or `owl:disjointWith` that a real existing graph could now fail; a domain/range narrowing; changing the ontology IRI itself. **Worked hypothetical:** if `voc:SchemeContract`'s `constrainsProperty` were changed from `minCount 1` (optional beyond that) to `exactly 1` with a new `sh:maxCount 1`, any existing contract legitimately naming zero or several properties would newly fail — that is MAJOR, even though it looks like "just a tighter shape." |

Two categories do not reduce to axiom-diffing:

- **Silent semantic redefinition.** The IRI and the axioms are unchanged, but
  the layer's own "Design decisions" prose now means something different.
  This is a MAJOR change even when no SHACL shape moves. Classification here
  is a judgement call against the layer's own README, made by whoever is
  authoring the change (human or agentic), and stated with its reasoning in
  the pull request — not inferred from a diff.
- **Cross-layer import pinning.** `owl:imports` in this repository pins an
  *exact* `owl:versionIRI`. Bumping any layer's version obliges updating
  every importing layer's `owl:imports` statement (and README `turtle-spec`
  source, where one mirrors it) in the *same* change, or the graph stops
  resolving.
- **Import-only changes take the imported level.** A document whose only
  change is an updated `owl:imports` takes the bump level of the change it
  imports, applied transitively, because its own consumers see that change
  through its import closure. Proposed in the
  [ADR-A86 addendum](decisions/ADR-A86-ontology-semantic-versioning.md#addendum-2026-09-25-guarantees-consumers-rely-on),
  item 1, and applied since the `applied-ontology-readiness` unit's AOR-2.

## The import-pinning cascade checklist

Before bumping any layer's version:

1. Enumerate every importer: `grep -rl "owl:imports.*<old-versionIRI-substring>" ontology/`
   (substitute the exact base, e.g. `neuro-semantic/lattice/foundation/`) across
   the whole `ontology/` tree, not just the layer's own directory — an import
   can live in another layer's `spec/*.ttl`, its mirrored README `turtle-spec`
   block, an unrelated example/test fixture, or (rarely) a hardcoded string in
   `tools/` reference-implementation code that stamps generated output with an
   ontology IRI (see `tools/surface/src/surface/namespaces.py`'s
   `SURFACE_ONTOLOGY` constant for a real instance of this last case).
2. Update every one of those references to the new `owl:versionIRI` in the
   same change. A bare, unversioned `owl:imports` target (MORK's `Mork.ttl` is
   imported this way by several of its own example/test fixtures) is a
   deliberate, separate choice some importers make to always resolve against
   "whatever Mork currently is" rather than pin a release; leave those alone
   unless the specific file's own convention is to pin exactly, matching its
   siblings.
3. Re-run the enumeration in step 1 after editing — it should return nothing
   for the old IRI.

Keeping exact-IRI pinning (rather than adopting a dependency-range import
mechanism) is this repository's current, deliberate choice — see ADR-A86's
"Open questions" if the cascade cost ever becomes a real source of friction.

## Where the number physically lives

**The seven literate-spec layers** (Foundation, Vocabulary, Quantification,
Party, Eligibility, Instrument, Behaviour) plus Surface: for the layers whose
README mirrors the ontology header in its own `turtle-spec` fenced block
(check with `grep -l "owl:versionIRI" ontology/<layer>/README.md` — today
that is Eligibility, Instrument, Behaviour, and Surface), edit the version in
*both* the README and the generated `spec/`/`vocab/` file, since
`tools/literate_extract.py` is meant to keep them identical.

**A known, pre-existing gap this policy does not paper over:**
`tools/literate_extract.py --check` does not currently pass for any of the
seven core layers — Foundation's, Vocabulary's, and Party's committed
`spec/*.ttl` predate the extraction tool's own output conventions entirely
(hand-authored/differently-generated Turtle, not a `turtle-spec` concatenation),
and Quantification, Eligibility, Instrument, Behaviour, and Surface's README
`turtle-shapes` blocks do not agree with the `--shapes` arguments the tool
needs to run without error. This was discovered, not introduced, while
implementing ADR-A86's baseline reset (2026-09-25): the reset edited the
version/import lines directly, in both the README and the generated file, by
hand, rather than by running the extraction tool, precisely because running
it would have overwritten unrelated, already-drifted content with a full,
differently-formatted regeneration — well outside this unit's scope. Treat
`tools/literate_extract.py --check` passing repository-wide as a separate,
future remediation unit, not a promise this policy makes.

**Persistence, MORK (`Mork.ttl`, `Executable.ttl`), SPC, and applied domain
ontologies** (`ontology/applied/*`) author their `owl:versionIRI` directly in
the committed `.ttl` file — there is no README mirror to keep in sync for
these.

## The one-time baseline reset (2026-09-25)

Every in-scope document was reset to **`0.2.0`** in the same change that
introduced this policy, per ADR-A86. This is an administrative
normalisation, not a claim that any layer took seven, or three, or one MINOR
release to get there — see the ADR's "Consequences." The full before/after
table:

| Document | Before | After |
|---|---|---|
| `foundation/spec/foundation.ttl` | `neuro-semantic/foundation/0.0.7` | `neuro-semantic/lattice/foundation/0.2.0` |
| `foundation/vocab/foundation-vocab.ttl` | `neuro-semantic/foundation-vocab/0.0.1` | `neuro-semantic/lattice/foundation-vocab/0.2.0` |
| `vocabulary/spec/vocabulary.ttl` | `neuro-semantic/vocabulary/0.0.2` | `neuro-semantic/lattice/vocabulary/0.2.0` |
| `quantification/spec/quantification.ttl` | `neuro-semantic/quantification/0.0.1` | `neuro-semantic/lattice/quantification/0.2.0` |
| `party/spec/party.ttl` | `neuro-semantic/party/0.0.3` | `neuro-semantic/lattice/party/0.2.0` |
| `party/vocab/party-vocab.ttl` | `neuro-semantic/party-vocab/0.0.1` | `neuro-semantic/lattice/party-vocab/0.2.0` |
| `eligibility/spec/eligibility.ttl` (+ README mirror) | `neuro-semantic/eligibility/0.0.1` | `neuro-semantic/lattice/eligibility/0.2.0` |
| `eligibility/vocab/eligibility-vocab.ttl` | `neuro-semantic/eligibility-vocab/0.0.1` | `neuro-semantic/lattice/eligibility-vocab/0.2.0` |
| `instrument/spec/instrument.ttl` (+ README mirror) | `neuro-semantic/instrument/0.0.1` | `neuro-semantic/lattice/instrument/0.2.0` |
| `instrument/vocab/instrument-vocab.ttl` (+ README mirror) | `neuro-semantic/instrument-vocab/0.0.1` | `neuro-semantic/lattice/instrument-vocab/0.2.0` |
| `behaviour/spec/behaviour.ttl` (+ README mirror) | `neuro-semantic/behaviour/0.0.1` | `neuro-semantic/lattice/behaviour/0.2.0` |
| `behaviour/vocab/behaviour-vocab.ttl` | `neuro-semantic/behaviour-vocab/0.0.1` | `neuro-semantic/lattice/behaviour-vocab/0.2.0` |
| `surface/spec/surface.ttl` (+ README mirror + `tools/surface`'s `SURFACE_ONTOLOGY` constant) | `neuro-semantic/surface/0.0.1` | `neuro-semantic/lattice/surface/0.2.0` |
| `surface/vocab/surface-vocab.ttl` (+ README mirror) | `neuro-semantic/surface-vocab/0.0.1` | `neuro-semantic/lattice/surface-vocab/0.2.0` |
| `persistence/spec/persistence.ttl` | `lattice/persistence/0.1.0` | `lattice/persistence/0.2.0` (base already correct) |
| `mork/spec/Executable.ttl` | `lattice/executable/0.0.1` | `lattice/executable/0.2.0` (base already correct) |
| `mork/spec/Mork.ttl` | *(no `owl:versionIRI` at all)* | `http://www.nebularis.org/ontologies/Mork/0.2.0` — first assignment, in MORK's own pre-existing namespace family, not migrated to `lattice/` |
| `spc/spec/spc.ttl` | *(no `owl:versionIRI` at all)* | `http://example.org/spc/0.2.0` — first assignment, in SPC's current (pre-ADR-A62-harmonisation) namespace |
| `applied/capacity/.../applied_capacity_execution_spec_capx_Version2.ttl` | `lattice/applied/capacity/execution/0.0.1` | `lattice/applied/capacity/execution/0.2.0` (base already correct) |
| `applied/insurance/spec/structure/contract.ttl` | `owl:versionIRI` `insurance/contract/0.1.1` **and** `owl:versionInfo "3.5.1"` (disagreeing) | `owl:versionIRI` `insurance/contract/0.2.0`; `owl:priorVersion` updated to `0.1.1`; `owl:versionInfo` dropped — `owl:versionIRI` is now the single authoritative signal. Namespace family (`insurance/`, outside `lattice/`) deliberately left as-is; see the open question below. |

Every `owl:imports` statement anywhere in `ontology/` that named one of the
"Before" IRIs above was updated to the corresponding "After" IRI in the same
change (the cascade checklist above), including the additional example
fixture `ontology/mork/examples/Governance/GovernanceAndVersioning.ttl` and
the illustrative MCN snippet in `docs/architecture/mork-compact-notation.md`.
MORK's own bare (unversioned) `owl:imports <http://www.nebularis.org/ontologies/Mork>`
references, used by several of its example/test fixtures, were deliberately
left unversioned — see the checklist's step 2.

**Still open, per ADR-A86:** whether `applied/insurance/contract.ttl`'s
namespace family (`neuro-semantic/insurance/...`, outside the `lattice/` tree
every other in-scope document uses) is deliberate applied-layer independence
or an oversight. Not decided by this reset.

## Applying this to a new change

1. Classify the change against the table above. If it is a silent semantic
   redefinition, say so explicitly in the PR, with the reasoning — do not
   rely on the table alone to justify a PATCH or MINOR label for a change
   that actually redefines what a term means.
2. Bump the correct document(s) only — `spec` and `vocab` are independent;
   bumping one because the other changed is itself a documentation error.
3. Run the import-pinning cascade checklist for every bump, PATCH included
   (see "The one subtlety," below).
4. Where a README mirrors the ontology header, edit both, keeping them
   identical for that block.
5. Regenerate the catalogs with `mise run build:ontology-catalog`, since a new
   version IRI needs a catalog entry before any importer resolves it
   ([ADR-A88](decisions/ADR-A88-ontology-import-resolution-for-consumers.md)).

### The one subtlety: PATCH still bumps the version

A PATCH bump changes the *version number*, even though the change itself was
"backward compatible with no visible axiom change" — the version number is
what tells a consumer that *something* changed at all, distinct from the
content-level classification of what kind of change it was. Do not confuse
"this was a small change" with "this needs no version bump." The narrow
tooling check described next exists specifically to catch this confusion.

## Enforcement

No tool in this repository classifies a change as MAJOR/MINOR/PATCH
automatically — that is a research problem, not a checklist, and this policy
does not attempt it. What is enforced is narrower and purely mechanical: a
change to an in-scope `.ttl` file's content must be accompanied by a change to
that file's own `owl:versionIRI` literal. A document under a `spec/` or
`vocab/` directory must also carry an `owl:versionIRI` at all. Examples and
test fixtures are exempt. Both checks read only files git tracks or would
track, so ignored build output is out of scope.

A generated document carries a content-addressed version IRI instead of a
semantic version: its ontology IRI followed by the first 16 hex digits of its
canonical hash, taken without the version IRI (ADR-A86 addendum,
item 5). The Surface compiler stamps it when it writes a module. See `tools/ontology_version_check.py` and
`mise run check:ontology-versioning`. The `platform` workflow runs the same
check against `origin/main`.
