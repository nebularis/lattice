<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Triple-store discovery

The project's record of how each triple store behaves lives in the Вивід domain `triple-stores`, in [findings.md](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md) at tag `v0.1.0`, with the query-writing rules RDF-1 to RDF-30 in [query-standards.md](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/query-standards.md) and [query-rules.md](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/query-rules.md) at the same tag, and this page says what each finding means for LATTICE, keyed to the domain's identifiers ([ADR-A152](decisions/ADR-A152-vyvid-adoption.md) decision 7). The identifiers TSD-nn and the standards STD-026 to STD-054 and STD-279 LATTICE's documents cite resolve to the domain by the moves `vyvid.toml` declares.

To read one, `mise run graph:ask -- read TSD-nn` prints a finding, and `mise run graph:ask -- find <the behaviour> --kind discovery` finds the ones that touch a behaviour. A new finding is recorded in the domain, skill `lattice-probing`, never here. The index reads the domain's clone as it stands, which may be ahead of `v0.1.0`, so `read` can show a finding's newer text than the tagged file this page links, until the binding pins the domain to a tag (TD-148).

## The findings

### TSD-01. The order in which a `DELETE`/`INSERT`/`WHERE` is applied

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-01-the-order-in-which-a-deleteinsertwhere-is-applied).

**What it means for LATTICE.**

- **R0, the replace as shipped, stays right on both.** It puts the whole payload in the `INSERT` template, so every solution adds every payload triple again, and the last solution restores anything an earlier one removed. Its redundancy is what makes it correct here, and that redundancy is what TSD-02 measures.
- **R2, the linear form, is unsafe on rdflib 7.6.0 and Oxigraph 0.5.11.** The sketch's §4.3 expected it to be safe where `snapshotUpdateSemantics` holds, and neither has it. H5's capability record carries `snapshotUpdateSemantics = false` for both, and `true` for Oxigraph 0.5.12. Since rdflib still lacks it, and an adopter may run an older Oxigraph, R2 stays unused.
- **Any generated update must be right whatever the solution order.** On rdflib a wrong assumption would not fail reliably, it would fail in some processes. A test of order-dependent behaviour on rdflib must fix the hash seed or sweep it.
- **The P1 test was corrected** on 2026-10-13 (`test_store_probes.py`, H2.4b-T1 and T2). On rdflib it runs the probe in child processes under seeds 0 to 11 and requires both outcomes to occur. On Oxigraph it keeps the row-order expectations up to 0.5.11 and expects the triple kept in both orders from 0.5.12, reading `SNAPSHOT_UPDATES` from `lattice_testing_oxigraph` (changed 2026-10-20). A machine that cannot install 0.5.12 still passes. `test_ox_t6` in `tools/testing/oxigraph` holds the flag to the installed version's behaviour, so a later release that changes it again fails there.

Rests on it: PAT-21, STD-174, STD-213.

### TSD-02. What filling a template once per solution costs

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-02-what-filling-a-template-once-per-solution-costs).

**What it means for LATTICE.**

- R0 is correct and quadratic on both, in time on rdflib and in time and memory on Oxigraph (TD-42).
- R2 is unsafe on both (TSD-01). R1, two operations in one request, is safe only where a failing request rolls back (TSD-06), which Oxigraph does and rdflib does not. So no single linear form fits both, which is what the capability record exists to decide. H5 chooses.
- The benchmark fails on a wrong result and never on time or memory (ADR-A124). A run that does not finish is recorded with its exit status.

Nothing in the registers rests on it.

### TSD-03. What a `BIND` inside an inner group can see

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-03-what-a-bind-inside-an-inner-group-can-see).

**What it means for LATTICE.** The checker's scope starts empty in a nested group, an `OPTIONAL`, a `UNION` branch and a `GRAPH` block, and starts from the enclosing scope only in `NOT EXISTS` (FMH-2.1, F4, and FMH-2.3). Tests H2.1-T29 and T29b check the rule against rdflib.

Nothing in the registers rests on it.

### TSD-04. A graph variable bound outside an inner group

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-04-a-graph-variable-bound-outside-an-inner-group).

**What it means for LATTICE.** The scope rule accepts a `GRAPH ?g` inside an inner group when an enclosing group binds `?g` in every solution before it (ADR-A123, second addendum). A caller-named graph, `GRAPH $g`, is available as an override for a store that does scan (H2.3-Q2 (c)). FMH-2.4b's T4 fails if either store starts to scan.

Nothing in the registers rests on it.

### TSD-05. A template quad whose graph variable is unbound

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-05-a-template-quad-whose-graph-variable-is-unbound).

**What it means for LATTICE.** With the parameter guards on, a missing `$root` is refused before this point. With `--no-parameter-guards`, on rdflib, a missing `$root` leaves an orphan graph that no audit names (TD-44). The README's guards paragraph says so.

Nothing in the registers rests on it.

### TSD-06. A request whose second operation fails, and graph management

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-06-a-request-whose-second-operation-fails-and-graph-management).

**What it means for LATTICE.** R1 is a candidate on Oxigraph and not on rdflib. This is only the failure half of `atomicUpdateRequest`. Its isolation half, what a concurrent writer sees between the two operations, needs concurrent writers and is H5's.

Nothing in the registers rests on it.

### TSD-07. Numeric datatypes are not kept by Oxigraph

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-07-numeric-datatypes-are-not-kept-by-oxigraph).

**What it means for LATTICE.** The guard's first datatype test, `DATATYPE($p) = xsd:long`, could never pass on Oxigraph, so every guarded write there wrote nothing (TD-45, FMH-2.4b decision 1). Guard D replaced it in FMH-2.5 with `DATATYPE($p) = DATATYPE("0"^^xsd:long)` (ADR-A123, addendum of 2026-10-13), which compares the parameter with what the store makes of a constant. Probe P5 now asserts that a constant, a substituted parameter, a `VALUES` row and a stored value report one datatype on each store (`test_h2_5_t1_p5_a_long_has_one_datatype_in_every_form_on_each_engine_so_guard_d_can_pass`), and that a simple literal stays `xsd:string` in every form. Because every number on Oxigraph is an `xsd:integer`, requests and stored rows match each other, so the hazard the test guards against cannot arise there. What stays is that the profile's `xsd:long` pinning cannot be checked on Oxigraph.

