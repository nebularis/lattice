<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Loading LATTICE in Protégé

How to open any LATTICE ontology in Protégé with its import closure resolved
from the checkout, and how to confirm the generated catalogs are what
resolved it ([ADR-A88](../architecture/decisions/ADR-A88-ontology-import-resolution-for-consumers.md)).
This is the manual step in the AOR-4 Validation Pack.

## Why a successful load is evidence

LATTICE imports its layers by version IRI, for example
`https://www.nebularis.org/neuro-semantic/lattice/foundation/0.3.0`. None of
these IRIs is served on the web. If Protégé loads a layer's imports, it found
them through a catalog. Protégé reads the `catalog-v001.xml` beside the file it
opens. In every `spec/` and `vocab/` directory that file is a stub with one
`nextCatalog` entry pointing at `ontology/catalog-v001.xml`, which maps every
LATTICE IRI to a file.

## Before you start

- Protégé 5.6 (desktop).
- From the repository root, confirm the catalogs are current:

  ```bash
  mise run check:ontology-catalog
  ```

- Note the output of `git status --short ontology`, so you can tell afterwards
  whether Protégé rewrote anything.

## Test 1: a layer with a deep import closure

1. Start Protégé. Choose **File → Open…** and select
   `ontology/behaviour/spec/behaviour.ttl`. Open the file, not a recent-files
   entry or a URL.
2. Expected: the ontology opens with no "missing imports" or "could not load
   import" dialog. Loading may take a few seconds while Protégé fetches the
   external imports (PROV-O and SKOS) from the W3C, which the root catalog
   maps to their published locations.
3. Open the ontology selector (the drop-down naming the active ontology at the
   top of the window). Expected: it lists Behaviour together with Foundation,
   Vocabulary, Quantification, Party, Eligibility and Instrument, plus PROV-O
   and SKOS.
4. Select Foundation in that selector. The window title shows the active
   ontology's IRI and its physical location. Expected: a file path ending in
   `ontology/foundation/spec/foundation.ttl` in your checkout.
5. In the **Entities** tab, find `fnd:DerivedArtefact`. Expected: present, with
   superclass `prov:Entity`. That confirms both the local Foundation file and
   the external PROV-O loaded.

## Test 2: remove the root catalog (negative control)

1. Close the ontology in Protégé without saving.
2. Temporarily rename the root catalog:

   ```bash
   mv ontology/catalog-v001.xml ontology/catalog-v001.xml.off
   ```

3. Open `ontology/behaviour/spec/behaviour.ttl` again.
4. Expected: Protégé reports the LATTICE imports it cannot load. This shows
   that Test 1 depended on the stub chaining to the root catalog.
5. Cancel or skip the missing imports, close without saving, and restore the
   catalog:

   ```bash
   mv ontology/catalog-v001.xml.off ontology/catalog-v001.xml
   ```

## Test 3: a MORK-family document

1. Open `ontology/mork/spec/Executable.ttl`.
2. Expected: no missing-import dialog. It imports MORK by its unversioned
   ontology IRI, and MORK imports Foundation by version IRI, so this exercises
   both kinds of catalog entry.

## Afterwards

1. Quit Protégé without saving any ontology.
2. Run:

   ```bash
   git status --short ontology
   ```

   Expected: the same output as before you started. Protégé can add entries to
   a catalog when you use its import wizard or save. If a `catalog-v001.xml`
   changed, restore the generated version:

   ```bash
   mise run build:ontology-catalog
   ```

3. Confirm:

   ```bash
   mise run check:ontology-catalog
   ```

## Reporting

Record the result in the AOR-4 Validation Pack sign-off
(`docs/developer/validation/LOG.md`).

If Test 1 shows missing LATTICE imports, Protégé did not follow the stub's
relative `nextCatalog`. That is the open question in ADR-A88. Report which
imports were missing. The fallback is to generate full catalogs in every
directory instead of stubs.
