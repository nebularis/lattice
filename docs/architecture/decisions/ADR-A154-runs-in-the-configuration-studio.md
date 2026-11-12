<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A154: Runs in the Configuration Studio, results that are not stored and reach the browser as frames

**Status:** Proposed
**Date:** 2026-11-12 (proposed)
**Amends:** ADR-A136, what the studio's events may carry and which components it has. ADR-A148, how a transform's result reaches the browser
**Related:** [ADR-A136](ADR-A136-configuration-studio.md) (the studio, its writers and its worker), [ADR-A148](ADR-A148-mork-transform-backends.md) (the transforms worker), [ADR-A149](ADR-A149-publication-from-the-studio.md) (who may read a workspace), [ADR-A30](ADR-A30-shared-semantic-platform-cross-runtime-boundary.md) (graph references and CloudEvents across runtimes), [ADR-A35](ADR-A35-trusted-surface-worker-execution-boundary.md) (what a worker takes from a message), [ADR-A132](ADR-A132-persistence-caller-library.md) (the caller library), PRI-52, PRI-56, PRI-58, PRI-75
**Unit:** [`studio-visual-authoring`](../../developer/plans/studio-visual-authoring.md)

## Context

The studio returns a result in one of two ways. A job writes its input and its result to the store through the workspace's writer, and the browser reads the job's graph when an event says it changed. A transform, which runs a compiled mapping over a sample, stores nothing, and the service holds the HTTP request open while one worker runs it, for up to 30 seconds.

The studio is gaining simulators, which show what a write would do to a small dataset, and a pane that runs a chosen compiled mapping over a sample on demand. Their results are derived, can be repeated, and are wanted many times a minute and in steps. Neither way fits them. A job per step costs commits on the store that every save of the same workspace waits behind, and leaves graphs whose space the store reclaims only by compaction. A request that waits holds a connection for each step, gives nothing until the end, and ties the answer to one worker taking one request at a time.

The studio's events already reach a browser tab over the broker's MQTT, on a topic only that tab reads, relayed by the service, which decides at delivery whether the principal may read the subject. They are sent at QoS 0 on a clean session, so an event can be lost, and today that costs only a read of the job from the store, since an event holds a job's status and never its content.

## Decision

