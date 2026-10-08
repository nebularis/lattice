<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Formal prover spike: macOS reproduction and portability findings

**Unit:** [formal-methods](../status/formal-methods.md), track D
**Report:** [formal-prover-experiment.md](formal-prover-experiment.md)
**Branch checked:** `fm/phase-0-prover-spike`, unmodified
**Date:** 2026-10-06

The spike was built on Windows and reproduced on macOS (Apple silicon) with native installs only.
The image route and the `mise` tasks were not exercised. Nothing on the branch was changed.

## 1. Environment

| Tool | Version |
|---|---|
| Rocq | 9.3.0, compiled with OCaml 5.3.0, opam switch `fm` under `$HOME/fmx/opamroot` |
| Isabelle | Isabelle2025-2 macOS bundle, Poly/ML `arm64_32-darwin`, with `ISABELLE_HOME_USER` under `.build/formal/isabelle-home` |
| GHC | from ghcup |

## 2. Result

| Check | Result |
|---|---|
| Rocq, seven theories compiled in dependency order | Pass. Both audit files print "Closed under the global context" for every theorem |
| Rocq defects S1 to S5 | All compile |
| Rocq OCaml extraction, regenerated in a scratch directory | Identical to the tracked `extracted_kernel.ml`. All 15 fixtures match |
| Isabelle session `FormalMethodsSpike` | Pass |
| Isabelle session `FormalMethodsSpikeDefects` | Pass |
| Isabelle-exported OCaml and Haskell | All 15 fixtures match in each |
| `check_s4.py` and `check_s5.py`, both tracks | Pass |
| `gate.py` on `rocq/` and `isabelle/` | **Fail**, see PF1 |

## 3. Findings to fix

### PF1. `gate.py` fails on a case-sensitive filesystem

`extract_statements` reads the GATE markers from every `.v` and `.thy` file under the track
directory, including `defects/`, and the last file read for a subject wins. `defects/S5_weaker_restatement`
carries a deliberately weakened `TA1` marker.

- On Windows, `sorted()` over paths is case-insensitive, so `defects/...` sorts before `Kernel.*` and
  the real statement is read last.
- On macOS, ordering is case-sensitive, so `Kernel.*` sorts before `defects/...` and the weakened
  statement is read last. The recomputed TA1 digest then differs from the committed claim and the gate
  reports an unreviewed restatement.

Evidence. The digests of the real `Kernel.v` and `Kernel.thy` equal the committed TA1 claims. Run over a
copy with `defects/` excluded, the gate passes for both tracks.

Fix. Skip any path with a `defects` component in `extract_statements`, as `scan_for_banned` already
does. Keying statements by file would also work.

### PF2. The native `mise` tasks and driver route are Windows only

| Item | Problem |
|---|---|
| `bootstrap:formal-native-rocq` and `bootstrap:formal-native-isabelle` | Defined with `run_windows` only. Elsewhere they print a notice and install nothing |
| `.local/formal-methods-spike/scripts/*.ps1` | The Windows tasks call these. They are git-ignored, so a fresh checkout has no installer at all |
| `driver.py`, `native_rocq` and `native_isabelle` | Hard-code PowerShell, `%LOCALAPPDATA%`, `C:/fmx` and Cygwin paths. `check:formal-smoke -- --route native` cannot work on macOS or Linux |
| `env/env-common.ps1`, `env/smoke.ps1`, `env/probe-network.ps1` | PowerShell only. `probe_network.py` is the portable equivalent |

Needed. A POSIX branch for both native tasks and for the driver's native route, with the
toolchain root taken from `LATTICE_FORMAL_ROOT` and the opam root from `OPAMROOT`. The Isabelle
entry point on macOS is `<root>/Isabelle2025-2.app/bin/isabelle`.

### PF3. No task runs the proofs

No `mise` task compiles the Rocq theories or builds the Isabelle sessions, and `gate.py` has no task.
`check:formal-smoke` only confirms the tools start. The sequences below were reconstructed by hand
and worked on macOS. They are candidates for tasks.

| Step | Command, from the stated directory |
|---|---|
| Rocq theories | In `spikes/formal-prover/rocq`: `rocq compile X.v` for Kernel, Eligibility, Adequacy, CheckKernel, CheckEligibility, Reading, Interface, in that order |
| Rocq defects | In `spikes/formal-prover/rocq`: `rocq compile -Q . "" defects/S<n>_<name>.v` for each of the five files |
| Rocq extraction | Compile Kernel, Eligibility and Extraction in a scratch directory, then `ocamlfind ocamlopt extracted_kernel.mli extracted_kernel.ml extraction_driver.ml -o drv` |
| Isabelle | In `spikes/formal-prover/isabelle`, with `ISABELLE_HOME_USER` set: `isabelle build -v -d . FormalMethodsSpike`, then the same for `FormalMethodsSpikeDefects` |
| Exported OCaml | `ocamlfind ocamlopt formal_methods_kernel.ml export_driver.ml -o drv` in a scratch directory |
| Exported Haskell | `ghc -O0 Formal_Methods_Kernel.hs ExportDriver.hs -o drv` in a scratch directory |
| Gate and defect checks | `python spikes/formal-prover/gate.py <track-dir>` and the four `check_s4.py` and `check_s5.py` scripts |

Compiling in place leaves git-ignored `*.vo` and `*.glob` files beside the Rocq sources. Scratch
directories under `.build/formal/out/` keep the extraction and export builds out of the tracked tree.
Isabelle's `export_code` output was not regenerated and compared against the tracked files, so only the
tracked copies were checked.

### PF4. Smaller items

- `build_images.py` stages `docker/<image>/extra-ca.crt` and removes it afterwards. A stray empty
  `spikes/formal-prover/env/docker/ghc-wasm/extra-ca.crt` was left untracked here. Add it to
  `.gitignore`, or make the script clean up on failure too.
- The D4 report states that neither track used the image route. The portable route was not exercised on
  macOS either, so the image route remains unverified on this host.
- `gate.py` documents `(* GATE:BEGIN ... *)` markers shared by both languages. Nothing else in it is
  platform specific.

## 4. Install notes for a fresh macOS host

- Rocq through opam needs the switch created without a trailing shell comment on the same line. An
  interactive zsh passes `# ...` to opam as an argument.
- The `rocq-released` repository is added per switch by default. That is enough for one switch.
- Both toolchains sit outside the repository. Export `OPAMROOT` and run `eval "$(opam env --switch=fm)"`
  in every new shell, since `opam init --no-setup` edits no profile.
- The Isabelle macOS bundle needs `xattr -dr com.apple.quarantine` on first use.
