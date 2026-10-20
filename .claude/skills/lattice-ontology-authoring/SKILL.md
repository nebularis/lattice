---
name: lattice-ontology-authoring
description: How to change a LATTICE ontology and model well in it. Use when editing anything under ontology/ (a layer README, spec, vocab, shapes, projection or examples), moving the release number or an applied module's version IRI, writing a SHACL or SHACL-SPARQL shape, declaring a domain or range, simplifying a model, or naming a new technical term, in LATTICE or an applied ontology built on it.
---

# Authoring LATTICE ontologies

## Changing an ontology document

Follow every step for any change to `ontology/**/spec/`, `ontology/**/vocab/`, or a `shapes/` or
`projection/` directory. Read the
[versioning policy](https://github.com/nebularis/lattice/blob/main/docs/architecture/ontology-versioning-policy.md)
(ADR-A129, ADR-A86, ADR-A113) first. A skipped step breaks consumers silently, and has done so before.

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
   - Persistence and the applied modules are not literate. Edit their `.ttl` directly.
   - A README migrated to the layout of ADR-A126 follows
     [literate-specifications.md](https://github.com/nebularis/lattice/blob/main/docs/architecture/literate-specifications.md):
     a term's axioms are written once, in its Description Logic Encoding section, and markers hide a
     block, exclude text or send a region to another file.
2. **Know which versioning applies.** The modules of the kinds listed in the repository catalogue's
   `[conventions.release]` (`substrate` and `standalone`, which cover the layers, MORK, SPC,
   Surface and Persistence) are one release with one number, held there (ADR-A129). Their shapes and projection
   directories have no `.version` file. The applied modules and the examples keep their own versions
   and pin a release (ADR-A86).
3. **Move the release for a change to a member.** `mise run release:prepare -- <X.Y.Z>` moves every
   member version IRI, every import of a member, the applied modules' pins, the literate READMEs and
   the tool packages' sources to the new number in one substitution, then regenerates the XML catalogs
   and the release register. At major version zero a breaking change is a MINOR (ADR-A113).
   `check:ontology-versioning` fails with `UNBUMPED` when a member changed and the number did not.
   Where the maintainer has agreed that a working branch defers versioning to its merge into `main`,
   that branch ignores the failure and takes one bump at the merge, as its status record says.
4. **Bump an applied module's or an example's own version.** Change the document's
   `owl:versionIRI`, or a `shapes/` or `projection/` directory's `.version` file. A document whose
   only change is a re-pinned import takes the imported change's bump level (ADR-A86). Build the
   import graph with `find_in_scope_ttl_files` and `extract_version_iris` from
   `tools/ontology_version_check.py`, and close it transitively from the changed IRI, never trusting a
   count. Replace exact IRIs with one regex alternation over the whole old-to-new mapping, so nothing
   is replaced twice.
5. **Tests.** `release:prepare` leaves tests alone, since they assert history as well as the present.
   Tests also build IRIs from fragments, such as `LATTICE + "behaviour/0.18.0"`. Move a test that
   locates the current document to the new version, and keep a test that asserts history, a release
   row or a release note. Leave alone `docs/architecture/ontology-releases.md` (generated),
   `tools/test_ontology_releases.py` and `tools/fixtures/import_guard/`.
6. **Regenerate and record.** `mise run build:ontology-catalog`, then `mise run build:ontology-releases`,
   which adds the register rows and prints the tags to create: one `ontologies-vX.Y.Z` for the
   release, and one per new applied version. The tags are the maintainer's (skill
   `lattice-lifecycle`). Write the release notes in the "Release notes" section of each changed
   README, classing every release change by its effect on a graph valid under the previous release:
   no effect, may invalidate, or changes meaning (ADR-A129).
7. **Check:** `mise run check:full-sweep` runs all of these but the literate checks, one line each. Or singly: `mise run check:ontology-catalog`, `check:ontology-versioning`, `check:import-guard`,
   `build:mtp`, `check:mtp`, `check:persistence`, `check:python-root`, `check:vocabulary`,
   `check:mork-compilers`, and the literate `--check` for every literate layer touched. `build:mtp`
   rewrites `ontology/mork/mtp/data/pins.lock.json` when MORK's version changes, so commit it. If
   Persistence's spec, examples or templates changed, run `mise run build:persistence-execution`.
8. **Check the code under test is this checkout's** (skill `lattice-toolchain`).

## Modelling from reality

**Ask how the law answers first.** Before modelling a legal concept, find how the law and contract
drafting already answer the question: what kind of act it is, who holds what power, where a contract
drafts the rule. Model that, and say so in the design. A model that reflects reality seldom drifts
from it, and is of more use than one shaped for implementation convenience. For example, "Majority
Lenders" is drafted as a defined word that several powers use, so a group's threshold belongs in
that word's meaning, not on each power.

**Reality first, then simplify.** Apply KISS, the ladder and the checks in "Simplifying a model
safely" to a model that already reflects what it models. Never reduce reality's complexity by waving
it away. Where usability or size forces the model to drift, record the drift and the reason beside
it, as documentation.

**Judgements are evaluated, never authored.** Whether declarations meet a rule, whether an exercise
took effect (law I10) and when an amendment was agreed are read from facts by the evaluator. Stating
one as data lets the data disagree with the rule that decides it.

**Facts, meaning and findings live apart.** Instrument holds stated meaning, bound meaning, and the
legal acts the parties did, such as assents and amendments. Behaviour holds what the evaluator
concluded and executed. Behaviour is an abstract state machine that applied ontologies use, and
deployments may implement differently, so outside a domain ontology do not name Behaviour constructs
where a legal concept belongs in Instrument.

**Layers state, code executes.** An ontology layer, Behaviour's runtime document included, is data.
Counting, summing and forcing a deferred value are the evaluator's. A layer may declare what will be
computed and how its result is read, never compute it, and must not depend on a runtime to say what
something means.

**Name the deferral.** A value not known when meaning is stated is deferred in one of two ways. A
binding-time deferral, such as a placeholder taking its value from a variable, is forced by the
instantiator and never survives into bound meaning (law I13). An evaluation-time deferral, such as
the consenting lenders' share of the commitments, is forced by the evaluator at a stated reference
time, may survive into bound meaning, and reads as Undetermined until forced. Say which a construct
is.

**Add only what may be added.** A sum is meaningful only over an extensive quantity, on one unit and
one base, such as commitments in one currency or signed lines on one order. Ratios, rates, ratings
and percentages of different bases are not additive. A proportion states its base. Never sum without
checking.

**The open world carries implied terms.** Statute and case law imply terms no clause states, such as
a duty not to withhold consent unreasonably (`ins:impliedBy`). That is why the model is open-world.
A drafter never gathers every legal influence into the contract, so keep a place for implication
rather than requiring every term to be stated.

## Modelling rules

**Say a design decision once.** Explain it in one place and cross-reference it. Do not explain why
a construct was not used beside the explanation of the one that was.

**Domain and range, sparingly.** `rdfs:domain` and `rdfs:range` are not constraints. They tell a
reasoner that everything carrying the property *is* in the domain, and every value *is* in the
range. A domain of `ins:LegalRelation` on `ins:activity` would make every trigger naming an act a
legal relation. Declare one only where it gives useful design-time entailment, or restates what a
shape already checks. Otherwise say the subject and value in the property's comment and let a shape
check use.

**"Versioned".** A class that is a member of `fnd:Version` is *versioned*: it supports versions,
provenance and the rest. Call a node "a version" only when it is one specific version. The class is
to be renamed `fnd:Versioned` (technical debt TD-20).

**Domain-neutral substrate.** Explain a substrate term from law, contract drafting or computing,
never by appeal to "the market". Never cite a downstream project in a layer README. Prefer examples
from several domains, such as lending, licences, trials and warranties, over insurance ones.

**No market words as technical terms.** A word with a market meaning reads as that meaning to an
insurance reader. "Binder" names a binding authority or a cover note, so producing bound meaning is
**instantiation**, done by an **instantiator**. Check a new term against `docs/glossary.md` and
`ontology/applied/insurance/` first. "Bound" stays where it is technical ("bound meaning",
`ins:boundIn`, `ins:boundFrom`), never alone where it could read as cover. SPC's "binder" is the
process-calculus term and stays.

**A "Formalisation" section names no tool.** Title it "Formalisation". Say what the type means, not
the ADR, the generation mechanism or past evaluations, which are recorded where they were decided.

## Simplifying a model safely

The pressure for a smaller model must never cost logical correctness. Before removing or merging
anything, check:

- **RDF has no override.** A merged view is the union of triples. A node "inheriting" another's
  properties and replacing some ends up with both values, breaking every "exactly one" rule.
  Restate in full and let a generator repeat it.
- **Derivable in the examples is not derivable in general.** Search the scenario catalogues and
  decisions for a case where it differs before deleting a property.
- **Open world.** Removing an assertion does not assert its negation. Check what a reasoner now
  infers, and what it can no longer distinguish.
- **Who reads it without a reasoner.** SHACL and the compilers read asserted triples. A fact moved
  into an axiom disappears for them.
- **Cross-check the roadmap.** Search every sketch and plan naming the term for a scenario the
  simplification breaks, and discuss it with the maintainer if one exists.
- **An accepted ADR wins.** A simplification contradicting one is a new decision.

## SHACL-SPARQL shapes

Read [docs/architecture/efficient-queries-and-shapes.md](../../../docs/architecture/efficient-queries-and-shapes.md) before writing or
changing a constraint query, and follow its checklist (section 4.1). A constraint runs once per focus node, so its cost is multiplied by the
nodes the shape targets. Most of its speed rules (R1 to R4, R8) are workarounds for how rdflib plans a query, and the record says which
rules are portable. A rewrite for speed is a PATCH change to the shapes' version, replayed against the old shapes' results first.

- **Declare prefixes inside the query**, with `PREFIX` lines at the top of `sh:select`, as
  `ontology/eligibility/shapes/constraints.ttl` does. Never point `sh:prefixes` at a namespace IRI
  without `sh:declare` triples for every prefix used, since pySHACL silently falls back to the
  file's `@prefix` lines where other engines fail.
- **A subject with zero matches must still produce a row.** Put the counted pattern in `OPTIONAL`,
  so "exactly one" does not pass when there are none.
- **Choose the counting form by the number of counts.** One count is a flat query, `OPTIONAL { … }`
  then `GROUP BY $this HAVING (COUNT(DISTINCT ?x) != 1)`. Two or more, or high cardinality, need one
  grouped sub-query per count, each anchoring the subject before its own `OPTIONAL`. Several flat
  `OPTIONAL`s multiply rows, which `COUNT(DISTINCT …)` survives and plain `COUNT` and `SUM` do not.
- **To probe that a test catches a broken shape, break a triple pattern**, never `FILTER (false)`.
  rdflib drops a constant false filter, so it removes no solutions (TSD-32), and a `NOT EXISTS` that contains
  one is inverted.
- **Test every cardinality rule at zero**, not only at too many.
- **pySHACL drops a node shape's message reached through `sh:node`.** Put the message on the
  property shape that uses it.
