<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: MSA-F5, the event's logical key names one event

**Unit:** [`multi-store-architecture`](../status/multi-store-architecture.md)
**Plan:** [multi-store-architecture](../plans/multi-store-architecture.md), MSA-F5, from finding MSAI4-04 of [MSA-I4](MSA-I4.md)
**Machine:** machine S, Windows, Python from the worktree's `.venv`, Oxigraph as the persistence tests' engine. **Placement:** T0, public. The persistence contract, nothing domain-specific.
**Status:** built 2026-11-18, not verified. The branch defers versioning, so the version check's `UNBUMPED` for `spec/persistence.ttl` is expected until the merge.

## Invariant

A resource's logical key names one resource. One append writes all its events under one revision and one sequence number, so `stream, seq` named the append, and a relational realisation keyed on it would hold one event of each (MSAI4-04). The key is now `stream, seq, event`, the event's IRI naming it within its append, which the caller library already holds unique there (`DuplicateEvent`). The brief allowed the IRI or the operation sequence where `opSeqRequired` holds. The IRI is the one that is always present, so a key that depends on a dimension's value was not needed.

## Change

- `tools/persistence/src/persistence/contract.py`, `LOGICAL_KEYS[EVENT]` is `("stream", "seq", "event")`, with the reason in its docstring.
- `ontology/persistence/README.md`, the `turtle-spec` block of §6.6 states `dal:Event dal:logicalKey "stream, seq, event"`, and the release notes gain an Unreleased entry, classed as changing meaning. `spec/persistence.ttl` regenerated from it with `tools/literate_extract.py`.
- `tools/persistence/tests/test_append_events.py`, a new test.

## Tests

| ID | Given / When / Then | Level | Invariant | Pass criterion | Kind |
|---|---|---|---|---|---|
| F5-T1 | Given a three-row append run on each engine, with and without parameter guards, when each event's key is read from what the append wrote by the parts `LOGICAL_KEYS` names, then the three keys are distinct, and every event is under the one revision | L3 | the invariant | `test_msa_f5_the_event_s_logical_key_names_each_event_of_an_append` passes | negative |
| F5-T2 | the code's keys against the spec's | L3 | one key in both | `test_h2_7_t4_each_logical_key_of_the_code_is_the_spec_s` passes | positive |

## Commands and results

Run on 2026-11-18.

| Command | Result |
|---|---|
| `mise exec -- python -m pytest tools/persistence/tests/test_append_events.py -q -k msa_f5`, before the change | 2 failed (Oxigraph, with and without guards): `assert 1 == 3`, the one key `('urn:stream:orders/1', '1')` for three events |
| `mise exec -- python tools/literate_extract.py ontology/persistence/README.md --layer persistence --root . --check`, before writing | `DRIFT ontology/persistence/spec/persistence.ttl`, the edited key and nothing else |
| the same without `--check`, then with it | five artefacts written, then consistent. The spec's diff is the one line |
| `mise exec -- python -m pytest tools/persistence/tests/test_append_events.py tools/persistence/tests/test_contract_emission.py tools/persistence/tests/test_patch_log.py -q` | 207 passed |
| `mise run check:persistence` | exit 0, 4816 passed |
| `mise run check:ontology-versioning -- --base-ref main` | `UNBUMPED ontology/persistence/spec/persistence.ttl`, expected while the branch defers versioning, with its `HOW` line |

The one command for the slice is `mise run check:persistence`.

## Deliberate non-coverage

- No generated operation's text changes. The key is a statement of the contract, read by a realisation that has to key the resource, so no SPARQL test moves.
- `mise run check:persistence-conformance`, the suite on every engine, was not run for this slice, since no generated text changed. It is listed for the merge.

## Decisions taken

- **The IRI, not the operation sequence.** The operation sequence names an event only where `opSeqRequired` holds, so a key on it would depend on a dimension. The IRI always names one.
- **Changes meaning, in the release note.** A reader that keyed events by the old key reads differently.
