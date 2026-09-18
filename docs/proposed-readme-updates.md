<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Proposed updates to the top-level README

**Status:** investigative draft for review. Nothing in this document has been applied to `README.md` or any other file. Each section below names the exact spot in the current `README.md` to change, what kind of change it is (add / replace / remove), and the proposed text.

This is based on everything currently uncommitted in the working tree (`git status` — see the appendix), read in full: the new `surface/` layer, the new `applied/` directory, the fleshed-out `tools/` folder, the MORK `ProjectionMapping` addition, the Eligibility `HierarchicalMatch` change, and the new `docs/glossary.md` and `docs/adr/ADR-A16-*.md`. Small copy-editing diffs (`quantification/README.md`, `.vscode/settings.json`) don't reach the top-level README and aren't covered here.

---

## 0. Summary of what's driving these changes

| New/changed thing | What it is |
|---|---|
| `surface/` (untracked, whole directory) | A new, 8th ontology layer: **Surface** — declares *promotion* (restate a reachable value as a direct assertion) and *indexing* (restate a value as a retrievable symbol). Low in the dependency order: imports Foundation, Vocabulary, Quantification; imported by nothing else in the substrate. Has its own worked examples, a design-sketch and outstanding-items doc, and one compiled-output stub under `execution/`. |
| `docs/adr/ADR-A16-surface-projection-mechanism.md` (untracked) | The ADR accepting the Surface layer. `docs/adr/README.md` (modified) already indexes it. |
| `docs/glossary.md` (untracked) | A new top-level, domain-neutral glossary — currently scoped to the Surface subsystem's vocabulary (carrier, contract, read path, promotion, indexing, etc.), explicitly written as "a drop-in section for the README(s)." |
| `applied/` (untracked, whole directory) | A **new top-level concept**: a home for ported/staged applied-domain ontologies, distinct from both `instrument/` (the generic upper ontology) and `examples/` (worked scenario instances). Currently contains `applied/insurance/` — a hand-ported insurance contract-structure ontology (`ctr:`). `applied/README.md` describes it as: "Lattice ships with several domains, at varying levels of maturity. Each domain is housed beneath this folder... and follows the same structure as any other ontology layer." |
| `tools/README.md`, `tools/literate_extract.py`, `tools/surface/` (all untracked) | `tools/` goes from a one-line mention to an actual documented reference implementation: a README⇄spec drift checker (`literate_extract.py`) and a full surface-contract compiler package (`tools/surface/`: compile, check freshness, parity, and lift/lower to/from MORK). |
| `mork/spec/Mork.ttl` (modified) | MORK gains `mrk:ProjectionMapping`, a new `GenerativeMapping` subtype that ties a MORK mapping directly to Surface: a mapping can now *propose* a surface contract, and a compiled surface can be lifted back into a MORK provenance record. |
| `eligibility/README.md` + spec/vocab/shapes (modified) | `HierarchicalMatch` no longer requires a hand-materialised local closure — it may now be backed by a **generated Surface index** instead of (or as well as) query-time traversal. This is the first concrete cross-layer consumer of Surface. |

Everything below is organized as edits against the *current* `README.md`, quoting the exact text being replaced.

---

## 1. Overview → MORK paragraph

**Location:** the `**MORK (...)**` paragraph, line 13.

**Action:** append one sentence.

**Current text ends:**
> ...`mork/targets/` is a configuration that points it at LATTICE specifically.

**Add after it:**
> A MORK mapping can also *propose* a lookup-surface (see Surface, below): a `mrk:ProjectionMapping` records the generated class it proposes, so a Surface contract can trace back through a mapping to the source text that motivated it, and a compiled surface can be lifted into that record for review before it's promoted to a governed contract.

---

## 2. Overview → Model Layers table and count

**Location:** line 23 ("LATTICE is organised as seven layers...") and the table at lines 25–34.

**Action:** replace "seven" with "eight"; add a new table row for Surface.

**Current:**
```
LATTICE is organised as seven layers, each an independent OWL/SHACL/SKOS module:

| Layer | Kind | What it models |
|---|---|---|
| **Foundation** | Substrate | ... |
| **Vocabulary** | Substrate | ... |
| **Quantification** | Substrate | ... |
| **Party** | Substrate | ... |
| **Eligibility** | Substrate | ... |
| **Behaviour** | Substrate | ... |
| **Instrument** | Applied domain ontology | ... |
```

