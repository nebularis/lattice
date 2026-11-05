<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: VM-3, the thin layer

**Unit:** [vyvid-migration](../plans/vyvid-migration.md)
**Status record:** [vyvid-migration](../status/vyvid-migration.md)

## Invariant

LATTICE keeps only what Вивід has no notion of, the architectural quanta and the catalogue's units with their folders, as one extractor command `vyd build` runs in the checkout, and its knowledge tests prove the knowledge base consistent against the store `vyd build` writes ([ADR-A152](../../architecture/decisions/ADR-A152-vyvid-adoption.md) decisions 1 and 6). The modules and tests Вивід's own suite already holds are removed only after those tests pass (plan, decision 4), and every removed test is accounted for below.

## Tests

| ID | Given / When / Then | Level | Invariant | Pass | Kind |
|---|---|---|---|---|---|
| test_vm3_01 | this checkout / the extractor run on Вивід's request / every quad in the index graph, protocol 1, no problem, every text a subject it wrote | L4 | the extractor contract | assertions | positive |
| test_vm3_02 | the same / the substrate's data quantum / it includes modules under the IRI Вивід gives a declared unit | L4 | an Owner edge and a quantum's part meet | assertions | positive |
| test_vm3_03 | the same / the units declared / every module by name, every tool package by path and by name where no module shares it, every module kind | L4 | the catalogue is the one source of units | assertions | positive |
| test_vm3_04 | the same / the unit paths declared / every path names a declared unit, a module's folder under its root's, a tool package's folder its own | L4 | a term's owner meets an Owner edge | assertions | positive |
| test_knowledge_base.py, 25 tests | `vyd build` on this checkout / the store read / decisions carry status and pointer, statuses in the closed set, every entry has a claim, a pointer and its scope, standards have a stratum and a check or a reason, enforcement names a capability, evidence targets exist across the index graphs, the facet groups reach their values, every decision file and capability row is a node, every register table is a data table, and the build prints no note or finding but the known ones | L4 | the knowledge base consistent | assertions | positive |
| test_the_release_is_one_data_quantum, test_a_governed_quantum_exists, test_a_terms_owner_meets_the_owner_edge_of_its_module | the store with the extractor run / the quanta and the owners / the substrate is one data quantum, every Governs cell names a quantum, and a foundation term and MEC-01's Owner cell reach one node | L4 | the quanta derived, the owners met | skipped with a reason until `vyd trust`, then assertions | positive |
| test_quanta.py, 7 tests | the rules of a quantum, unchanged | L1 | derived, never declared | assertions | positive |

## What ran, and what it showed

Three passes on 2026-11-05. The first, at v0.2.4 with the binding untrusted, had `mise run check:knowledge` at 34 passed and 2 skipped before the deletions and after, and the slice was marked built on that. That was too early, since the two skipped tests are the ones the extractor feeds. The second, with the binding trusted at trust point 2, failed both. STD-319's Governs cell named `registers`, which is no quantum, and CAP-98's Provided by cell named `tools/owl_profile.py`, which is no unit, with thirteen more notes on Owner cells written with a folder's trailing slash. `main`'s own build had reported CAP-98 the same way, so that row predates this unit. Вивід 0.2.5 reads a Governs cell as an edge, drops the slash and gives a term the unit whose declared folder holds it, and the two rows are corrected here. The third pass, at v0.2.5 trusted, read in full: `mise run check:knowledge` 38 passed and none skipped, `mise run build:knowledge` printing the claim-length notes, the moved-entries note and the extractor's version finding and nothing else, and `mise run check` written unfiltered to a file, exit 0 from `mise` itself in 254 s. Of its 3,449 lines the first 150 were read whole and the rest searched for every result and failure word, which gave knowledge 38, identifiers 1641 mentioned and 0 unresolved, vyvid-binding 8, hooks 45, mork-rdf 103, mork-compilers 195, mork 438, workers 189, ontology-catalog 1239, persistence 4814, reference-eligibility 81, persistence-vectors 94, frontend 118, 65 and 21, all passed, and ontology-versioning's banner for four pending release tags, which are the maintainer's. The Jena `ERROR` lines and the Saxon and broker lines of `check:java` are negative fixtures inside passing tests.