Nothing in the registers rests on it.

### TSD-08. A zero-length path from a term that is in no triple

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-08-a-zero-length-path-from-a-term-that-is-in-no-triple).

**What it means for LATTICE.** Nothing changes for the sweep, since `?s ?p ?o` must also match and a term in no triple has none. FMH-2.8's `payload-check` query starts a path at `$root` over the payload alone, so it must not depend on which reading a store takes. Its tests run on both.

Nothing in the registers rests on it.

### TSD-09. Unicode escapes and an escaped backslash

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-09-unicode-escapes-and-an-escaped-backslash).

**What it means for LATTICE.** `Literal.encode` now writes the `u` of such a pair, and the hex digits after it, as escapes themselves, so neither reading changes the value (FMH-2.1 decision 1). The literal is correct on both stores. Any code that writes SPARQL text must assume the stricter rdflib reading.

Nothing in the registers rests on it.

### TSD-10. A result row whose projected variables are all unbound

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-10-a-result-row-whose-projected-variables-are-all-unbound).

**What it means for LATTICE.** A test that counts rows on rdflib must project at least one variable it knows is bound. T29 selects `?a ?b` for that reason.

Rests on it: STD-175.

### TSD-11. `BOUND` and text substitution

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-11-bound-and-text-substitution).

**What it means for LATTICE.** The guard is a type test per parameter, never `BOUND` (ADR-A123, first addendum). H2.1-T28 and H2.3-T25 run guarded operations after text substitution.

Nothing in the registers rests on it.

### TSD-12. Initial bindings are visible inside inner groups on rdflib

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-12-initial-bindings-are-visible-inside-inner-groups-on-rdflib).

**What it means for LATTICE.** The guard in its own group works for an initial-binding caller on rdflib and for a text-substituting caller anywhere. Another engine's initial-binding API must be probed before it is relied on.

Nothing in the registers rests on it.

### TSD-13. A filter at the top of a group sees what the group's patterns bound

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-13-a-filter-at-the-top-of-a-group-sees-what-the-groups-patterns-bound).

**What it means for LATTICE.** The guard is its own group (ADR-A123 decision 5). It runs once per request, where the top-level form ran once per solution and cost about 60% on a 20,000-triple sweep on rdflib.

Nothing in the registers rests on it.

### TSD-14. Graph management operations on rdflib

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-14-graph-management-operations-on-rdflib).

**What it means for LATTICE.** A probe or a test that needs an operation to fail at run time on rdflib uses `LOAD` of a source that does not exist.

Nothing in the registers rests on it.

### TSD-15. A sub-select and the variables around it

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-15-a-sub-select-and-the-variables-around-it).

**What it means for LATTICE.** A sub-select that reuses an outer variable's name without projecting it gives different results on the two stores. The `SubSelectLeak` rule makes that a refusal, so no operation the IR builds can depend on it. A sub-select inside a `GRAPH` block reads that graph on both, so the checker passes the enclosing graph to its patterns. Tests `test_h2_5_t12` and `test_h2_5_t13`.

Nothing in the registers rests on it.

### TSD-16. `MIN` and `MAX` over IRIs

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-16-min-and-max-over-iris).

**What it means for LATTICE.** The first port of merge-rewrite equalled its template, so on rdflib it wrote a plain literal as the link's object, and because an IRI is never equal to a literal, `?other != ?canonical` also held for the canonical owner, which got a link to itself. On Oxigraph it wrote IRIs and no self-link. Decided 2026-10-13 (FMH-2.5, decision 1): the template and the builder project `IRI(MIN(STR(?owner)))`, which gives an IRI on both (`test_h2_5_t30`). The `MIN` itself is still different on the two stores and `test_h2_5_t41` keeps the probe.

Nothing in the registers rests on it.

### TSD-17. A chain of additions and subtractions

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-17-a-chain-of-additions-and-subtractions).

**What it means for LATTICE.** The gap scan's template, written as a chain, counted wrongly on Oxigraph. The renderer therefore always writes the parentheses of a nested arithmetic operand, and the template now says `(?S - ?L) + 1` (FMH-2.5, decision 2), both correct on either store. Test `test_h2_5_t44`, and the harness mutation `test_h2_5_t47`, which fails a builder that groups the sum from the right. The parentheses stay, since an adopter may run 0.5.11. Since 2026-10-20 `test_h2_5_t44` expects the grouping of the installed version, reading `LEFT_GROUPED_ARITHMETIC` from `lattice_testing_oxigraph`, and `test_ox_t6` holds the flag to the installed version's behaviour.

Nothing in the registers rests on it.

### TSD-18. `COUNT(DISTINCT)` over `xsd:long` and `xsd:integer` terms

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-18-countdistinct-over-xsdlong-and-xsdinteger-terms).

**What it means for LATTICE.** The gap scan counts distinct `seq` terms. A receipt whose `seq` was written with another integer type adds a term on rdflib and none on Oxigraph, so a duplicate `seq` written that way is reported on rdflib only (`test_h2_5_t43`). Comparisons with `>=` and `<=` work across numeric types on both. The profile pins positions to `xsd:long`, so this arises only from data written outside the generated operations.

Nothing in the registers rests on it.

### TSD-19. The order of `GROUP_CONCAT`

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-19-the-order-of-group_concat).

**What it means for LATTICE.** The order is the store's scan order and no guarantee. A different query shape or store could differ, so the audit tests compare owners as a set. Test `test_h2_5_t45`.

Rests on it: PRI-58.

### TSD-20. A `FILTER` inside `NOT EXISTS` and a parameter

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-20-a-filter-inside-not-exists-and-a-parameter).

**What it means for LATTICE.** `key-claim-write` and merge-rewrite rely on this, and it holds on both stores for both ways of binding. Test `test_h2_5_t14`.

Nothing in the registers rests on it.

### TSD-21. An empty `VALUES` block in an update

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-21-an-empty-values-block-in-an-update).