**Proposed:**
```
LATTICE is organised as eight layers, each an independent OWL/SHACL/SKOS module:

| Layer | Kind | What it models |
|---|---|---|
| **Foundation** | Substrate | Identity, versioning, provenance and evidence, governance state, temporal scoping. |
| **Vocabulary** | Substrate | The governed mechanism by which external, domain-specific concept schemes get bound into the other layers without touching their core specifications. |
| **Quantification** | Substrate | Declared value spaces, quantities, ordered values, bounds, ranges, conversion, granularity, and recurrence — the mechanism behind any magnitude, interval, or ordinal comparison the other layers need. |
| **Surface** | Mechanism *(see note)* | Declares how part of a declaration graph may be restated locally as query-friendly symbols, without changing what the source means: *promotion* (a reachable value restated as a direct property) and *indexing* (a value restated as a symbol subjects can be retrieved by). Imports Foundation, Vocabulary, and Quantification; sits low in the dependency order and is imported by nothing else in the substrate — it names other layers' terms by punning rather than by import. |
| **Party** | Substrate | Actors, the roles they occupy, and the direction and composition of obligation between them (e.g., modelling independently capped shares, joint obligation with a right of recourse, delegated accountability, or contingent role occupancy). |
| **Eligibility** | Substrate | Admissibility criteria (conditions, unresolved questions, and decisions). |
| **Behaviour** | Substrate | State, transition, trigger, and effect, including a usable `Sequential` allowance profile. `Proportional` allowance semantics and reset edge cases remain explicitly deferred. |
| **Instrument** | Applied domain ontology | A primary domain ontology built on the substrates, giving the generic shape of a governing document, e.g., Provision → Obligation → Qualifier. |
```

*Note on the "Mechanism" kind:* Surface doesn't fit either existing `Kind` value cleanly — it's domain-neutral like a substrate layer, but it isn't part of the main import chain (nothing above imports it; it reaches other layers' terms by punning) and it produces *generated, disposable* artefacts rather than authored semantics that other layers build on. "Mechanism" is a suggested label, not a settled one — **flagging this cell specifically for the author's own call** on what to name the category, rather than asserting it.

*Placement note:* the row above places Surface between Quantification and Party to match its declared import order (Foundation, Vocabulary, Quantification) per ADR-A16 and its own README — not because it sits in the Party→Eligibility→Behaviour chain, which it doesn't.

---

## 3. Overview → paragraph after the Model Layers table

**Location:** line 35, immediately after the table.

**Action:** add a paragraph. This is where the new `applied/` directory belongs conceptually — it's the concrete realisation of the "different applied domain ontology" the existing text already gestures at.

