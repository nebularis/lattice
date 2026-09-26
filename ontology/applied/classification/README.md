<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Classification (`cls:`)

Cross-domain classification properties (ADR-A98 decision 1, epic D8): territory, asset class and
industry. Built by the [`applied-insurance-reference`](../../../docs/developer/plans/applied-insurance-reference.md)
epic (AIR-1.2), because insurance is its first consumer, but the module carries no insurance
vocabulary: any domain may use or specialise it.

## Files and namespaces (ADR-A98 decision 6)

| File | Content | Namespace | Prefix | Version IRI |
|---|---|---|---|---|
| `spec/classification.ttl` | `cls:territory`, `cls:assetClass`, `cls:industry` | `https://www.nebularis.org/neuro-semantic/lattice/applied/classification#` | `cls:` | `…/lattice/applied/classification/0.1.0` |
| `vocab/classification-vocab.ttl` | one `voc:SchemeContract` per property, no bound scheme | `https://www.nebularis.org/neuro-semantic/lattice/applied/classification/vocab#` | `cls-voc:` | `…/lattice/applied/classification-vocab/0.1.0` |

## The three contracts

| Contract | Constrains |
|---|---|
| `cls-voc:TerritoryContract` | `cls:territory` |
| `cls-voc:AssetClassContract` | `cls:assetClass` |
| `cls-voc:IndustryContract` | `cls:industry` |

None binds a scheme here. A reference edition or a deployment's own scheme binds later, from
whichever module publishes or consumes it — this module only declares that the classification
exists and which property it governs.

## How a domain specialises these properties

Each property is declared with no domain and range `skos:Concept`, so any applied module may use
it directly. A module with its own, narrower classification need declares a sub-property instead
of a fresh, unrelated one — for example `aeo:peril rdfs:subPropertyOf icm:peril` in the insurance
exposure module (Phase 4), so a query over `icm:peril` still reaches it. This module is not itself
an example of that pattern: `cls:territory`, `cls:assetClass` and `cls:industry` are the properties
being specialised, not specialisations themselves.

## The no-domain-terms rule

This module never grows a domain-specific term (an insurance code, a lending product name, and so
on). A domain-specific classification, however cross-cutting it feels within that domain, belongs
in that domain's own `common/` module (ADR-A98 decision 1) — `insurance/common/`'s `icm:peril` and
the rest are the example, not `cls:` growing an insurance-shaped property.