**What it means for LATTICE.** An append with an empty `eventRows` slot writes nothing on either store, and on rdflib it raises. FMH-2.8's caller check refuses an empty slot before sending, so the generated operation never meets the difference. Test `test_h2_6b_t6`.

Nothing in the registers rests on it.

### TSD-22. rdflib parses and translates a query's text on every call

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-22-rdflib-parses-and-translates-a-querys-text-on-every-call).

**What it means for LATTICE.** Parsing and translating is most of what a SHACL-SPARQL validation costs on rdflib (TSD-23 says why it happens so often). `tools/conftest.py` translates each distinct text once while `ValidationCache` runs pySHACL (`_sparql_translated_once`), keyed on the text, the base and the prefixes the text uses without declaring (TSD-24, TSD-30). This is not a property of SPARQL or of SHACL, and a different engine or validator may not have the cost. [Efficient queries and shapes](efficient-queries-and-shapes.md) draws the line.

Rests on it: STD-176.

### TSD-23. pySHACL runs a SPARQL constraint once per focus node

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-23-pyshacl-runs-a-sparql-constraint-once-per-focus-node).

**What it means for LATTICE.** The cost of a node shape is the number of its focus nodes times the cost of one run, and a shape that targets a common class has one focus node per instance of that class in the data. Exposure's documentation rule targeted `skos:Concept` and ran 15,713 times over 21 validations. Whether Jena SHACL or another validator also runs once per node is not tested (TSD-Q14).

Nothing in the registers rests on it.

### TSD-24. The PREFIX block pySHACL writes changes order between validations

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-24-the-prefix-block-pyshacl-writes-changes-order-between-validations).

**What it means for LATTICE.** Text is not a stable cache key. `_canonical_query` in `tools/conftest.py` sorts the leading declarations before keying, and leaves a text alone that declares a prefix twice, since the later declaration may be the one that applies.

Rests on it: PRI-58.

### TSD-25. rdflib fixes the order of a group's patterns before it knows the initial bindings

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-25-rdflib-fixes-the-order-of-a-groups-patterns-before-it-knows-the-initial-bindings).

**What it means for LATTICE.** Rule R1 of [efficient-queries-and-shapes.md](efficient-queries-and-shapes.md). Three shapes changed: peril 0.3.1 (two queries, 2.0 s and 2.3 s down to 0.11 s and 0.13 s over 405 focus nodes), exposure 0.1.1 (the documentation rule, 1.4 ms to 0.19 ms) and wording 0.4.1 (TSD-26, TSD-27). The benefit is specific to rdflib. The rewrite is harmless elsewhere, since it means the same, but on an optimising engine it buys nothing we measured.

Nothing in the registers rests on it.

### TSD-26. A chain of three or more groups is joined by evaluating the later ones whole

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-26-a-chain-of-three-or-more-groups-is-joined-by-evaluating-the-later-ones-whole).

**What it means for LATTICE.** Rule R2: keep a group to two operands, or put the dependent operand in `FILTER EXISTS`, where the substituted solution reaches it. TSD-Q1 asks about the order of a lazy join's solutions, which this finding does not answer.

Nothing in the registers rests on it.

### TSD-27. A `FILTER` is applied after its group's patterns, and rdflib does not move it earlier

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-27-a-filter-is-applied-after-its-groups-patterns-and-rdflib-does-not-move-it-earlier).

**What it means for LATTICE.** Rule R3. The sub-group is exactly equivalent when the guards read only variables the sub-group binds, so the change is safe to make and to check by replay.

Nothing in the registers rests on it.

### TSD-28. Presence and absence tests: the forms differ little

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-28-presence-and-absence-tests-the-forms-differ-little).

**What it means for LATTICE.** These are worth taking when a query is being rewritten for another reason, and not worth a shapes release alone. We reverted the instrument change for that reason. Choose by clarity.

Nothing in the registers rests on it.

### TSD-29. Two parses of one document never give equal triple sets

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-29-two-parses-of-one-document-never-give-equal-triple-sets).

**What it means for LATTICE.** A cache keyed on triple content cannot hit across parses. Build a fixture once with `graph_cache` and give each test a copy (`tools/test_exposure_ontology.py`, `_fixture`). The copy cost 0.14 s against 0.28 s to parse.

Nothing in the registers rests on it.

### TSD-30. A query's undeclared prefixes resolve from the data graph's bindings

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-30-a-querys-undeclared-prefixes-resolve-from-the-data-graphs-bindings).

**What it means for LATTICE.** A cache key holds the text, the base and the bindings of the undeclared prefixes the text uses (`_sparql_translated_once`). Replaying a recorded validation needs the data graph's bindings restored. Whether Oxigraph has a fallback was not tested.

Nothing in the registers rests on it.

### TSD-31. pySHACL copies the data graph on every validation unless told not to

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-31-pyshacl-copies-the-data-graph-on-every-validation-unless-told-not-to).

**What it means for LATTICE.** A fixed cost per validation that grows with the size of the data, about 9% of a validation in that profile. `inplace=True` would remove it, and pySHACL then may change the graph (inference, rules). Our caches share graphs between tests, and a guard fails the run when one changes (`_graph_cache_not_mutated`), so we did not adopt it (TSD-Q16).

Nothing in the registers rests on it.

### TSD-32. A constant `FILTER` whose value is false is dropped by rdflib

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-32-a-constant-filter-whose-value-is-false-is-dropped-by-rdflib).

**What it means for LATTICE.** Never write a constant false filter to make a probe fail, on any engine, since rdflib ignores it. Break a triple pattern instead. The authoring skill said so for pySHACL (`FILTER (false)` is reported for every focus node), and this is the reason.

Rests on it: STD-132.

### TSD-33. On Oxigraph, `COUNT(*)` over a statically false filter returns no row

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-33-on-oxigraph-count-over-a-statically-false-filter-returns-no-row).

**What it means for LATTICE.** Code that reads the first row of a `COUNT` from `OxigraphStore.select` should expect none (the benchmark's pass criterion never writes such a filter). The mechanism is open (TSD-Q17).

Rests on it: STD-176.

### TSD-34. rdflib evaluates a `FILTER NOT EXISTS` in a `GRAPH` block against the wrong graph for some solutions

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-34-rdflib-evaluates-a-filter-not-exists-in-a-graph-block-against-the-wrong-graph-for-some-solutions).