1. **A run.** A run executes the artefacts of a finished compile job over an input that is not saved, and stores nothing. It is a deterministic function of the compile job, the input and a time the request states, so its identifiers and its times come from the request (PRI-56), its output is ordered canonically, and each kind of run is tested with a permutation and a repeat (PRI-58). Compilation, validation, proposal and publication stay jobs.
2. **A run is accepted at once.** The service authenticates the request, checks that the principal may read the workspace and that the job is a finished compilation of the part the run names, checks the input's size and media type, publishes the request to the run worker's queue and answers `202` with the run's identifier. No request waits for a worker where the tab has events.
3. **The result comes as frames.** The run worker publishes the result as numbered frames on the studio's events exchange, each a CloudEvent whose subject is the run, with its sequence number and whether it is the last. A frame holds content. A job's event still holds its status and its workspace and never its content.
4. **The accepting instance relays.** The service instance that accepted a run keeps, in memory, who submitted it, from which tab, for which workspace and until when. Every instance reads every event, and only that instance forwards a run's frames, to the submitting tab's own topic. So a frame reaches a tab once and in the order one consumer read it, and who may hear a run never travels in a message. The entry is coordination state (PRI-52), and losing it loses only runs in flight.
5. **The check is at delivery.** Before each frame the relay asks whether the principal may read the workspace, by the rule a read of the workspace follows, from the graph as it is then. A change of access is one commit to the graph and needs no change in the broker.
6. **A deadline bounds a run.** The request states it as an absolute time. The message expires at it, the worker stops an execution that passes it, and the accepting instance sends a failed frame for a run it has not seen end by then and drops its entry. The browser holds the same deadline for the case where that instance has stopped.
7. **A run is never run twice by the broker's choice.** A worker that receives a run the broker marks as redelivered sends a failed frame saying a worker stopped during it, and acknowledges it. The author runs it again.
8. **Frames are assembled by sequence.** The browser keeps the first frame it sees for each sequence number, ignores a frame of a run it no longer shows, and has the result when every number up to the last is present. A run whose frames are not all present at its deadline is shown as incomplete, and the author runs it again. Nothing is read again from anywhere, since nothing was stored.
9. **Runs are bounded.** The contract states the largest frame, the most frames a run may send, the most runs a tab may have pending and the deadline of each kind of run. A result over the bound fails with a message that says so. The browser sends one run at a time for each pane and, of the requests that wait behind it, only the newest.
10. **Without events the same run answers on the request.** Where a deployment offers no events, or a tab's connection is down, the browser asks the service to wait. The accepting instance then collects the run's frames from the events it already reads into the response, or answers at the deadline that the run timed out. The worker behaves the same either way.
11. **A simulator's state is the tab's.** A simulator step's request carries the dataset it applies to and the edit, and the result is the change. No worker holds a session, any worker serves any step, and a step sent twice gives the same answer.
12. **The run worker.** The transforms worker of ADR-A148 becomes the run worker. It consumes a queue for interactive runs and a queue for sample runs, so a long sample run does not delay a simulator's step, takes a bounded number of requests at once, reads the store and never writes it, and checks each request as the service did (PRI-75). It runs XSLT and JOLT as it does today, and SPARQL on Apache Jena's in-memory dataset, with the Java caller library of ADR-A132 for a persistence operation. Jena is the engine the studio's own store runs, and each display that shows a simulated write says which engine evaluated it.
13. **The waiting transform route is deprecated.** `POST /api/workspaces/{ws}/transforms` stays for one release, answered by the run worker, and is then removed. This replaces the answer ADR-A148 records for how a transform's result reaches the browser.

**Rejected.** A job for every run, for the commits and the dead space it costs on the store. A request that waits for every run, which is what a simulator's steps would hold open. A session in a worker's memory, which needs every step routed to one worker and is lost with it. A scratch dataset in the store for a simulator's state, which adds writes and a second kind of data to the one state the studio has. Frames addressed by the worker to a tab's topic directly, which would move the decision of who hears a run out of the service and away from delivery. A copy of a run's result kept for a missed frame to be read from, which is a store beside the graph for something that can be run again.

## Consequences

- A simulator's steps and a sample run cost the store nothing, and no save waits behind one.
- A result can be shown in parts as it is produced.
- A lost frame costs the author a wait until the deadline and a second run. An interactive run's deadline is therefore short.
- The studio's events now carry content for runs, so the largest frame and the number of frames are limits of the contract, held to what the broker delivers to a slow reader.
- A service instance that stops loses the runs it accepted. Their authors see them as incomplete at the deadline.
- The run worker gains Jena, which the studio's other Java components already use.
- A simulation shows what Jena does. A deployment on another store may differ where the triple-store record says the two differ.
- A client of the waiting transform route has one release to move to runs.

## Provenance

**Unit:** [`studio-visual-authoring`](../../developer/plans/studio-visual-authoring.md) (plan), [sketch](../../developer/sketches/studio-visual-authoring.md), section 4, slice SVA-R1.

Drafted on 2026-11-12 from the maintainer's answers of that day to the sketch's questions: SVA-Q1 (c), frames, which reopened XJ-Q8 of the `mork-transforms` plan, SVA-Q2 (a), content in a run's frames only, SVA-Q4 (a), Jena in the Java run worker with Oxigraph left as a later option (BL-21), and SVA-Q16 (a), the transform route deprecated for the studio until a sidecar architecture is defined. Decision 11 rests on SVA-Q3, where the maintainer asked for the size of a request body in triples before answering, and it is confirmed or changed with that answer. The limits of decision 9 are set in the contract from the probes of slice SVA-R0, recorded in that slice's Validation Pack. The events this builds on were decided as PM-Q18 and PM-Q20 of the `projection-maintenance` unit.
