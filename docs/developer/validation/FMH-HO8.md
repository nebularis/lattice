<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: FMH-HO8, injective graph naming

**Unit:** [`formal-methods-track-h`](../status/formal-methods-track-h.md), slice HO8
([plan §3.5](../plans/formal-methods-track-h.md#ho8-injective-graph-naming-td-38)).
**Source:** [ADR-A122](../../architecture/decisions/ADR-A122-aggregate-ownership.md) decision 8,
[sketch §9](../sketches/persistence-aggregate-ownership.md#9-named-graph-naming-ao-q13-ho8), and review findings F6 and F11.
**Closes:** TD-38 (removed from the register).
**Decisions needing confirmation:** none. Two small deviations, below.

## Invariant

Equal graph IRIs imply the same family and the same root. Within a family, a graph is the prefix, the whole root
IRI percent-encoded, and the suffix, and percent-encoding is injective, so two roots that share a local name no
longer share a graph. Across families, the prefixes before `{id}` form an antichain and a suffix starts with a
character the encoding never emits, so one family's graphs cannot be read as another's.

## What changed

- The seven templates that name a graph (create, replace and tombstone, each with a dataset-guard variant, and
  `unconditional-write`) compute `IRI(CONCAT(prefix, ENCODE_FOR_URI(STR($root)), suffix))` where they computed
  `CONCAT(prefix, REPLACE(STR($root), "^.*[/#]", ""))`. Text after `{id}` was silently dropped. It is kept.
- `operations.py` splits `dal:graphIriTemplate` at `{id}` into `graphPrefix` and `graphSuffix`. A family with no
  template defaults to `urn:g:<family token>/{id}`, where it defaulted to `urn:g:<the class IRI>/`.
- `validator.py`: `GraphIriTemplateInvalid` (no `{id}`, more than one, or a suffix whose first character the encoding
  can emit) and `GraphIriTemplateOverlap` (two families whose prefixes are nested or equal, declared or defaulted).
  The overlap is checked across the whole compile, in `compiler.py`.
- Two witnesses. The inventory is 98 of 98.
- The `dal:graphIriTemplate` comment in the spec says all of this. It is edited within 0.3.0, which has no tag yet,
  so `check:ontology-versioning` run against `HEAD` flags it until committed, and the full sweep against `main` does not.
- Register and README: TD-38 removed, and the rule stated. The gap rule `NamedGraphNamedFromLocalName` is removed.

## Deviations, for the maintainer

1. **The default template changes shape.** A family with no template named its graphs `urn:g:` plus the whole class
   IRI. The sketch says `urn:g:<family token>/{id}`, and it is what is built. Two classes whose local names are the
   same (in two namespaces) then share a default prefix, and that is refused as an overlap (HO8-T5c). It is the
   ambiguity the rule exists to catch.
2. **The overlap is keyed by family.** A family is one boundary profile, or one class when no template is declared, so
   the several targets one profile resolves to (one per deployment) are not an overlap with each other.

## Test cases

In `tools/persistence/tests/test_graph_naming.py`, on rdflib's `Dataset`. Expected graph IRIs are computed in Python
with percent-encoding of every byte but the unreserved characters.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| HO8-T1 | roots `https://example.org/a/1` and `https://example.org/b/1` in one family / create both / two graphs, each with its own payload | L5 | + |
| HO8-T2 | `urn:g:orders/{id}/data`-style template / create / the graph IRI ends in `/data` | L5 | + |
| HO8-T2b | a root with `?` and `#`, and a family with no template / create / the encoded root under `urn:g:loanapplication/` | L5 | + |
| HO8-T3 | a template with no `{id}`, and one with two / compile / `GraphIriTemplateInvalid` | L3 | − |
| HO8-T4 | a suffix beginning with a letter, a digit, `-`, `.`, `_`, `~` or `%` / compile / `GraphIriTemplateInvalid` | L3 | − |
| HO8-T4b | a suffix beginning with `/`, `:`, `#`, `?` or `@` / compile / accepted | L3 | + |
| HO8-T5 | families `urn:g:{id}` and `urn:g:orders/{id}` / compile / `GraphIriTemplateOverlap`, naming both profiles | L3 | − |
| HO8-T5b | equal prefixes refused, and `urn:g:lend/` with `urn:g:lending/` accepted | L3 | +/− |
| HO8-T5c | two classes with one local name and no template / compile / `GraphIriTemplateOverlap` | L3 | − |
| HO8-T6 | the two new witnesses / the witness check / each triggers exactly its own rule | L4 | + |
| HO8-T7 | every shipped example / compile / none is refused by the new rules | L4 | + |
| HO8-T8 | the seven templates / their text / each encodes the whole root and keeps the suffix, none uses `REPLACE` | L1 | + |

## One command

Run from the repository root. A pass is `1356 passed, 1 xfailed`, with no new skip. The expected failure is TD-23.

```bash
mise run check:persistence
```

## Adversarial probes

Run on 2026-10-10, each restored afterwards.

| Mutation | Result |
|---|---|
| the suffix is dropped again | T2 fails |
| the suffix rule disabled | seven items fail (T4 and its witness) |
| the overlap check reduced to equal prefixes | T5 and the `GraphIriTemplateOverlap` witness fail |

## Deliberate non-coverage

- A store that refuses an over-long graph IRI. No standard limits IRI length, and the review (§7) decided to put a
  per-store limit in the capability record if one is ever found.
- Renaming graphs when a template changes. That is a migration of stored data (law L15), which nothing generates.
- The audits, which name no graph from a root.