**What it means for LATTICE.**

- Initial bindings inside a sub-select work on both stores. The account of the fast form of the `members` read that the paid debt TD-68 gave was wrong, and this finding corrects it. The form is still not usable on rdflib.
- **Added 2026-10-20 (FMH-2.8c).** The sub-select form with a `GRAPH` inside each `NOT EXISTS` body is right. It read every version of 24 random histories (checkpoint every 2, 3 and 4 versions, stray adds) as the reference model gives, on rdflib under 16 hash seeds in child processes and on Oxigraph, and the existing histories of `test_membership.py` on both engines with and without guards. It is the `members` read since H2.8c. The read of version 100 of a set of 500 took 1.28 s on rdflib, where the form without a sub-select took 98.6 s, and 0.005 s on Oxigraph, where it took 1.7 s (`benchmark/persistence-membership`).
- The `members` read had no sub-select, and no history we built exposed the defect in it on 192 runs over 16 seeds (FMH-2.6g). Its two `NOT EXISTS` bodies depend on solution variables, so it is the one generated operation where the defect could change an outcome. Since H2.6g each body names its graph, and a sweep holds it to the reference model.
- A fast form of `members` on rdflib should put a `GRAPH` inside each `FILTER [NOT] EXISTS` body, which the audits (`key-claim-quarantine`, `key-claim-merge-rewrite`) already do, or avoid a sub-select beside a `UNION` in one `GRAPH` block, and be tested on a sweep of hash seeds against the reference model of `test_membership.py`.
- Which generated operations had the shape, and what it could change (H2.6g, TSD-Q19), is in the next subsection. Every builder now states a `GRAPH` inside such a body, and the IR checker refuses a `NOT EXISTS` inside a `GRAPH` block whose body has none (`NotExistsWithoutGraph`).
- A test of a `FILTER [NOT] EXISTS` inside `GRAPH` on rdflib must sweep seeds in child processes, as the probe for this finding does. One run in the test process measures luck.
- The probe is `test_tsd_34_*` in `tools/persistence/tests/test_store_probes.py`. It asserts the defect on rdflib, so a fix in rdflib fails it and this entry is then updated.

Nothing in the registers rests on it.

### TSD-35. A literal as the graph of a `GRAPH` block is refused by Oxigraph and parsed by rdflib

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-35-a-literal-as-the-graph-of-a-graph-block-is-refused-by-oxigraph-and-parsed-by-rdflib).

**What it means for LATTICE.** A guarded write that is given a literal for a graph writes nothing on both stores, by different routes, so the outcome a test asserts is the same. A test that expects the request to be accepted and do nothing holds on rdflib only, and is a conformance test. The caller check refuses a literal for a graph parameter before the store sees it.

Rests on it: STD-023.

### TSD-36. A bound object does not give the seek a bound subject gives

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-36-a-bound-object-does-not-give-the-seek-a-bound-subject-gives).

**What it means for LATTICE.** [Efficient queries and shapes](efficient-queries-and-shapes.md) R8 asks that every pattern start from a bound term. This refines it. A bound term in the object position is not equivalent to a bound subject, and a query that looks fully constrained can still scan. Where a row's identity is computable, addressing it by a derived IRI is a different order of cost from searching for it by its properties, and Persistence already has the strategy for exactly that, `dal:PositionDerivedEvent`, an IRI minted from the target and the position. The ledger's checkpoints are position-derived in this sense, since a closing recurrence fixes the positions at which they exist.

Rests on it: PAT-03, PAT-14.

### TSD-37. Oxigraph refuses an IRI with two fragment separators and rdflib accepts it

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-37-oxigraph-refuses-an-iri-with-two-fragment-separators-and-rdflib-accepts-it).

**What it means for LATTICE.** A document that only ever passes through rdflib can hold IRIs that no strict parser accepts, and the defect surfaces at the first strict consumer rather than at authoring time. Anything that loads the corpus into Oxigraph, or hands it to a consumer's own store, has to treat a parse failure per document as expected and report which document failed, rather than loading the corpus as one batch. The fixture itself is referenced by no tool, test or document, so whether it is live input or an orphan is a question for its owner rather than a finding here.

Rests on it: STD-023.

### TSD-38. Oxigraph's read-only open costs a fraction of a read-write open, and a query over the whole corpus is sub-millisecond

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-38-oxigraphs-read-only-open-costs-a-fraction-of-a-read-write-open-and-a-query-over-the-whole-corpus-is-sub-millisecond).

**What it means for LATTICE.** A caller that only reads opens read-only, which is both roughly six times faster and the mode that cannot write by accident. At this corpus size the query is not the cost and the open is, so a long-running server process to amortise loading buys little: 50 ms per call means twenty calls cost one second, against which a server has to be supervised, has a lifecycle to get wrong, and cannot be relied on where a process may not persist. Measure again before assuming this holds at ten times the quads, since the open is a fixed cost and the queries are not.

Rests on it: STD-004.

### TSD-39. One Oxigraph bulk load per document fragments the store past a default open-file limit

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-39-one-oxigraph-bulk-load-per-document-fragments-the-store-past-a-default-open-file-limit).

**What it means for LATTICE.** Load many documents in one bulk write, isolating a bad document by parsing it on its own first rather than by giving it a bulk load of its own (TSD-37). And test a tool that opens many files at the default limit, not only in an agent's shell: this one passed where the limit was 1,048,576 and failed in the maintainer's terminal, which had 256.

Nothing in the registers rests on it.

### TSD-40. A zero-or-more property path's cost changed between Oxigraph 0.5.11 and 0.5.13

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-40-a-zero-or-more-property-paths-cost-changed-between-oxigraph-0511-and-0513).

**What it means for LATTICE.** A cost measured for a property path is a cost for one patch version, not for the engine. The project's floor is now `pyoxigraph>=0.5.13` (`tools/testing/oxigraph`), raised from `>=0.5.11` for this reason, so a figure quoted from the ledger benchmark is reproducible. Where a fold's cost matters, enumerating the accounts is the stable choice, since it measured the same on both versions, and a subtree whose members are known to the caller can be enumerated. This is a sharper case of STD-176 than the standard states: a cost is a hypothesis across patch versions of one engine, not only across engines.

