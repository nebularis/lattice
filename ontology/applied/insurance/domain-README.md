<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Insurance Domain

The insurance domain groups every applied module specific to insurance and reinsurance content.
It is being built by the
[`applied-insurance-reference`](../../../docs/developer/plans/applied-insurance-reference.md)
epic, whose sketches describe the design each module implements.

## Modules

| Module | Content | State | Built in |
|---|---|---|---|
| `common/` | insurance scheme contracts (peril, mechanism, agency, consequence, harm subject, pool), liability role types (ADR-A102), the loss event | not yet built | AIR-1.2 |
| `peril/` | reference peril vocabulary: cause scheme, characteristics, collections, crosswalks | not yet built | Phase 2 |
| `exposure/` | locations, assets, values, zones, dependencies, exposure units, loss history, requirements, liability exposure | not yet built | Phase 4 |
| `submission/` | packaging an exposure set version for underwriting | not yet built | AIR-6.1 |
| `claims/` | loss cause chains recorded against a responding contract | deferred with `contract/` (epic D2) | Phase 6 |
| `contract/` | term parameters, term relations, liability direction, optional compilation | deferred until Phases 1 to 4 are wired into Open CBAA (epic D2) | Phase 5 |

## Dependencies

`common/` imports `classification/` and the substrate. `peril/` imports `common/`. `exposure/`
imports `common/` and `peril/`. `submission/` imports `exposure/`. `claims/` imports `exposure/`
and `contract/`.

## Namespaces and prefixes (ADR-A98 decision 6)

| Module | Namespace | Prefix |
|---|---|---|
| `common/` | `https://www.nebularis.org/neuro-semantic/insurance/common#` | `icm:` |
| `peril/` | `https://www.nebularis.org/neuro-semantic/insurance/peril#` | `prl:`, for properties and datatypes. Schemes and concepts live in the module's `vocab/` document, prefix `prl-voc:` |
| `exposure/` | `https://www.nebularis.org/neuro-semantic/insurance/exposure#` | `aeo:` |
| `submission/`, `claims/`, `contract/` | fixed when those modules are built | — |

## The legacy contract module

An earlier `spec/structure/contract.ttl`, its vocabulary and its shapes were dropped (epic D1):
the spec did not parse as Turtle, it imported pre-LATTICE namespaces, and nothing in the
repository imported it. They remain available at the `insurance-contract-v0.2.0` and
`applied-insurance-shapes-v0.1.0` release tags.

## See also

- [`applied-insurance-reference`](../../../docs/developer/plans/applied-insurance-reference.md), the epic building this domain
- Its sketches: [peril-vocabulary.md](../../../docs/developer/sketches/peril-vocabulary.md),
  [asset-exposure-ontology.md](../../../docs/developer/sketches/asset-exposure-ontology.md),
  [term-parameters.md](../../../docs/developer/sketches/term-parameters.md),
  [mork-bridge.md](../../../docs/developer/sketches/mork-bridge.md),
  [peril-structure-whitepaper.md](../../../docs/developer/sketches/peril-structure-whitepaper.md)
- [`ontology/applied/README.md`](../README.md), the domains and sharing levels this module follows
