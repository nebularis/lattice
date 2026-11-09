<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# `tools/proofs/base/`, the prelude

`LatticeBase` is the one session under `tools/proofs/` that is not a layer's ([ADR-A-FM2](../../../docs/architecture/decisions/ADR-A-FM2-formal-methods-theory-home.md)'s addendum of 2026-11-08). Its one theory, `Prelude.thy`, imports the `HOL-Library` theories the layers' proofs reach for, and nothing else. It states no law and carries no claim, so the gate reports it as having nothing to gate.

Every layer session parents on it, `session <Layer> = LatticeBase +`. A library theory is then checked once per machine, into this session's heap, no machine builds the `HOL-Library` heap, and a session kept outside the repository has a public heap to parent on. A layer's generated `Kernel.thy` keeps importing `Main` or `Complex_Main`, and a library theory is imported by the layer's theorem theories alone.

**Why each theory is here.** The [HOL sessions survey](../../../docs/developer/sketches/hol-sessions-survey.md) §7 names each of the nineteen, the construct we use from it and the proof area it is for, and §7 also lists the theories considered and not imported. Adding a theory is one import in `Prelude.thy` and a row in that table, reviewed once.

**How it is built.** `mise run check:proofs` builds `LatticeBase` before any layer's session, with `-b` so its heap is saved and the layers' builds find it, and runs every build from `tools/proofs/` with `-d base` beside the layer's own directory. `isabelle build` builds the heap on the first run that needs it and rebuilds it when its sources change, by their digests, so nothing else pins it and `-f` is never passed. `bootstrap` never builds it (STD-324). Its first build on machine S took about a minute and a half. To build it alone, from the repository root:

```bash
python spikes/formal-prover/env/driver.py --route native --workdir tools/proofs isabelle build -b -d base LatticeBase
```

Each session's `ROOT` states its own `timeout`, the prelude's wide enough for its first build from source and a layer's narrow, so a looping proof fails fast. A `-o timeout=` on the command line would apply to every session, the prelude included, change its options and so force its heap to be rebuilt. A build that names the prelude's directory another way, `-d .` from inside it, was also not taken for the same session on machine S, which is why every build runs from `tools/proofs/`.
