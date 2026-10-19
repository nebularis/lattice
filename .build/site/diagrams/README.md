<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Architecture Diagrams

Five views of the same system, each answering a different question. Start with whichever
question you have:

| # | Diagram | Answers |
|---|---|---|
| 1 | [The whole architecture](01-full-architecture.md) | Every axis at once: ontology layers, tools, platform services, apps, data realms, formal methods — how do they all relate? |
| 2 | [Development-time toolchain](02-development-time-toolchain.md) | When I change a README, a law, or a compiler, what actually runs to keep everything consistent? |
| 3 | [Design-time authoring](03-design-time-authoring.md) | How does someone author a contract or a template, and what checks it as they do? |
| 4 | [Runtime capabilities](04-runtime-capabilities.md) | Once an instrument is deployed, what runs, and on what data? |
| 5 | [Compiler backends and pluggable surfaces](05-compiler-backends-pluggable-surfaces.md) | How does one shared semantics reach SPARQL, SHACL, SQL, or a surface someone else builds? |

Every diagram is [Mermaid](https://mermaid.js.org/), rendered inline by GitHub and most Markdown
viewers. If a diagram grows too large to read comfortably, split it rather than shrink the text —
a diagram that needs a magnifying glass has stopped doing its job.

These diagrams describe the architecture as documented elsewhere in `docs/architecture/` and
`docs/developer/`; they do not introduce new decisions. Where a capability shown is planned but
not yet built, the diagram says so explicitly (dashed edges, "planned" labels) rather than
blurring the line between what exists and what is designed.