Nothing in the registers rests on it.

### TSD-41. An aggregate over an expression that errors on one row of a group is unbound on Oxigraph and skips the row on rdflib

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-41-an-aggregate-over-an-expression-that-errors-on-one-row-of-a-group-is-unbound-on-oxigraph-and-skips-the-row-on-rdflib).

**What it means for LATTICE.** - An aggregate whose argument can be unbound or error on some row of its group must not be written bare. Coalesce it, or make its rows never error (STD-279). The other aggregates in `tools/mork_compilers` already do (`SUM(IF(COALESCE(?outcome, "") = ...))`, `MAX(COALESCE(STR(?reason), ''))`), and `COUNT(DISTINCT ?condition)` and `SAMPLE` are safe on both. The profile query's `GROUP_CONCAT` was the one that did not. - The profile query now builds `?closures` from one coalesced `SUM` flag per distinct closure its conditions name, in IRI order, with no `GROUP_CONCAT`. Both engines return the same strings. A `GROUP_CONCAT(DISTINCT COALESCE(STR(?x), ""))` also agrees but puts the empty element at either end by the group's order, which differs between engines, and needs a trim. - `check:mork-compilers` and `check:mork-compilers-conformance` both pass. `check:mork-compilers` keeps rdflib as its default engine until the maintainer decides under STD-274. Tests `PU-01` to `PU-09` in `test_profile_union.py` pin the probes of each engine and the generated query on both. - rdflib's leniency is the one the persistence suite never meets, since its generated SPARQL runs on Oxigraph by default. A query written to run on rdflib may rely on it without knowing. The conformance task is what shows it (STD-054). - A possible upstream report, not filed: Oxigraph's `COUNT(expr)` over an erroring expression returns an unbound value where §18.5.1.2 says to count the rest. Jena ARQ 5.1.0 counts the rest (TSD-43). - TSD-43 works through every aggregate and four remedies, and shows the coalesce this entry first recommended changes the meaning of `SUM` and `AVG`. STD-279 is under review for that reason.

Rests on it: STD-274.

### TSD-42. Oxigraph reads every graph for a `GRAPH ?g` whose `?g` is bound outside, a computed name on every version and a constant one inside an `OPTIONAL` from 0.5.13

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-42-oxigraph-reads-every-graph-for-a-graph-g-whose-g-is-bound-outside-a-computed-name-on-every-version-and-a-constant-one-inside-an-optional-from-0513).

**What it means for LATTICE.**

- **TSD-04's Oxigraph half was true of a constant `?g` only, and the probe tested that form.** The compiler computes `?g` from `$root`, so TSD-04 never held for generated queries on Oxigraph, and FMH-2.4b's T4 (a pass on 0.5.11) measured a form the compiler does not emit. The scope rule of H2.3-Q2 and ADR-A123 is unaffected, since the result is right. The cost note of H2.3-Q2 ("Oxigraph passes the binding in") is wrong for Oxigraph.
- **On Oxigraph, every named-graph replace and tombstone under the default `graph_names="query"` costs time in the size of the whole dataset,** whatever the version: 6 ms at 10,000 quads in other graphs, 65 to 90 ms at 100,000, 0.7 s at 1,000,000. `_named_where` builds the sweep for both, in `builders.py`. `graph_names="caller"` is flat at about 1 ms at every size. The composite family, which names its data graph by a bound constant, and the gap scan, whose `VALUES` sits in the same group, are not affected. The other generated forms were not run.
- **The cost of the computed form is a property of the store, and four engines have been measured.** Oxigraph scans, and rdflib, Jena and RDF4J do not, so the computed form is portable in cost across the stores measured except Oxigraph, and not across all stores. The caller-named form was no slower than the computed form on any of them, within the spread of a run (step 3 and step 4), so it bounds the cost from below. Jena on disk, Fuseki over HTTP, RDF4J's `NativeStore`, GraphDB, Virtuoso and Neptune were not measured (TSD-Q25).
- **Choosing a default, changing the sweep's form, or declining to care at a given dataset size is a design decision for the maintainer** (PDD-17).
- FMH-2.4b's T4 and T4b, which asserted these ratios in `check:persistence`, are benchmarks now (STD-290): `benchmark/persistence-store-probes` and `benchmark/persistence-graph-naming-cost` print the ratio per form, engine and version and fail only on a wrong count. `CONSTANT_GRAPH_INLINED_IN_OPTIONAL` in `tools/testing/oxigraph` holds the version change to the behaviour (`test_ox_t6`).
- **The constant form's departure is reported** as [oxigraph/oxigraph#2008](https://github.com/oxigraph/oxigraph/issues/2008), with its tracker search and reproduction in [the upstream reports note](../developer/notes/upstream-sparql-engine-reports.md). The computed form, which no Oxigraph version passes in, is not yet in that report (TSD-Q24).
- A release that restores the constant form shows as a ratio near 1 in both benchmarks (TSD-Q22). A cost is a hypothesis across patch versions of one engine (TSD-40, STD-176).

Rests on it: STD-290.

### TSD-43. What an aggregate does with a row that has no value or errors, for every aggregate, and what each remedy does

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-43-what-an-aggregate-does-with-a-row-that-has-no-value-or-errors-for-every-aggregate-and-what-each-remedy-does).

