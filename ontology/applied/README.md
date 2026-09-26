<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Applied Domains

Lattice ships domain content on top of its substrate layers, at varying levels of maturity. This
directory holds two kinds of module. A **domain** groups everything specific to one applied field,
in `applied/<domain>/`, with a `domain-README.md` and one directory per module. A **cross-domain
module** sits directly under `applied/`, shared by two or more domains.

## Three levels of sharing (ADR-A98 decision 1)

A module lives at the lowest level that covers every module using it, or planned to.

| Level | Location | Content | Moving up |
|---|---|---|---|
| substrate | `ontology/<layer>/` | domain-neutral mechanisms with stated laws | clean-room promotion (ADR-A-C2) |
| cross-domain applied | `ontology/applied/<module>/` | domain-neutral mechanisms and classifications not yet promoted. No domain vocabulary | criteria of the module's own design |
| domain-shared | `ontology/applied/<domain>/common/` | content meaningful only in one domain, used by two or more of its modules | to cross-domain, when a second domain needs it |

Moving a module up a level changes its namespace and is MAJOR for every importer. The
lowest-level rule keeps such moves rare and deliberate.

## Dependency direction (ADR-A98 decision 5, as amended by its addendum)

Dependencies run one way. `classification/` imports the substrate only. A domain's `common/`
module imports `classification/` and the substrate. Every other module in a domain imports its
own `common/` module, directly or indirectly, and never a module of another domain. A
cross-domain module never imports a domain module.

## Namespaces and versioning

Each module versions independently under ADR-A86: `spec/`, `vocab/`, `shapes/` and `projection/`
each carry their own `.version`, and a shapes change in one module never moves another module's
number. Namespaces and prefixes follow ADR-A98 decision 6:

| Module | Namespace | Prefix |
|---|---|---|
| cross-domain `<module>` | `https://www.nebularis.org/neuro-semantic/lattice/applied/<module>#` | per module |
| `classification/` | as above | `cls:` |
| domain `<module>` | `https://www.nebularis.org/neuro-semantic/<domain>/<module>#` | per module |

A module's `vocab/` document, where it has one, uses the namespace without its `#` plus
`/vocab#`, and its own version IRI, `…/<module>-vocab/<semver>`.

## Modules

| Module | Level | State |
|---|---|---|
| `capacity/` | cross-domain | present |
| `classification/` | cross-domain | planned, `applied-insurance-reference` AIR-1.2 |
| `insurance/` | domain | see [`insurance/domain-README.md`](insurance/domain-README.md) |

Every applied module imports LATTICE layers and other applied modules by exact version IRI,
resolved through the catalog (ADR-A88).

