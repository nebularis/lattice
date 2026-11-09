<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# `tools/proofs/`

Mechanised Isabelle/HOL theories for the `formal-methods` epic's track E, the prover programme
(ADR-A-FM1: Isabelle/HOL; ADR-A-FM2: this directory as their home).

## Layout

One subdirectory per ontology layer that has a formalised law, named after that layer
(`eligibility/`, …), created only when that layer's first theorem lands. Within a layer's
directory:

| File | Origin | Edited by hand? |
|---|---|---|
| `Kernel.thy` | **generated** from `ontology/<layer>/README.md`'s `isabelle-spec` fenced blocks, via `tools/literate_extract.py --proofs-root tools/proofs` | never. Regenerate it; do not hand-edit it |
| `<Layer>Laws.thy`, `<Layer>.thy`, … | hand-written, importing `Kernel` (or another generated theory) | yes |
| `ROOT` | an Isabelle session definition (one or more sessions: the layer's own theories, a `Defects` session for seeded defects, by the same convention `spikes/formal-prover/isabelle/ROOT` used) | yes |
| `claims/*.json` | one claim record per theorem, conforming to `claim-schema.json` | yes |

Only the **closed datatype** is generated (epic principle E1, `formal-methods.md`): everything
built on top of it (functions, laws, proofs) is hand-written directly in the `.thy` file that
imports it. This is why a generated file and a hand-written file are never the same file: running
the generator again must never silently discard a proof.

**The prelude, `base/`.** One directory is not a layer's. `base/` holds `LatticeBase`, `session LatticeBase = HOL +` with `sessions "HOL-Library"`, whose one theory imports the `HOL-Library` theories the layers' proofs reach for and states no law (ADR-A-FM2's addendum of 2026-11-08). Every layer session parents on it, `session <Layer> = LatticeBase +`, so a library theory is checked once per machine into its heap and no machine builds the `HOL-Library` heap. A layer's `Kernel.thy` keeps importing `Main` or `Complex_Main`, and a library theory is imported by its theorem theories alone. [base/README.md](base/README.md) says why each theory is there.

## Shared infrastructure

`gate.py` and `claim-schema.json` were carried over from `spikes/formal-prover/`, whose own copies were removed on 2026-11-07 so that one gate exists (ADR-A-FM2's addendum), unchanged in
design (PF1 already fixed there: `gate.py`'s digest check excludes any `defects/` path, so it
does not depend on a filesystem's sort order). One gate script serves every layer here, the same
way it served both provers in the spike.

## Building and checking

Native route only: ADR-A-FM1's spike measured this stack on native Isabelle, and this programme has
no Isabelle container image (see the formal-methods status record). Install Isabelle2025-2 once, then
check every layer:

```bash
mise run bootstrap:formal-native-isabelle
mise run check:proofs
```

| Platform | What the install does | Where Isabelle goes |
|---|---|---|
| macOS | downloads the macOS release from the pinned release's archive (`spikes/formal-prover/env/install_native.py`) | `~/.local/share/lattice-formal/Isabelle2025-2.app` |
| Linux, x86_64 or arm64 | downloads the Linux release the same way | `~/.local/share/lattice-formal/Isabelle2025-2` |
| Windows | runs `spikes/formal-prover/env/install-isabelle.ps1`, which unpacks the Windows installer with 7-Zip (`7z` on `PATH`) and initialises Isabelle's bundled Cygwin | `C:/fmx/Isabelle2025-2` |

`LATTICE_FORMAL_ROOT` moves the install directory on every platform. On Windows keep it short, since
long paths fail there. The release includes prebuilt Pure and HOL heaps, so the first check does not
build HOL. A Claude Code cloud session gets Isabelle from `tools/claude-cloud-setup.sh` instead, in
`/opt/Isabelle2025-2`.

`check:proofs` runs each session through `spikes/formal-prover/env/driver.py`, which finds Isabelle
through `FMX_ISABELLE` (its home directory), then the install directory above, then
`/opt/Isabelle2025-2`, then `isabelle` on `PATH`. On Windows it runs Isabelle through the bundled
Cygwin bash. It builds the prelude first and every build runs from `tools/proofs/` with `-d base`, so every build names the prelude the same way and finds the one heap. The first run on a machine builds the prelude's heap from source, about a minute and a half on machine S, and a later run finds it current in seconds. Each `ROOT` states its session's own `timeout`, and nothing passes `-o timeout=` or `-f`, either of which would rebuild the prelude.

To build one session by hand, from `tools/proofs/`, on macOS or Linux with `isabelle` on `PATH`:

```bash
isabelle build -d base -d <layer> -v <SessionName>
python gate.py <layer>
```

On Windows, run the same `isabelle build` inside Isabelle's Cygwin shell (`C:/fmx/Isabelle2025-2/contrib/cygwin/bin/bash.exe --login`), or let `driver.py` do it, from the repository root:

```powershell
python spikes/formal-prover/env/driver.py --route native --workdir tools/proofs isabelle build -d base -d <layer> -v <SessionName>
python tools/proofs/gate.py tools/proofs/<layer>
```

Regenerate a layer's `Kernel.thy` from its README after an `isabelle-spec` block changes, on any
platform:

```bash
mise exec -- python tools/literate_extract.py ontology/<layer>/README.md --layer <layer> --root . \
  --proofs-root tools/proofs --reference-root tools/reference
```

**A layer whose `spec`/`vocab`/`shapes` extraction already drifts from its README** (tracked as
technical debt for Eligibility, TD-16) must not have that drift silently "corrected" as a side
effect of regenerating its `Kernel.thy`: extract only the `@proofs-root@/<layer>/Kernel.thy`
output (`literate_extract.plan()`'s one new key) until TD-16 (or the equivalent for another
layer) is resolved on its own terms.