The two full checks of the first pass need an account. The first ran through `grep -v '^\['` and `tail`, so every line `mise` prefixed was dropped, its whole output was `Finished in 92.16s`, and the exit code reported for it was the pipeline's, not `mise`'s. The second, two minutes later, failed `test_every_tool_writes_text_with_an_explicit_encoding_and_newline` on `extractor.py`. The code of that line did not change between them. What changed is that the test scans tracked files and `extractor.py` was untracked until the commit between the two runs, so the first run may well have passed that test, but neither its exit code nor its output says so either way. The fix, af71c406, and the third pass are the evidence.

After the third pass the slice family was added to `vyvid.toml`, which lapsed trust, trust point 3. Untrusted, `vyd find WB-10 --kind slice` and `vyd find VM-3 --kind slice` rank the slice first at 1.00, `vyd find "the quanta and owners extractor" --kind slice` ranks VM-3 first at 0.82, `vyd board --here` lists the board, `mise run check:identifiers` passes at 2107 identifiers mentioned, 466 of them slices, and 0 unresolved, `mise run check:vyvid-binding` has 7 passed and 1 skipped, and `mise run check:knowledge` has 35 passed and 3 skipped.

## One command

```bash
mise run check:knowledge
```

Run from the checkout's root. A pass is every test passing, 38 where the binding is trusted, and 35 with the three quanta and owner tests skipped where it is not, since the extractor is a command and runs only after `vyd trust`.

## Artefacts

`tools/knowledge/extractor.py` with its `units` and `unit_paths`, `tools/knowledge/test_extractor.py`, `tools/knowledge/test_knowledge_base.py`, the `lattice-quanta` entry, the `SL` family and the identifier scan's `skip` of `vyvid.toml`, the fourteen VTB test identifiers excused in `tools/knowledge/identifier-exceptions.txt`, the tasks `check:knowledge`, `check:identifiers` and `bootstrap:knowledge` in `mise.toml` with v0.2.5 pinned, STD-319 and CAP-98 corrected, `tools/knowledge/README.md` rewritten for what stays, CAP-10 to CAP-12 and CAP-81 re-pointed, and the removal of `extract.py`, `ask.py`, `identifiers.py`, `facets.py`, `anchors.py`, `embed.py`, `knowledge.ttl` and their six test modules.

## Not covered here

A pointer at the whole of a long file. Вивід's `read` refuses one, which its suite tests, and the build prints no note for a new one in the corpus, so the old test's baseline is gone and nothing here catches one, reported to Вивід's side. A problem Вивід neither notes nor finds is not caught here either, and its own suite is where that is tested. The board tasks, VM-4.

## The tests removed, each accounted for

The maintainer asked for no loss of function. The six removed modules held 132 tests, 69 of them in `test_extract.py`, of which the subagent's first cut kept 22 and three were restored by hand. Each is accounted for in the table. Kept means the same check runs in `test_knowledge_base.py` or `test_extractor.py`. Notes means the old test checked that the extractor reports a corpus problem, which Вивід now prints as a note or a finding and `test_the_build_reports_nothing_but_the_known_notes` catches. Vyvid means the behaviour is Вивід's own, the tool's `find`, `read` and `exists`, its embeddings, its facet scheme, its identifier scan and its T-Box, and the named test of its suite holds it. Gone means the behaviour no longer exists.