**What it means for LATTICE.** - No single rule fits every aggregate. A row with no value can mean "not a member of the group" (filter), "contributes the neutral element" (coalesce), or "the answer is unknown" (detect and propagate), and each aggregate has the choices the table shows. STD-279 and R9 say to coalesce, which is the second only. A proposed replacement is in the Validation Pack for CCS-9b.3, not ratified. - A coalesce is correct only where the aggregate has a neutral element and the meaning is that absence contributes nothing. `SUM` over weights where a missing weight must be reported Undetermined is not that case, and neither is `AVG` where the denominator should be the rows that have a value. - `FILTER(BOUND(?x))` removes a group as well as a row. Where a group with no value must appear, the filter belongs inside the `OPTIONAL` and then leaves the variable unbound again, or a coalesce or a detect is the form. - `COUNT(?x)` over a bare variable and `COUNT(*)` agree on all three engines and are the safe pair for detection. `COUNT(expr)` is not portable, since each engine differs from the others (rdflib counts the row, Oxigraph is unbound, Jena removes the row, which §18.5.1.2 asks for). - A grouped query over no rows returns a row on rdflib and none elsewhere, so a consumer of generated SPARQL must not depend on it (candidate for TSD-Q23). - `SUM` over a term that is not a number raises on rdflib and is unbound elsewhere, so a type guard (`isNumeric`) belongs in any `SUM` or `AVG` over data not validated. - Audit of `tools/mork_compilers` and `tools/persistence` against this table is in the Validation Pack.

Nothing in the registers rests on it.

### TSD-44. A small update on Fuseki TDB2 costs its commit, so batching updates is the lever for write throughput

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-44-a-small-update-on-fuseki-tdb2-costs-its-commit-so-batching-updates-is-the-lever-for-write-throughput).

**What it means for LATTICE.** On TDB2, write throughput is about 15 transactions a second, however many writers send them. A writer that merges the updates waiting for it into one request multiplies that by the batch size, so batching, not more writers, is the lever. A batch shares one transaction, so it commits or fails as one.

Nothing in the registers rests on it.

### TSD-45. Oxigraph passes a constant graph variable into an `OPTIONAL` before 0.5.13, and a computed one never

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-45-oxigraph-passes-a-constant-graph-variable-into-an-optional-before-0513-and-a-computed-one-never).

Nothing in the registers rests on it.

### TSD-48. RDF4J counts 0 for `COUNT(*)` over a pattern with no variable that matches

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-48-rdf4j-counts-0-for-count-over-a-pattern-with-no-variable-that-matches).

**What it means for LATTICE.** A test or check that counts over a pattern with no variable cannot tell a match from a miss on RDF4J. Bind a variable and filter on it, as `benchmark/persistence-graph-naming-cost` now does, or use `ASK`. No generated operation counts this way, and the benchmark's checks were the only place it was found.

Nothing in the registers rests on it.

### TSD-50. On Jena ARQ in memory a failed request is rolled back, and CLEAR GRAPH of an absent graph fails where DROP GRAPH does not

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-50-on-jena-arq-in-memory-a-failed-request-is-rolled-back-and-clear-graph-of-an-absent-graph-fails-where-drop-graph-does-not).

**What it means for LATTICE.** The two-operation replace (R1) is atomic on Jena in memory, as on Oxigraph and unlike rdflib. No generated operation in `tools/persistence/src` emits `CLEAR` or `DROP`. A hand-written update that clears a graph it may not have written to should say `SILENT`, which all three engines accept. Probe P2 expects `DROP GRAPH <urn:absent>` to succeed and `CLEAR GRAPH <urn:absent>` and `LOAD <urn:no-such>` to fail and roll back on Jena (`test_h2_4b_t3`), so a fix upstream shows as a failure there. Whether TDB2 does the same is TSD-Q13.

Nothing in the registers rests on it.

### TSD-51. Jena ARQ matches a zero-length path from a term in no triple with the term itself

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-51-jena-arq-matches-a-zero-length-path-from-a-term-in-no-triple-with-the-term-itself).

**What it means for LATTICE.** Two of three engines match the term, which supports TSD-08's reading and leaves Oxigraph as the outlier, though TSD-Q3 is still unanswered from the specification's text. The sweep is unaffected (TSD-08). `test_h2_4a_t6` expects the term on rdflib and Jena and nothing on Oxigraph.

Nothing in the registers rests on it.

### TSD-52. Jena ARQ keeps xsd:long, counts distinct terms, groups arithmetic from the left and divides integers into a decimal

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-52-jena-arq-keeps-xsdlong-counts-distinct-terms-groups-arithmetic-from-the-left-and-divides-integers-into-a-decimal).

**What it means for LATTICE.** The profile's `xsd:long` pinning can be checked on Jena, which Oxigraph cannot do (TSD-07). A receipt whose `seq` was written as `xsd:integer` adds a distinct term on Jena and is reported by the gap scan, as on rdflib (`test_h2_5_t43`). Guard D passes a well typed `xsd:long` epoch and refuses an `xsd:integer` one on Jena, as on rdflib (`test_h2_5_t4`). None of this departs from the specification. Oxigraph's canonicalisation is the departure, recorded in TSD-07.

Nothing in the registers rests on it.

### TSD-53. Jena ARQ applies a DELETE/INSERT in the specification's order, skips an unbound template graph and tests the right graph in TSD-34's form

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-53-jena-arq-applies-a-deleteinsert-in-the-specifications-order-skips-an-unbound-template-graph-and-tests-the-right-graph-in-tsd-34s-form).

**What it means for LATTICE.** The generated named-graph operations rely on none of the three departures that rdflib shows, and Jena agrees with Oxigraph on them. `test_h2_4b_t1`, `t2`, `t5` and `test_tsd_34_...` hold the Jena expectation beside the other two.

Nothing in the registers rests on it.

### TSD-54. A blank node label loaded twice is one node on rdflib and Jena with labels kept, and two on Oxigraph

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-54-a-blank-node-label-loaded-twice-is-one-node-on-rdflib-and-jena-with-labels-kept-and-two-on-oxigraph).

**What it means for LATTICE.** A test that adds quads in several calls and refers to a blank node by label gets one node on rdflib and two on Oxigraph, so it must not rely on either. `platform/sparql-testkit` passes `createUseLabelEncoded()` for every load, so a label means the same node across loads, as in rdflib. The testkit's blank node behaviour is therefore a choice and not Jena's default. TSD-29 holds on every engine for a parse that is meant to be independent. Test `MSC5-09`.

Nothing in the registers rests on it.

### TSD-55. rdflib's n3 writes a multi-line literal in triple quotes, which N-Quads refuses

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-55-rdflibs-n3-writes-a-multi-line-literal-in-triple-quotes-which-n-quads-refuses).

