<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Component administration: plan

**Unit ID:** `component-administration` (slice prefix ADM)
**Prefix:** ADM
**Status record:** [component-administration.md](../status/component-administration.md)
**Decisions it builds on:** ADR-A29 (`mise` as the one task entry point), ADR-A149 (publication from the studio, whose writer and broker it reads first), PRI-52 (no new authoritative store).
**Placement:** open. Tooling for running components, nothing domain-specific.

## Why

Nothing lets an operator ask a running component what it holds or whether it is working, and nothing repairs what a component left behind. The review of the studio's fixes on 2026-11-19 found two cases. A stream writer whose thread has ended stays a member of its group and holds its partitions, and nothing shows it (MSAF2-01 of the [multi-store plan](multi-store-architecture.md)). A broker declared by an older worker keeps a binding the topology contract no longer states, and declaring again removes nothing.

## Outcome

- **A read side.** For each component it covers, what the component holds and whether it is working, from one command. For the studio's writer that is its group membership, the partitions it holds, the offset last stored for each and whether its thread is alive.
- **An act side.** Named repairs, each safe to run twice, each stating what it removes before it removes it. The first reconciles a broker with the topology contract, which unbinds and deletes what the contract no longer declares.

## Out of scope

- Monitoring, alerting and dashboards. This unit answers a question asked, and watches nothing.
- Repairs to the graph store's data. A repair here touches coordination state only, which can be rebuilt (PRI-52).
- Deployment and scaling of components.

## Order and dependencies

It is planned on 2026-11-19 and built later, at the maintainer's word. ADM-1 reads the state MSA-F10 of the [multi-store plan](multi-store-architecture.md) leaves readable on the writer. Nothing waits on this unit.

## Slices

| Slice | Kind | Where | Depends on |
|---|---|---|---|
| ADM-0 | design | a sketch that answers ADM-Q1 to ADM-Q3 with their options and what each costs | none |
| ADM-1 | read | the studio writer's health: group membership, partitions held, offset last stored for each, thread alive | ADM-0, MSA-F10 |
| ADM-2 | repair | a broker reconciled with the topology contract, listing what it would remove before removing it | ADM-0 |

## Questions for the maintainer

- **ADM-Q1, what form it takes.** A command-line tool that reads the contracts and talks to the broker and the store, an endpoint on each service, or both with the tool calling the endpoints. The first needs no change to a service and cannot see inside a process, such as a thread's state.
- **ADM-Q2, who may run a repair.** Whether a repair needs a principal and leaves a record, and where that record is kept.
- **ADM-Q3, which components it covers first** after the studio's writer and its broker.