**Current text (unchanged, kept as-is):**
> Instrument is a first layer building on the substrates. A different applied domain ontology (e.g., a device's operational lifecycle, access-control entitlement system, asset maintenance schedule, etc) could sit atop Instrument or even replace it, composing with the same Party, Eligibility, and Behaviour mechanisms through its own `projection/` contracts, without touching any of the core specifications.

**Add immediately after:**
> `applied/` is where these domain ontologies are staged as they're ported in, at whatever level of maturity they've reached — see [Repository layout](#repository-layout) below. The first is `applied/insurance/`, a hand port of an existing insurance contract-structure ontology. **As currently committed it has no `projection/` contracts of its own and imports a namespace outside the `neuro-semantic/lattice` tree** — it is staged content, not yet wired into the substrate the way this paragraph describes. Treat anything under `applied/` as a domain ontology in progress rather than a worked composition until it declares `projection/` contracts against Party, Eligibility, or Behaviour.

---

## 4. Repository Layout (generic per-layer template) → `tools/` line

**Location:** line 63, inside the fenced template block's closing description:
> The `tools/` folder holds reference implementations handling compilation. It's licensed separately from everything else in the tree — see [Licensing](#licensing).

**Action:** replace with a slightly fuller description now that `tools/` has real, documented content (previously this was a placeholder-level description; the folder held only `mork2rml.py` and a `.gitkeep`).

**Proposed:**
> The `tools/` folder holds reference implementations handling compilation — currently the MORK→RML compiler (`mork2rml.py`), the README⇄spec drift checker (`literate_extract.py`), and the Surface contract compiler (`surface/`). See `tools/README.md` for usage. It's licensed separately from everything else in the tree — see [Licensing](#licensing).

---

## 5. `## Repository layout` (the actual tree) — several changes

**Location:** lines 69–105, the fenced `lattice/` tree.

**Action:** insert `surface/` into the layer list, insert a new top-level `applied/` block, expand the `docs/` and `tools/` entries, and annotate `examples/` with its current (empty-placeholder / superseded) state.

**Current:**
```
lattice/
├── README.md
├── LICENSE                  # MPL 2.0 — ontology artefacts, tools/
├── LICENSE-DOCS.md          # CC BY-SA 4.0 — documentation, specifications
├── CONTRIBUTING.md
│
├── foundation/              # Foundation Layers (provenance, versioning)
├── vocabulary/              # Inclusion of Domain-specific Vocabularies 
├── quantification/          # Value Spaces, Quantities, Ranges, Recurrence
├── party/                   # Parties, Roles, & Participation Modelling 
├── instrument/              # Governing Instrument (Upper Domain Ontology)  
├── eligibility/             # Eligibility Criteria Modelling 
├── behaviour/               # Behaviour Modelling 
├── mork/                    # Mapping Vocabulary
├── spc/                     # Orchestration calculus (standalone, unintegrated)
│
├── governance/              # Cross-layer governance
│   ├── scheme-contracts/
│   ├── parity/
│   └── shapes/
│
├── docs/
│   ├── architecture/
│   └── adr/
│
├── examples/                # Cross-layer composition scenarios
│   ├── employment.ttl
│   ├── lending-covenant.ttl
│   ├── saas-subscription.ttl
│   ├── clinical-trial.ttl
│   └── insure-o/            # Applied validation package for insurance-style substrate checks
│
├── test/                    # Whole-graph CI
│
└── tools/                   # Reference implementation
```

**Proposed:**
```
lattice/
├── README.md
├── LICENSE                  # MPL 2.0 — ontology artefacts, tools/
├── LICENSE-DOCS.md          # CC BY-SA 4.0 — documentation, specifications
├── CONTRIBUTING.md
├── GENAI_CONTRIBUTION.md    # disclosure obligations for AI-assisted contributions
│
├── foundation/              # Foundation Layers (provenance, versioning)
├── vocabulary/              # Inclusion of Domain-specific Vocabularies 
├── quantification/          # Value Spaces, Quantities, Ranges, Recurrence
├── surface/                 # Promotion & indexing: generated, local, query-facing restatements
├── party/                   # Parties, Roles, & Participation Modelling 
├── instrument/              # Governing Instrument (Upper Domain Ontology)  
├── eligibility/             # Eligibility Criteria Modelling 
├── behaviour/               # Behaviour Modelling 
├── mork/                    # Mapping Vocabulary
├── spc/                     # Orchestration calculus (standalone, unintegrated)
│
├── applied/                 # Ported/staged applied-domain ontologies, varying maturity
│   └── insurance/           # Insurance contract-structure port — not yet wired via projection/
│
├── governance/              # Cross-layer governance
│   ├── scheme-contracts/
│   ├── parity/
│   └── shapes/
│
├── docs/
│   ├── architecture/
│   ├── adr/                 # includes ADR-A16, Surface projection mechanism
│   └── glossary.md          # plain-language glossary (currently: Surface subsystem terms)
│
├── examples/                # Cross-layer composition scenarios — currently all placeholder/empty
│   ├── employment.ttl
│   ├── lending-covenant.ttl
│   ├── saas-subscription.ttl
│   ├── clinical-trial.ttl
│   └── insure-o/            # Applied validation package for insurance-style substrate checks
│                             #   — confirm against applied/insurance/ before treating both as current
│
├── test/                    # Whole-graph CI
│
└── tools/                   # Reference implementation
    ├── README.md
    ├── mork2rml.py           # MORK → RML/R2RML compiler
    ├── literate_extract.py   # README ⇄ spec/vocab/shapes drift check
    └── surface/              # Surface contract compiler (compile / check / parity / mork lift-lower)
```

**Notes for the author, not asserted as fact above:**
- All four files under root `examples/` (`employment.ttl`, `lending-covenant.ttl`, `saas-subscription.ttl`, `clinical-trial.ttl`) are currently **zero bytes**. That predates this batch of changes, but it's now more conspicuous: `surface/examples/` has three fully worked, populated `.ttl` files using two of the same domain names (`saas-subscription-currency.ttl`, `clinical-trial-crosswalk.ttl`) at the single-layer level. Worth deciding whether the root `examples/` files are meant to be filled in as cross-layer compositions built *on top of* the single-layer ones, or renamed/removed.
- `examples/insure-o/` and `applied/insurance/` look like two different snapshots of the same domain (insurance contract structure) at different points in its life — the Surface layer's own outstanding-items note says explicitly: *"you are dropping the current insure-o and porting CSO and FBO by hand"* into what is now `applied/insurance/`. If that's accurate, `examples/insure-o/` may be slated for removal rather than something to document as current. This document doesn't remove it, since that's a judgement call, not an investigative finding.
- `tools/README.md` (as currently written) documents the drift checker at the path `tools/lattice/literate_extract.py`, but the actual untracked file sits at `tools/literate_extract.py` — no `tools/lattice/` directory exists. That's a documentation bug worth fixing at the source (`tools/README.md`) rather than something to paper over in the top-level README; flagged here so it isn't silently propagated into the tree above.
- `GENAI_CONTRIBUTION.md` is not new (it predates this batch of changes and isn't part of `git status`), but it's also not currently listed in the root tree at all — added above only because the tree was otherwise being rewritten; drop that line if it's out of scope for this pass.

---

## 6. `## How the layers interact` — dependency diagram

**Location:** lines 111–123, the fenced dependency diagram and the paragraph after it.

**Action:** add a line for Surface's position, and add one bullet to "a few common compositions."

**Current:**
```
foundation
    └── vocabulary
            └── quantification
                    └── party
                            ├── eligibility
                            │       └── instrument
                            └── behaviour   (imports instrument, eligibility, party, quantification)

mork — targets any layer
spc  — standalone today; not yet imported by, or importing, any layer above
spc  — leverages domain ontology axioms to form session types once a separate integration effort defines the needed contracts
```

**Proposed:**
```
foundation
    └── vocabulary
            └── quantification
                    └── party
                            ├── eligibility
                            │       └── instrument
                            └── behaviour   (imports instrument, eligibility, party, quantification)

surface — imports foundation, vocabulary, quantification; imported by nothing above.
          Names other layers' terms by punning, not by import — it can be introduced or
          removed without any layer's own specification changing.

mork — targets any layer; can also propose a surface contract via mrk:ProjectionMapping
spc  — standalone today; not yet imported by, or importing, any layer above
spc  — leverages domain ontology axioms to form session types once a separate integration effort defines the needed contracts
```

**And add to the "common compositions" bullet list** (after the existing three bullets at lines 127–129):
> - **Eligibility's hierarchical match can be backed by a Surface index.** `HierarchicalMatch` no longer requires a hand-maintained closure — evaluation may compute the closure at query time or resolve it against a generated Surface `ClosureRelation`/`NominalClass` pair over the same bound scheme, and either is a valid way to discharge the underlying law.

---

## 7. Licensing — no substantive change, one optional clarifying line

**Location:** lines 133–139.

**Action:** none required. `surface/`, `applied/`, and `tools/surface/` all fall cleanly under the existing two-licence split (`.ttl`/code under MPL 2.0, `.md` under CC BY-SA 4.0), so the existing text is already accurate. Not proposing a change here — noted only so it isn't mistaken for an oversight.

---

## Appendix: what this proposal is based on

`git status` at investigation time (working tree, uncommitted):

```
 M .vscode/settings.json
 M docs/adr/README.md
 M eligibility/README.md
 M eligibility/shapes/rules.ttl
 M eligibility/spec/eligibility.ttl
 M eligibility/vocab/eligibility-vocab.ttl
 M mork/spec/Mork.ttl
 M quantification/README.md

?? .github/prompts/plan-surfaceOutstandingItemsRemediation.prompt.md
?? applied/insurance/
?? docs/adr/ADR-A16-surface-projection-mechanism.md
?? docs/glossary.md
?? surface/
?? tools/README.md
?? tools/literate_extract.py
?? tools/surface/
```

Read in full for this proposal: `surface/README.md`, `surface/docs/*.md` (including both `OUTSTANDING-ITEMS.md` and the duplicate `OUTSTANDING-ITEMS 2.md`, which differ — worth reconciling, not done here), `docs/adr/ADR-A16-*.md`, `docs/glossary.md`, `applied/README.md` and a sample of `applied/insurance/spec/structure/contract.ttl`, `tools/README.md`, the diffs for every modified file above, and `.github/prompts/plan-surfaceOutstandingItemsRemediation.prompt.md` (an internal planning artefact — not proposed for README inclusion, but useful corroboration for several notes above, e.g. the insure-o → applied/insurance transition).

Not covered above because they don't reach the top-level README: the `quantification/README.md` diff (prose tightening only, no new mechanism), `.vscode/settings.json` (editor config).
