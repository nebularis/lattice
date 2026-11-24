<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Two families in one mapping vocabulary (MSA-I10)

This spike writes two families of records in R2RML, the ledger's records and the derived family of one Surface promotion, and states beside each table the relational place a compiled profile could hold for it. It answers the falsifier of investigation MSA-I10 in the multi-store sketch, that the two families need different vocabularies. The [note](../../docs/developer/notes/multi-store/MSA-I10-two-families-one-mapping.md) gives the findings, and the place each table emits is in [results/places.md](results/places.md).

## Run

From inside the repository:

```
mise exec -- python spikes/multi-store-mapping/mapping.py
mise exec -- python -m pytest spikes/multi-store-mapping -q -p no:cacheprovider
```

On Windows PowerShell quote the separator, `mise exec '--' python ...`, since `mise` is a function there and drops a bare `--`. The script needs rdflib. It reads the persistence compiler's logical keys where that package is installed, and says so where it is not. It runs no database.

The script prints its report and writes `results/places.md`. It exits 1 where the falsifier fires or the mapping does not hold, and 0 otherwise. Two runs on the same checkout write the same file, which a test checks.

## Files

| File | What it holds |
|---|---|
| `ledger.r2rml.ttl` | the ledger's records, every record of its runtime vocabulary but the supersession, nine tables |
| `promotion.r2rml.ttl` | the derived family of the promotion in Surface's example `saas-subscription-currency.ttl`, one table |
| `place.ttl` | the terms the spike adds beside R2RML to state a relational place, under an example.org namespace. None is a LATTICE term |
| `mapping.py` | reads both mappings, emits their places, and checks them |
| `test_mapping.py` | the result and one test for each check's failure |
| `results/places.md` | the places, generated |

## Where the inputs come from

The script asks the repository catalogue reader, `tools/lattice_repo_catalogue.py` (STD-273), for the ledger module's runtime vocabulary and examples and for Surface's examples, as the shape census does. It walks up from `LATTICE_ROOT` or the working directory to the checkout that holds the reader.

## What it checks

| Check | Fails when |
|---|---|
| one vocabulary | a mapping uses a term that is neither R2RML's nor one `place.ttl` declares |
| every column holds something | a column holds no key part of a logical resource, no field and no derived value, or a key column holds no key part |
| coverage | a record or a property the ledger's runtime vocabulary declares has no map or no column. The supersession and its properties are held, and listed |
| both directions | the records of an example, encoded to rows by inverting the mapping and decoded by R2RML's rules, are not the same triples, or the rows break a key, a unique constraint, a foreign key or an exactly-one field |

The encode puts each triple in the one column whose predicate and subject class match, in the row the record identifies. A derived column, which decodes to nothing, is filled after by the rule its place states. The decode follows R2RML for the subset the two mappings use. Graph maps, joins, SQL views and language tags are refused, never half read.

An `rdfs:comment` on a record has no column. It is counted as an annotation and left out of both sides of the comparison.

## Limits

- The interpreter is the spike's own, not a conforming R2RML processor, and covers only the constructs the mappings use.
- The constraints are checked on the encoded rows in Python. No SQL is generated or run.
- The supersession is not mapped until the ledger's LG-Q58 is answered.
- The promotion example declares no persistence profile, so each subscription is taken as the root of its own source aggregate.