Twelve vyvid rows found no test in Вивід's suite by reading, and are for its side: `exists` reaching a principle by a word of its claim, a TOML table anchor, a related facet value raising entries of another facet, the weak-answer advice to ask again with `--kind term`, the ADR spelling pattern that is now a family of `vyvid.toml`, which `check:identifiers` exercises over every spelling the corpus uses, and six shape checks of the T-Box, which is now Вивід's file. One check the old suite made of the corpus was lost and is recovered here, an unpromoted question past thirty days, which Вивід prints as a finding, so the build-notes test now reads findings as well as notes.

| Removed test | Module | Disposition | Covered by |
|---|---|---|---|
| test_every_decision_file_becomes_a_node | extract | kept | test_knowledge_base.py::test_every_decision_file_becomes_a_node |
| test_a_known_decision_carries_its_claim_status_and_pointer | extract | kept | test_knowledge_base.py::test_a_known_decision_carries_its_claim_status_and_pointer |
| test_no_decision_has_two_statuses | extract | kept | test_knowledge_base.py::test_no_decision_has_two_statuses |
| test_a_decision_with_no_readable_status_is_reported_not_guessed | extract | vyvid | tests/test_index_extract.py::test_a_decision_with_no_readable_status_is_reported_not_guessed |
| test_every_decision_in_the_corpus_states_its_status | extract | notes | Note: no **Status:** header field (extract.py:377), build-notes test |
| test_every_status_used_is_in_the_tbox_closed_set | extract | kept | test_knowledge_base.py::test_every_status_used_is_in_the_tbox_closed_set |
| test_the_term_summary_answers_the_question_the_index_exists_for | extract | kept | test_knowledge_base.py::test_the_term_summary_answers_the_question_the_index_exists_for |
| test_every_tracked_ontology_document_parses_in_the_strict_store | extract | notes | Note: ontology document does not parse (build.py:94), build-notes test |
| test_an_unparseable_document_is_reported_and_loses_only_itself | extract | vyvid | tests/test_index_extract.py::test_an_unparseable_document_is_reported_and_loses_only_itself |
| test_the_registers_contribute_their_rows | extract | gone | row-count floors, node-count and register tests cover the registers |
| test_every_node_has_a_claim_and_a_pointer | extract | kept | test_knowledge_base.py::test_every_node_has_a_claim_and_a_pointer |
| test_every_facet_tag_is_a_value_of_its_scheme | extract | notes | Note: not a taggable value of the X facet (registers.py:214) |
| test_a_group_reaches_every_value_under_it | extract | kept | test_knowledge_base.py::test_a_group_reaches_every_value_under_it |
| test_the_term_summary_holds_only_declared_ontology_terms | extract | kept | test_knowledge_base.py::test_the_term_summary_holds_only_declared_ontology_terms |
| test_an_unknown_column_header_is_reported | extract | notes | Note: column 'X' is neither declared nor on the unmapped list (registers.py:176) |
| test_an_audience_outside_the_set_is_reported_not_stored | extract | notes | Note: Audience 'X', which is not one of (registers.py:214) |
| test_an_owner_that_names_no_catalogue_unit_is_reported_not_minted | extract | notes | build-notes test (owner outside the declared units, no exact phrase found) |
| test_a_capability_is_invoked_and_a_mechanism_is_adopted | extract | kept | test_knowledge_base.py::test_a_capability_is_invoked_and_a_mechanism_is_adopted |
| test_every_capability_row_is_a_capability_node | extract | kept | test_knowledge_base.py::test_every_capability_row_is_a_capability_node |
| test_every_pattern_states_a_cost | extract | kept | test_knowledge_base.py::test_every_pattern_states_a_cost |
| test_every_evidenced_by_target_exists | extract | kept | test_knowledge_base.py::test_every_evidenced_by_target_exists |
| test_exists_reaches_every_register_that_records_what_exists | extract | vyvid | tests/test_ask.py::test_declared_terms_are_searched_only_when_their_kind_is_named (exists on a term only). No Вивід test found for: exists reaching patterns and capabilities by name or claim |
| test_every_index_entry_states_its_scope | extract | kept | test_knowledge_base.py::test_every_index_entry_states_its_scope |
| test_a_principle_is_found_by_a_word_in_its_claim | extract | vyvid | no Вивід test found for: exists finding a principle by a word in its claim |
| test_every_table_in_a_register_is_a_data_table | extract | kept | test_knowledge_base.py::test_every_table_in_a_register_is_a_data_table |
| test_a_range_follows_an_edit | extract | vyvid | tests/test_index_core.py::test_a_section_anchor_resolves_to_its_current_lines |
| test_a_repeated_heading_is_suffixed_as_github_does | extract | vyvid | tests/test_index_core.py::test_a_repeated_heading_is_suffixed_as_github_does |
| test_a_line_number_is_refused_as_a_pointer | extract | vyvid | tests/test_index_core.py::test_a_line_number_is_refused_as_a_pointer |
| test_a_python_definition_resolves_to_its_ast_span | extract | vyvid | tests/test_index_core.py::test_a_python_definition_resolves_to_its_span |
| test_a_toml_table_resolves_to_its_span | extract | vyvid | no Вивід test found for: a TOML table anchor (mise.toml::task) |
| test_the_slug_rule_matches_every_link_the_guides_already_use | extract | notes | Note: Pointer ... no heading (registers.py:200), build-notes test |
| test_every_authored_pointer_resolves_against_the_real_corpus | extract | notes | Note: has Pointer <reason> (registers.py:200) |
| test_read_returns_the_bounded_text_of_a_pointer | extract | vyvid | tests/test_ask.py::test_read_prints_an_entry_with_a_register_row_and_a_pointer |
| test_read_prints_the_register_row_before_what_its_pointer_names | extract | vyvid | tests/test_ask.py::test_read_prints_an_entry_with_a_register_row_and_a_pointer |
| test_an_open_store_question_is_a_discovery_with_its_row | extract | gone | store findings moved to the triple-stores domain, not indexed here |
| test_an_answered_store_question_names_its_finding_and_is_labelled_not_hidden | extract | gone | store findings moved to the triple-stores domain, not indexed here |
| test_a_ratified_cell_is_read_by_its_leading_word | extract | vyvid | tests/test_registers.py::test_a_row_is_read_by_its_columns |
| test_a_query_rebuilds_an_index_older_than_the_files_it_reads | extract | vyvid | tests/test_ask.py::test_a_built_index_is_stale_only_when_a_file_the_stack_reads_is_newer |
| test_every_standard_has_a_stratum | extract | kept | test_knowledge_base.py::test_every_standard_has_a_stratum |
| test_a_standard_refines_only_one_at_its_own_level_or_above | extract | kept | test_knowledge_base.py::test_a_standard_refines_only_one_at_its_own_level_or_above |
| test_enforcement_names_a_capability | extract | kept | test_knowledge_base.py::test_enforcement_names_a_capability |
| test_an_extrapolated_standard_rests_on_something | extract | kept | test_knowledge_base.py::test_an_extrapolated_standard_rests_on_something |
| test_the_enforcement_gap_is_one_query | extract | kept | test_knowledge_base.py::test_the_enforcement_gap_is_one_query |
| test_the_release_is_one_data_quantum | extract | kept | test_knowledge_base.py::test_the_release_is_one_data_quantum |
| test_a_governed_quantum_exists | extract | kept | test_knowledge_base.py::test_a_governed_quantum_exists |
| test_every_architectural_and_design_standard_names_its_check_or_why_it_has_none | extract | kept | test_knowledge_base.py::test_every_architectural_and_design_standard_names_its_check_or_why_it_has_none |
| test_every_enforcing_check_is_classified_as_a_fitness_function | extract | kept | test_knowledge_base.py::test_every_enforcing_check_is_classified_as_a_fitness_function |
| test_the_store_stays_within_a_default_open_file_limit | extract | vyvid | tests/test_index_extract.py::test_the_store_stays_within_a_default_open_file_limit |
| test_a_facet_value_matches_up_and_down_its_chain_but_not_its_siblings | extract | vyvid | tests/test_ask.py::test_a_matching_facet_raises_an_entry_and_a_mismatch_hides_none (boost only). No Вивід test found for: facet chain up and down and siblings excluded |
| test_a_related_value_raises_entries_in_another_facet | extract | vyvid | no Вивід test found for: a related facet value raising entries of another facet |
| test_a_store_finding_takes_its_technology_from_its_evidence | extract | kept | test_knowledge_base.py::test_a_store_finding_takes_its_technology_from_its_evidence |
| test_a_decision_is_claimed_by_what_it_decides_not_its_title | extract | vyvid | tests/test_index_extract.py::test_a_decision_is_claimed_by_what_it_decides_not_its_title |
| test_each_numbered_decision_and_addendum_is_a_section_with_its_own_range | extract | vyvid | tests/test_index_extract.py::test_each_numbered_decision_and_addendum_is_a_section_with_its_own_range |
| test_a_section_is_an_auxiliary_node_and_never_an_entry | extract | vyvid | tests/test_index_extract.py::test_a_section_is_an_auxiliary_node_and_never_an_entry |
| test_a_question_is_read_from_its_lead_or_its_row | extract | vyvid | tests/test_index_extract.py::test_a_question_is_read_from_its_lead_or_its_row |
| test_a_question_is_an_entry_and_a_promotion_answers_it | extract | vyvid | tests/test_index_extract.py::test_a_question_is_an_entry_and_a_promotion_answers_it |
| test_an_unpromoted_rule_in_an_answer_is_reported_after_thirty_days | extract | vyvid | tests/test_index_extract.py::test_an_unpromoted_rule_in_an_answer_is_reported_after_thirty_days (printed as FINDING, not NOTE, so the gate does not see it) |
| test_every_question_of_the_plans_and_sketches_is_an_entry | extract | vyvid | tests/test_index_extract.py::test_a_question_is_an_entry_and_a_promotion_answers_it |
| test_an_addendum_lead_supersedes_or_narrows_numbered_decisions | extract | vyvid | tests/test_index_extract.py::test_an_addendum_lead_supersedes_or_narrows_numbered_decisions |
| test_a_superseded_decision_names_its_successor | extract | notes | Note: X is Superseded and its Status line names no successor (extract.py:352) |
| test_every_supersession_lead_names_a_numbered_decision | extract | notes | Note: <verb> decision N, which names no numbered decision of the file (extract.py:289) |
| test_the_signpost_columns_are_read_and_checked | extract | vyvid | tests/test_index_extract.py::test_the_signpost_columns_are_read_and_checked |
| test_a_narrowed_by_cell_points_an_entry_at_the_addendum_by_its_day | extract | vyvid | tests/test_index_extract.py::test_a_narrowed_by_cell_points_an_entry_at_the_addendum_by_its_day |
| test_the_corpus_resolves_every_narrowed_by_cell | extract | notes | Note: has Narrowed by ..., names no addendum or no addendum of that day (extract.py:452,460) |
| test_a_signpost_to_nothing_is_reported | extract | vyvid | tests/test_index_extract.py::test_a_signpost_to_nothing_is_reported |
| test_every_signpost_in_the_corpus_names_something | extract | notes | Note: names no entry or declared term (extract.py:674), whose prefix no ontology document declares (extract.py:395) |
| test_no_new_entry_points_at_the_whole_of_a_long_file | extract | vyvid | tests/test_ask.py::test_read_refuses_a_pointer_to_a_whole_long_file (read refuses it). No Вивід test found for: a corpus guard against new whole-file pointers |
| test_a_declared_term_carries_a_claim_from_its_own_document | extract | kept | test_knowledge_base.py::test_a_declared_term_carries_a_claim_from_its_own_document |
| test_no_new_claim_is_longer_than_the_limit | extract | kept | test_knowledge_base.py::test_the_build_reports_nothing_but_the_known_notes |
| test_find_prints_the_whole_claim_under_each_row | ask | vyvid | tests/test_ask.py::test_find_prints_the_whole_claim_under_each_row |
| test_flags_mark_a_boundary_a_debt_and_a_proposed_entry | ask | vyvid | tests/test_ask.py::test_flags_mark_a_boundary_a_debt_and_a_proposed_entry |
| test_an_open_backlog_idea_flags_the_entry_it_bears_on | ask | vyvid | tests/test_ask.py::test_an_open_backlog_idea_flags_the_entry_it_bears_on |
| test_a_closed_debt_does_not_flag_its_entry | ask | vyvid | tests/test_ask.py::test_a_closed_debt_does_not_flag_its_entry |
| test_a_superseded_decision_is_kept_marked_and_ranked_below_its_successor | ask | vyvid | tests/test_ask.py::test_a_superseded_decision_is_kept_marked_and_ranked_below_its_successor |
| test_a_reversed_section_is_marked_and_names_the_addendum | ask | vyvid | tests/test_ask.py::test_a_reversed_section_is_marked_and_names_the_addendum |
| test_an_entry_and_a_decision_name_the_addendum_that_narrowed_them | ask | vyvid | tests/test_ask.py::test_an_entry_and_a_decision_name_the_addendum_that_narrowed_them |
| test_declared_terms_are_searched_only_when_their_kind_is_named | ask | vyvid | tests/test_ask.py::test_declared_terms_are_searched_only_when_their_kind_is_named |
| test_a_weak_answer_points_at_the_terms | ask | vyvid | no Вивід test found for: the weak-answer advice to retry with --kind term |
| test_the_case_an_entry_does_not_cover_is_embedded_with_it | ask | vyvid | tests/test_ask.py::test_the_case_an_entry_does_not_cover_is_embedded_with_it |
| test_read_prints_the_fields_and_every_neighbour_before_the_text | ask | vyvid | tests/test_ask.py::test_read_prints_the_fields_and_every_neighbour_before_the_text |
| test_a_symmetric_neighbour_is_shown_from_either_end | ask | vyvid | tests/test_ask.py::test_a_symmetric_neighbour_is_shown_from_either_end |
| test_read_refuses_a_pointer_to_a_whole_long_file | ask | vyvid | tests/test_ask.py::test_read_refuses_a_pointer_to_a_whole_long_file |
| test_read_prints_an_entry_with_a_register_row_and_a_pointer | ask | vyvid | tests/test_ask.py::test_read_prints_an_entry_with_a_register_row_and_a_pointer |
| test_every_find_and_read_is_logged_with_its_best_score | ask | vyvid | tests/test_ask.py::test_every_find_and_read_is_logged_with_its_best_score |
| test_a_gap_is_recorded_with_its_entry_and_line | ask | vyvid | tests/test_ask.py::test_a_gap_is_recorded_with_its_entry_and_line |
| test_misses_near_lists_the_confident_and_incomplete | ask | vyvid | tests/test_ask.py::test_misses_near_lists_the_confident_and_incomplete |
| test_a_kind_can_be_excluded_and_every_other_kept | ask | vyvid | tests/test_ask.py::test_a_kind_can_be_excluded_and_every_other_kept |
| test_closing_a_gap_removes_its_lines_and_the_question_behind_it | ask | vyvid | tests/test_ask.py::test_closing_a_gap_removes_its_lines_and_the_question_behind_it |
| test_misses_removes_a_question_the_index_now_answers | ask | vyvid | tests/test_ask.py::test_misses_removes_a_question_the_index_now_answers |
| test_a_slice_is_found_only_when_asked_for_or_named | ask | vyvid | tests/test_shown.py::test_find_shows_a_named_slice_first_and_no_slice_otherwise |
| test_a_rebuild_embeds_only_changed_text | embed | vyvid | tests/test_index_core.py::test_a_rebuild_embeds_only_changed_text |
| test_vectors_from_another_revision_are_refused_and_rebuilt | embed | vyvid | tests/test_index_core.py::test_vectors_from_another_revision_are_refused_and_rebuilt |
| test_an_unavailable_model_leaves_no_stale_vectors | embed | vyvid | tests/test_index_core.py::test_an_unavailable_model_leaves_no_stale_vectors |
| test_find_ranks_by_meaning_and_filters_exactly | embed | vyvid | tests/test_ask.py::test_find_ranks_by_meaning_and_filters_exactly |
| test_find_falls_back_when_nothing_is_close | embed | vyvid | tests/test_ask.py::test_find_falls_back_when_nothing_is_close |
| test_find_falls_back_when_no_entry_has_the_facets | embed | vyvid | tests/test_ask.py::test_find_falls_back_when_no_entry_has_the_facets |
| test_find_falls_back_when_there_are_no_vectors | embed | vyvid | tests/test_ask.py::test_find_falls_back_when_there_are_no_vectors |
| test_a_matching_facet_raises_an_entry_and_a_mismatch_hides_none | embed | vyvid | tests/test_ask.py::test_a_matching_facet_raises_an_entry_and_a_mismatch_hides_none |
| test_misses_lists_each_question_once_newest_first | embed | vyvid | tests/test_ask.py::test_misses_lists_each_question_once_newest_first |
| test_find_lists_what_the_top_answers_are_linked_to | embed | vyvid | tests/test_ask.py::test_find_lists_what_the_top_answers_are_linked_to |
| test_a_phase_matches_up_and_down_its_chain_and_never_a_sibling | embed | vyvid | tests/test_ask.py::test_a_phase_matches_up_and_down_its_chain_and_never_a_sibling |
| test_a_decision_is_scored_by_its_best_section_and_points_at_it | embed | vyvid | tests/test_ask.py::test_a_decision_is_scored_by_its_best_section_and_points_at_it |
| test_the_register_is_read_into_three_schemes_of_ratified_values | facets | vyvid | tests/test_facets.py::test_the_packaged_general_register_holds_the_three_schemes |
| test_each_column_becomes_the_skos_property_that_states_its_meaning | facets | vyvid | tests/test_facets.py::test_the_turtle_is_the_same_bytes_for_the_same_registers (SKOS concept only). No Вивід test found for: broader, related, scopeNote per column |
| test_the_same_register_gives_the_same_bytes_and_any_row_order_the_same_graph | facets | vyvid | tests/test_facets.py::test_the_turtle_is_the_same_bytes_for_the_same_registers (repeat only). No Вивід test found for: row-order permutation |
| test_the_real_register_generates_the_same_bytes_twice | facets | vyvid | tests/test_facets.py::test_the_turtle_is_the_same_bytes_for_the_same_registers |
| test_a_broader_or_related_value_defined_nowhere_is_refused_with_its_line | facets | vyvid | tests/test_facets.py::test_a_merge_that_cannot_be_read_is_refused_with_its_problem |
| test_a_broader_value_in_another_scheme_is_refused | facets | vyvid | tests/test_facets.py::test_a_merge_that_cannot_be_read_is_refused_with_its_problem |
| test_a_value_defined_twice_is_refused | facets | vyvid | tests/test_facets.py::test_a_merge_that_cannot_be_read_is_refused_with_its_problem |
| test_a_table_with_other_columns_or_a_flag_outside_yes_and_no_is_refused | facets | vyvid | tests/test_facets.py::test_a_merge_that_cannot_be_read_is_refused_with_its_problem |
| test_the_generated_turtle_is_never_committed | facets | gone | Вивід builds the facet Turtle in memory, no derived file is written |
| test_normalise_unifies_the_spellings_one_decision_is_written_in | identifiers | vyvid | tests/test_index_extract.py::test_two_spellings_of_one_identifier_count_once_under_the_first |
| test_normalise_keeps_distinct_decisions_apart | identifiers | vyvid | tests/test_index_extract.py::test_two_spellings_of_one_identifier_count_once_under_the_first |
| test_the_decision_pattern_matches_every_spelling_the_corpus_uses | identifiers | vyvid | no Вивід test found for: LATTICE's ADR spelling pattern (now a vyvid.toml family, exercised by mise run check:identifiers) |
| test_the_decision_pattern_does_not_match_ordinary_prose | identifiers | vyvid | no Вивід test found for: LATTICE's ADR spelling pattern (now a vyvid.toml family, exercised by mise run check:identifiers) |
| test_every_family_with_a_definition_rule_names_where_it_defines | identifiers | vyvid | tests/test_index_extract.py::test_an_unknown_family_rule_is_refused |
| test_a_question_raised_outside_a_plan_or_sketch_is_counted_and_never_failed | identifiers | vyvid | tests/test_identifiers.py::test_a_loose_pattern_reads_a_bare_match_only_where_its_identifier_is_defined |
| test_a_removable_family_is_never_failed | identifiers | vyvid | tests/test_identifiers.py::test_a_removable_family_is_reported_and_never_failed |
| test_the_corpus_has_no_unresolved_identifier_outside_the_baseline | identifiers | vyvid | mise run check:identifiers (vyd check identifiers) over the real corpus, tests/test_identifiers.py::test_a_resolved_mention_passes_and_an_unresolved_one_fails |
| test_the_scan_skips_a_generated_copy_and_keeps_an_original | identifiers | vyvid | tests/test_identifiers.py::test_a_skipped_file_and_a_generated_copy_are_not_read |
| test_a_known_decision_resolves_to_its_canonical_filename_spelling | identifiers | vyvid | tests/test_identifiers.py::test_another_spelling_of_a_defined_identifier_is_a_variant_and_never_fails |
| test_or1_a_family_defining_one_identifier_twice_is_reported | identifiers | vyvid | tests/test_identifiers.py::test_the_first_row_committed_keeps_a_duplicated_number |
| test_wb8_first_in_is_decided_to_the_second_and_a_tie_goes_to_the_maintainer | identifiers | vyvid | tests/test_identifiers.py::test_two_rows_committed_in_the_same_second_are_left_to_the_maintainer |
| test_or1_the_corpus_defines_no_identifier_twice | identifiers | vyvid | mise run check:identifiers over the real corpus, tests/test_identifiers.py::test_the_first_row_committed_keeps_a_duplicated_number |
| test_the_tbox_parses_in_the_strict_store_not_only_in_rdflib | vocabulary | vyvid | no Вивід test found for: the T-Box file parsing in the strict store |
| test_every_property_states_a_domain_and_a_range | vocabulary | vyvid | no Вивід test found for: every T-Box property having a domain and range |
| test_every_class_and_property_says_what_earns_it | vocabulary | vyvid | no Вивід test found for: every T-Box class and property having a comment |
| test_the_derived_edge_is_the_only_one_and_is_marked_as_such | vocabulary | vyvid | no Вивід test found for: citedWith as the only derived edge |
| test_the_facets_meet_the_skos_scheme | vocabulary | vyvid | no Вивід test found for: facet properties ranging over skos:Concept |
| test_every_node_kind_is_a_subclass_of_node | vocabulary | vyvid | no Вивід test found for: every node kind subclassing Node |
| test_status_is_a_closed_set_of_typed_individuals | vocabulary | kept | test_knowledge_base.py::test_every_status_used_is_in_the_tbox_closed_set (used within declared only, the exact five not asserted) |
| test_the_vocabulary_sits_outside_the_substrate_release | vocabulary | gone | the T-Box is no longer a LATTICE file or in the release |