**What it means for LATTICE.** `n3()` is a Notation3 writer and not an N-Quads one, so nothing here departs from a specification. Code that builds N-Quads from rdflib terms must escape a literal itself or serialise with the `nt` writer. `lattice_testing_jena` does the first (`_nquads`). Test `MSC5-10`.

Nothing in the registers rests on it.

### TSD-56. Jena ARQ evaluates a sub-select on its own and orders IRIs as IRIs

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-56-jena-arq-evaluates-a-sub-select-on-its-own-and-orders-iris-as-iris).

**What it means for LATTICE.** Jena agrees with Oxigraph and with the specification where rdflib departs, so the `SubSelectLeak` rule and the `IRI(MIN(STR(?owner)))` workaround stay needed for rdflib only, and cost nothing on Jena. Tests `MSC5-01` to `MSC5-06`. Whether Fuseki differs from in-process ARQ is TSD-Q12's remainder.

Nothing in the registers rests on it.

### TSD-57. Jena ARQ shows none of the growth that TSD-25 to TSD-27 record on rdflib

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-57-jena-arq-shows-none-of-the-growth-that-tsd-25-to-tsd-27-record-on-rdflib).

**What it means for LATTICE.** In-process ARQ does not show TSD-25 to TSD-27's sensitivity. The one difference is E2, where Jena's naive form is 2 to 3 times the improved one at every size, a constant factor and not growth. ADR-A128's rules on the order of a group's patterns and the place of a filter stay about rdflib, as that document already says. Jena's absolute times are dominated by the pipe, so the ratios are the evidence and not the milliseconds. The measure is for ARQ over an in-memory dataset. Whether Fuseki over TDB2 differs is TSD-Q18's remainder. A cost is a hypothesis across engines (STD-176).

Nothing in the registers rests on it.

### TSD-60. An aggregate over IF of an unbound variable raises on rdflib and is unbound on Oxigraph and Jena

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-60-an-aggregate-over-if-of-an-unbound-variable-raises-on-rdflib-and-is-unbound-on-oxigraph-and-jena).

**What it means for LATTICE.** Oxigraph and Jena agree in every cell, so the dependence on `?decision` is a property of the generated query and not of one engine. On rdflib a malformed value would crash the profile query where the other two engines return an unbound count. `COALESCE(?decision, "")` gives `1` on all three engines for the arithmetic error, which makes the row count as none of the outcomes. Whether that is the intended meaning is a design decision for CCS slice C9b3b, and the generated query is not changed here.

Nothing in the registers rests on it.

### TSD-61. rdflib orders a string against a number where the specification gives a type error

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-61-rdflib-orders-a-string-against-a-number-where-the-specification-gives-a-type-error).

**What it means for LATTICE.** A test such as a containment check `?candLower >= 5` decides on rdflib where a candidate value is a string, and drops the row on Oxigraph and Jena. This is the divergence the CCS-9b.3 aggregate-errors audit saw in item 4 and attributed to the aggregate. It is the comparison. A generated query that orders a value of unchecked type guards it with `isNumeric` (rule R9, option 1).

Nothing in the registers rests on it.

### TSD-62. Fuseki on TDB2 applies concurrent updates one at a time, and a read does not wait for them

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-62-fuseki-on-tdb2-applies-concurrent-updates-one-at-a-time-and-a-read-does-not-wait-for-them).

**What it means for LATTICE.** On one TDB2 dataset, more writers do not write faster. They keep a busy workspace from delaying the others in the queue, and they parallelise what a writer does before its update, such as parsing and checking. Write throughput beyond one writer needs a dataset per group of partitions. Reads need no coordination with the writers.

Nothing in the registers rests on it.

### TSD-63. rdflib rewrites an `xsd:dateTime`'s `Z` as `+00:00` when it parses

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-63-rdflib-rewrites-an-xsddatetimes-z-as-0000-when-it-parses).

**What it means for LATTICE.** A check that a graph round-tripped through rdflib is unchanged compares literals by value (Jena's `Node.sameValueAs`), as the studio's writer now does, never by term. An identity, a hash or a canonical form taken over such a literal must fix its lexical form first, or it differs between a graph written by Jena and the same graph after rdflib.

Nothing in the registers rests on it.

### TSD-64. A cast lookup key joins a stored integer by value on both stores, and Oxigraph joins `xsd:long` with `xsd:integer` too

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-64-a-cast-lookup-key-joins-a-stored-integer-by-value-on-both-stores-and-oxigraph-joins-xsdlong-with-xsdinteger-too).

**What it means for LATTICE.** A cast lookup must name the reference data's own datatype in `mork:lookupDatatype`. Oxigraph forgives naming a sibling integer type and rdflib does not, so the rdflib run in the mork_rdf tests is the stricter one. Leading zeros never stop a numeric cast lookup from matching on either store.

Nothing in the registers rests on it.

### TSD-65. A `DELETE`/`INSERT` fills every template quad once per solution on every engine measured, whether or not the quad is then skipped, and only Jena applies a quad with no variable once per operation

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-65-a-deleteinsert-fills-every-template-quad-once-per-solution-on-every-engine-measured-whether-or-not-the-quad-is-then-skipped-and-only-jena-applies-a-quad-with-no-variable-once-per-operation).

**What it means for LATTICE.**

- TD-42's cause is now the same on every engine and named: the payload, or on Jena the patch log's delta, sits in a template that M solutions fill.
- The two linear forms are R1′, which needs the request to be one transaction (TSD-66 for Jena's family, TSD-06 for Oxigraph's failure half), and R2, which needs every deletion applied before any insertion (P1, TSD-53, TSD-66, TSD-01 from Oxigraph 0.5.12). Neither is safe on rdflib or RDF4J, which stay on R0. The choice is the sketch's LR-Q1.
- On Jena alone, R0 with the delta's graphs ground would be linear, but that is Jena's shortcut and not the specification, so it is not a form.

Nothing in the registers rests on it.

### TSD-66. Jena TDB2 and Fuseki over it apply an update as ARQ in memory does, roll back a request whose second operation fails, and apply a request the client abandoned

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-66-jena-tdb2-and-fuseki-over-it-apply-an-update-as-arq-in-memory-does-roll-back-a-request-whose-second-operation-fails-and-apply-a-request-the-client-abandoned).

