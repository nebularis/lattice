---
name: lattice-ontology-authoring
description: How to change a LATTICE ontology and model well in it. Use when editing anything under ontology/ (a layer README, spec, vocab, shapes, projection or examples), bumping or re-pinning a version IRI, writing a SHACL or SHACL-SPARQL shape, declaring a domain or range, simplifying a model, or naming a new technical term, in LATTICE or an applied ontology built on it.
---

# Authoring LATTICE ontologies

## Changing an ontology document

Follow every step for any change to `ontology/**/spec/`, `ontology/**/vocab/`, or a `shapes/` or
`projection/` directory. Read the
[versioning policy](https://github.com/nebularis/lattice/blob/main/docs/architecture/ontology-versioning-policy.md)
(ADR-A86, ADR-A113) first. A skipped step breaks consumers silently, and has done so before.

1. **Find the source of truth.** A literate layer's `README.md` is its source. Its fenced
   `turtle-spec`, `turtle-vocab` and `turtle-shapes` blocks generate the `.ttl` files, and
   `turtle-example` blocks are illustration only. Edit the README, never the generated file, then
   regenerate:

   ```bash
   python tools/literate_extract.py ontology/<layer>/README.md --layer <layer> --root . --shapes <shape files>
   ```

   - `--shapes` lists one file per `turtle-shapes` block, relative to the layer, in block order.
     For example, Wording takes `shapes/structural.ttl shapes/constraints.ttl`, and Instrument adds
     `shapes/single-expression.ttl`. The layer's README or its test names them.
   - All `turtle-spec` blocks concatenate, in order, into `spec/<layer>.ttl`, and all `turtle-vocab`
     blocks into `vocab/<layer>-vocab.ttl`. The ontology header is itself a block, so a version bump
     is a README edit.
   - A `turtle-spec` block whose **first** line is `# @output-file "spec/<file>.ttl"` goes to that
     file instead, which gains `spec/<layer>.ttl`'s `@prefix` lines (ADR-A120). It states its own
     ontology header. All of a layer's spec documents share one version, bumped together even when
     only one changed. The extractor refuses them otherwise.
   - Add `--check` to compare without writing. Run it **before** relying on a README. If the layer
     already drifts, the README is not yet its source (technical debt TD-16). Compare the extracted
     and committed graphs (`rdflib.compare.graph_diff` over `to_isomorphic` graphs) before
     regenerating, and either restore the README or record the drift. A regeneration over a
     drifting layer can silently discard hand-maintained content.
   - Persistence and the applied modules are not literate. Edit their `.ttl` directly.
2. **Bump the version.** At major version zero an additive change is a MINOR, and a breaking one a
   MINOR marked breaking (ADR-A113). Change the document's `owl:versionIRI`. A `shapes/` or
   `projection/` directory is versioned by its `.version` file, never by the spec's IRI.
3. **Compute the cascade, never trust a count.** A document whose only change is a re-pinned import
   takes the imported change's bump level (ADR-A86). Build the import graph with
   `find_in_scope_ttl_files` and `extract_version_iris` from `tools/ontology_version_check.py`, and
   close it transitively from the changed IRI. MORK's IRIs are `http://`. A document with no version
   of its own still re-pins, with no release.
4. **Re-pin in one pass.** Version IRIs appear in spec and vocab files, literate README blocks,
   `tools/surface/src/surface/namespaces.py`, examples and tests. Replace exact IRIs with one regex
   alternation over the whole old-to-new mapping, so nothing is replaced twice. Tests also build
   IRIs from fragments, such as `LATTICE + "behaviour/0.10.0"`. Move a test that locates the current
   document to the new version, and keep a test that asserts history, a release row or a release
   note. Leave alone `docs/architecture/ontology-releases.md` (generated),
   `tools/test_ontology_releases.py` and `tools/fixtures/import_guard/`.
5. **Regenerate:** `mise run build:ontology-catalog`, then `mise run build:ontology-releases`, which
   adds a row per new version and prints the tags to create. The tags are the human's (skill
   `lattice-lifecycle`).
6. **Record the release** in the "Release notes" section of every README that has one, re-pins
   included.
7. **Check:** `mise run check:ontology-catalog`, `check:ontology-versioning`, `check:import-guard`,
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
  simplification breaks, and discuss it with the human if one exists.
- **An accepted ADR wins.** A simplification contradicting one is a new decision.

## SHACL-SPARQL shapes

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
- **To probe that a test catches a broken shape, break a triple pattern**, never `FILTER (false)`,
  which pySHACL reports for every focus node.
- **Test every cardinality rule at zero**, not only at too many.
- **pySHACL drops a node shape's message reached through `sh:node`.** Put the message on the
  property shape that uses it.
