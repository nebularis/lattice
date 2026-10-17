<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: RC1, the repository catalogue and its reader

**Unit:** [`improved-ontology-documentation`](../status/improved-ontology-documentation.md), slice RC1
([plan](../plans/improved-ontology-documentation.md#slices)).
**Implements:** [ADR-A121](../../architecture/decisions/ADR-A121-repository-catalogue.md) decisions 1 to 5
and 9, for ontology modules. Roots, tool packages, documentation areas and the bypass scan are RC3's,
downstream extension RC4's and the package RC5's.
**Decisions needing confirmation:** eight implementation choices, below.

## Invariant

Every module under `ontology/` is listed once, in order, and its entry states exactly the subdirectories it
has, the files its README generates in extraction order, and, for a substrate layer, the layers it may
import. Each of those is checked against the tree, against what the README actually generates, and against
the import guard's rules, so the catalogue cannot silently disagree with any of them. Nothing reads the
catalogue yet except its own check, so no tool's behaviour changes (RC2 moves the tools onto it).

## What changed

- `repository-catalogue.md`, new at the root. The conventions (roles, kinds, versioned documents and
  directories) and the ordered list of 19 modules, with prose for a reader.
- `tools/lattice_repo_catalogue.py`, new. The reader, standard library only: root discovery, block reading
  (fence-aware), schema validation, `check()`, and the command line `path`, `paths`, `check` and
  `dump --json`.
- 19 module READMEs. Each gains one `toml repository-catalogue` block, its entry. Governance's README was
  empty, and now says what the module is for and holds its entry.
- `mise.toml`. `check:catalogue`, part of `check`. `tools/test_lattice_repo_catalogue.py` joins
  `check:ontology-catalog`.
- `README.md` lists `repository-catalogue.md` in the repository layout. The developer guide describes the
  reader and the check, and its extractor commands now go through `mise exec`.

## Implementation choices, for the maintainer

1. **A module's name is its path under `ontology/`**, for example `applied/insurance/peril`, the same string
   `literate_extract.py --layer` takes. The root file lists the names in `[catalogue] modules`, and each
   README's entry is a `[module]` table that does not repeat the name.
2. **Five kinds:** `substrate` (ADR-A01's order), `standalone` (MORK, SPC, Surface, Persistence),
   `applied`, `example` (`ontology/examples/insure-o`) and `scaffold` (Governance). Each is described in the
   root file.
3. **A module's roles are exactly its subdirectories**, and the conventional roles include MORK's `mtp` and
   `targets` and insure-o's `cases`, so the tree-to-catalogue check knows them.
4. **`imports` is given for the eight substrate layers only**, equal to the import guard's `ALLOWED`. Other
   modules have none and are not judged, as today. Applied entries can state imports later, when the import
   guard reads them (RC2).
5. **Where an unmigrated README holds its entry.** At the end of its extraction section ("Extraction
   contract" or "How to Read This Document") where it has one, otherwise in a new last section, "Repository
   catalogue entry" (MORK, Persistence, the two applied modules without a literate source, insure-o and
   Governance). Migration moves each entry into section 3.
6. **Paths are printed relative to the repository root**, so a `mise` task, which runs from the root, can
   use them as they are.
7. **`load()` is not cached.** Nothing calls it often enough to need it.
8. **No path templates in the conventions.** Each entry lists its extracted files, so `{module}`-style
   defaults have no reader yet.

## Deviations from the plan

1. The plan puts each entry in section 3. For an unmigrated README, section 3 may be about something else,
   so choice 5 applies until the README migrates.
2. Governance's README gained content, two sentences and its entry, since an empty file cannot hold one.

## Test cases

In `tools/test_lattice_repo_catalogue.py`.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| RC1-T1 | the repository / load / 19 modules, the substrate first in ADR-A01's order, Governance last, Instrument's three shape files in order | L1 | + |
| RC1-T2 | the repository / check / no problem | L3 | + |
| RC1-T3 | each literate module / its README extracted with the declared shapes / the generated files are exactly the declared ones | L3 | + |
| RC1-T4 | the substrate entries / compared with `import_guard.ALLOWED` / equal, and no other module has imports | L3 | + |
| RC1-T5 | a small tree / root discovery from a subdirectory, from outside with and without `LATTICE_ROOT`, and given explicitly / found, refused naming `LATTICE_ROOT`, found, given | L1 | +/− |
| RC1-T6 | a catalogue block inside a four-backtick fence / read / ignored | L1 | + |
| RC1-T7 | four entries that disagree with their tree (a missing role directory, an undeclared one, an import of no module, a missing extracted file) / check / each named | L1 | − |
| RC1-T8 | a module directory on disk that is not listed / check / named | L1 | − |
| RC1-T9 | six malformed entries (an unknown key, an unknown kind, a non-list, an unknown extracted role, a key defined twice, bad TOML) / load / each refused | L1 | − |
| RC1-T10 | a listed module with no entry, one with no README, and an unknown key in the root file / load / each refused | L1 | − |
| RC1-T11 | the command line / `paths`, `path`, a missing role, `dump --json`, `check` / the paths in order, the error names where to declare the role, JSON, exit 0 | L4 | +/− |

## One command

Run from the repository root. A pass is every test passing, with no skip.

```bash
mise exec -- python -m pytest tools/test_lattice_repo_catalogue.py -q
```

Then the check itself, which should report 19 modules agreeing with the tree:

```bash
mise run check:catalogue
```

And the ontology tool suite, which now includes the new tests, to confirm the README edits change no
extraction. A pass is the suite passing as before:

```bash
mise run check:ontology-catalog
```

## Adversarial probes, for the gate

| Mutation | Expected |
|---|---|
| `check()` stops comparing roles with subdirectories | RC1-T7 fails |
| delete `shapes/rules.ttl` from Eligibility's entry | RC1-T3 fails, and `check:catalogue` passes, which is why T3 exists |
| give Party `wording` among its imports | RC1-T4 fails |

## Deliberate non-coverage

- No tool reads the catalogue yet. RC2 moves `literate_extract.py`, the per-layer tests, `import_guard.py`,
  `ontology_version_check.py` and `check_formal_freshness.py` onto it.
- Roots, tool packages, documentation areas, generated outputs, site sections, the generated AGENTS.md table
  and the bypass scan. RC3 and DOC2.
- `dump --json` has no consumer in another runtime yet.
