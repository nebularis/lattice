<!-- SPDX-License-Identifier: MPL-2.0 -->

# `tools/models/`

Design-time models for the formal-methods epic's track C (`docs/developer/plans/formal-methods-track-c.md`).
Each subdirectory holds one checked model, in whichever relational or SMT language fits the
question it answers (Alloy for relational modelling, Z3/cvc5-driven Python for numeric
satisfiability — the epic plan's own C2/C3 split, not a per-directory choice).

A model here is evidence for an ADR, not code that ships. It is not a mechanised proof
(`tools/proofs/`, Isabelle, ADR-A-FM2) — a different question (does a design admit the claimed
properties, checked over generated instances up to a stated scope, not proved as a theorem for
every instance) and a different artefact (a `run`/`check` result and a recommendation).

No toolchain binary is tracked here. Alloy Analyzer is a single MIT-licensed JAR, run from wherever
it is installed locally (this track installed it under `C:\fmx\alloy\alloy.jar` on the native-route
convention track D and E's toolchains already use — see `tools/proofs/README.md`).

## Subdirectories

- `vocabulary-scheme-composition/` — track C2: binding resolution with scheme composition, ahead
  of CCS's HQ-4 and insurml-alignment's IMA-D4a.