**What it means for LATTICE.**

- What TSD-53 found for ARQ in memory holds for the studio's store, by source and by observation. A one-operation linear replace that needs P1 and P4 is safe there, and a two-operation one that needs the request to be one transaction is too.
- A client that loses its connection during an update learns nothing from the failure. The update is applied all the same, 22 seconds later at this size, so the caller's obligation to confirm a write by reading its transaction claim, and never from the reply, is what makes the outcome known. That is the caller library's third obligation already.
- A payload with a blank node is written once per solution of the operation that carries it, so the generated replace, whose `WHERE` has one solution per stored triple, would leave M copies of each blank node's structure. The callers refuse a blank node in a payload, which this shows to be a correctness rule and not a convenience.

Nothing in the registers rests on it.

### TSD-67. RDF4J 6.1.0's MemoryStore applies a `DELETE`/`INSERT` one solution at a time, writes a template quad whose graph is unbound, and rolls back a request whose second operation fails

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-67-rdf4j-610s-memorystore-applies-a-deleteinsert-one-solution-at-a-time-writes-a-template-quad-whose-graph-is-unbound-and-rolls-back-a-request-whose-second-operation-fails).

**What it means for LATTICE.** The generated named-graph replace R0 is right on RDF4J, since it relies on neither the order nor the skip, and it is quadratic there as on every per-solution store (TSD-65). A one-operation linear form is not safe on RDF4J. A two-operation form has the failure half of request atomicity, and its isolation half is not probed.

Nothing in the registers rests on it.

### TSD-68. Oxigraph refuses a prologue after the `;` of an update request

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-68-oxigraph-refuses-a-prologue-after-the--of-an-update-request).

Nothing in the registers rests on it.

### TSD-69. Jena keeps no empty named graph from a TriG body

[The finding at v0.1.0](https://github.com/nebularis/vyvid-triple-stores/blob/v0.1.0/findings.md#tsd-69-jena-keeps-no-empty-named-graph-from-a-trig-body).

Nothing in the registers rests on it.

### TSD-70. No store compares an `owl:rational` literal by value

Recorded in the domain on 2026-11-08, after `v0.1.0`, so it has no tagged link yet. `mise run graph:ask -- read TSD-70` prints it from the domain's clone.

**What it means for LATTICE.** Ledger records an exact share as two integers, `ldg:proportionNumerator` and `ldg:proportionDenominator`, rather than one `owl:rational` (LG-Q6, LG-2), since its runtime shapes compare and sum grants and no store compares the literal. LG2-01 in `tools/test_ledger.py` runs the probe on each engine present, so an engine that starts comparing by value fails there.

Nothing in the registers rests on it.

### TSD-71. An `OPTIONAL` join and a `UNION` that stands for it cost differently on each engine

Recorded in the domain on 2026-11-11, after `v0.1.0`, so it has no tagged link yet. `mise run graph:ask -- read TSD-71` prints it from the domain's clone.

**What it means for LATTICE.** A ledger read that counts only the credits an account accepts joins to a credit's kind, an optional property. `benchmark/ledger-credit-kinds/` reads with `OPTIONAL` on rdflib and Jena and with `UNION` on Oxigraph, since each form costs 4 to 6 times the plain read on one engine. The `UNION` form as first written dropped a credit with no kind, which the ledger allows on a path where every account accepts all kinds, and LG-15 corrects and re-measures it (LG-Q10, LG-14, LG-15).

### TSD-72. A running balance clamped at a ceiling is not one SPARQL query, and the ordered read that replaces it

Recorded in the domain on 2026-11-11, after `v0.1.0`. `mise run graph:ask -- read TSD-72` prints it.

**What it means for LATTICE.** Where an account's credit ceiling can bind, its balance is an ordered read folded by the caller, at about the cost of a filtered sum on rdflib and Oxigraph. The ledger's laws apply the ceiling step by step (LD3, the balances sketch §3), so the runtime shapes and reads that check a balance follow this form, and LG-15 records Jena's cost from a native caller.

### TSD-73. Oxigraph on disk does not make concurrent updates wait for each other, so a guarded update loses writes, and Oxigraph in memory does

Recorded in the domain on 2026-11-12, after `v0.1.0`. `mise run graph:ask -- read TSD-73` prints it.

**What it means for LATTICE.** The guarded write of PAT-21 and PAT-04, and the write `dal:Optimistic` generates (MEC-59), close a race only on a store that applies update requests one at a time or refuses the second of two that rewrite one statement. Oxigraph 0.5.13 embedded on disk does neither, so a store description for it declares `dal:providesSingleWriter` only where its adapter sends updates one at a time, and store isolation is verified against the store as configured (PRI-59). One lock around the update call restores the guard. The ledger's write benchmark (LG-17) asserts the guard on the in-memory store and reports the on-disk store. The patterns guide and the concurrency document, which named Oxigraph among the stores that serialise writers, carry a dated note, and TD-162 holds what is left. The behaviour is a trade-off Oxigraph made on purpose in 0.5.0, so it will not go away in a patch release, and a report with a proposed writer lock is drafted in the [upstream reports note](../developer/notes/upstream-sparql-engine-reports.md#oxigraph-on-disk-store-loses-concurrent-updates), not filed.

### TSD-74. Jena in memory and TDB2, called in process, make a second write transaction wait, so a guarded update holds

Recorded in the domain on 2026-11-12, after `v0.1.0`. `mise run graph:ask -- read TSD-74` prints it.

**What it means for LATTICE.** The guarded write of PAT-21 and PAT-04 and the write `dal:Optimistic` generates (MEC-59) hold on Jena in memory and on TDB2 called in process, which is the evidence a store description declaring `dal:providesSingleWriter` for either rests on (PRI-59). The ledger's native write benchmark (LG-17) holds both stores' guarded runs to the replay of their commits. A durable commit on TDB2 costs 84 to 98 ms on a laptop, so a writer that retries after a lost race gains nothing from more threads there, which bears on how many writers a ledger runs and on whether its guard is one revision per owner. A guarded update over HTTP to Fuseki is not probed (TSD-62 has its timing).

