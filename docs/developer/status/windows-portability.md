<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# The build and its tests on Windows, Linux and macOS: status

**Unit ID:** `windows-portability`
**Status:** built 2026-11-07
**Plan:** [windows-portability.md](../plans/windows-portability.md)
**Mode:** autonomous, at the maintainer's request on 2026-11-07. Each slice is committed locally and nothing is pushed. Вивід itself is not changed. The domains `tools`, `lifecycle` and `python` may be.

## Position

| Slice | Deliverable | State | Blocked on |
|---|---|---|---|
| XP-0 | plan, status record, STD-322, STD-323, TD-153 | built 2026-11-07, building 2026-11-07 |  |
| XP-1 | the `mise` skill split between the domain and LATTICE | built 2026-11-07, building 2026-11-07 |  |
| XP-2 | the small fixes: a task dependency, line endings, junctions, the hook's interpreter | built 2026-11-07, building 2026-11-07 |  |
| XP-3 | skips for a missing capability, and `LATTICE_REQUIRE_ALL` | built 2026-11-07, building 2026-11-07 |  |
| XP-4 | `check:vyvid-binding` under Git Bash | built 2026-11-07, building 2026-11-07 |  |
| XP-5 | the shell tasks as Python scripts | built 2026-11-07, building 2026-11-07 |  |
| XP-6 | the portability check | built 2026-11-07, building 2026-11-07 |  |
| XP-7 | ratification, `skills:link` by junction or copy, the directory links page | built 2026-11-07, building 2026-11-07 |  |

**Next action, for the maintainer:** review the [Validation Pack](../validation/windows-portability.md) and [Directory links on Windows](../windows-links.md), and run `mise run --continue-on-error check` on Linux and macOS, which this unit could not.

## Open decisions, for the maintainer

- The `tools` domain's `mise` skill keeps a rule on `run_windows`, rewritten: the maintainer took the PowerShell rule as general, and it now says `$ErrorActionPreference = "SilentlyContinue"` with `exit 0` suits only a clean-up, since as a general rule it reports success whatever failed.
- The domain changes (the `mise` and `windows` skills, NOTE-11 to NOTE-15) are committed in the `tools` domain's checkout, not pushed.

## History

- 2026-11-07: a whole `mise run --continue-on-error check` on Windows, after bootstrap with the editable `vyd`, failed `check:workers`, `check:agent-guidance`, `check:ontology-catalog`, `check:vyvid-binding`, `check:java` and `check:hooks`. Every `vyd`-backed check passed: `check:identifiers`, `check:skills` and `check:knowledge`. `check:mork` had failed first on a fresh checkout, since it reads the Teaching Pack `build:mtp` writes without depending on it. The reasoner's timeout in `check:ontology-catalog` passes alone and is TD-153.
- 2026-11-07: XP-0, the plan, this record, STD-322 and STD-323, STD-190 marked as superseded.
- 2026-11-07: XP-1. The `tools` domain's `mise` skill now says only what holds for any project using `mise`: running tasks, a task's dependency on the build it reads, `--continue-on-error` (its NOTE-11, run here), the per-checkout virtual environment where `mise.toml` creates one, shell activation, and the rules for tasks, with a portable-script rule in the domain's own words. LATTICE's additions take ADR-A29's entry point, its commands and task families, the `.venv` each checkout has, the running process and the build (the studio's jars), Docker, and STD-322's rule. The domain's `other_authorities` default goes, since only LATTICE's additions use it. `check:skills` passes, 15 composed, and the agent-guidance check finds no problem.
- 2026-11-07: XP-2, on Windows.
  - `check:mork` depends on `build:mtp`. 438 passed.
  - The secret reader reads with `newline=""`, so the `\r\n` it strips is the file's own. Before, universal newlines turned every carriage return into a newline first. Its tests write bytes, and a new case shows `\r\r\n` keeps one `\r`.
  - `DocumentSchemaTest` compares with line endings normalised. Trang run here wrote 172 `\r\n` and matched the committed XSD once normalised. `build:document-schema` still writes the platform's line endings, which git's `eol=lf` normalises at commit.
  - `agent_guidance.link` makes a directory junction where Windows refuses a symlink (error 1314), and its test reads a skill through the link. `skills:link` still copies on Windows by default.
  - The installed hook runs the first of `python3`, `python` and `py` that starts, since Windows' `python3` can be a stub offering the Store. `test_gh1_09` asks `os.access(X_OK)` rather than reading a POSIX mode bit, `test_gh1_12` drops `mise` from `PATH` by `shutil.which`, so `mise.exe` too, and `test_vm2_03`'s fake `vyd` is a Python script with a `.cmd` or `sh` launcher, no longer skipped on Windows. `tools/vyd.py` runs the `vyd` that `shutil.which` found.
  - `check:hooks` 48 passed and none skipped, `check:agent-guidance` 9 passed, `check:workers` 210 passed with the `anthropic` test left for XP-3, and `DocumentSchemaTest` passed under Maven.
- 2026-11-07: XP-3.
  - `tools/testing/requires` (CAP-107) is a pytest plugin, loaded through its `pytest11` entry point wherever it is installed. `@pytest.mark.requires("<package>")` skips a test whose package cannot be imported, naming the package, ends the run with a line listing each missing package and its count, and under `LATTICE_REQUIRE_ALL=1` fails the test in setup instead. Bootstrap installs it, the catalogue declares it, and `check:testing-requires` (3 passed) is part of `check`.
  - `test_the_provider_is_chosen_by_the_environment` is split. Choosing the chat-completions provider and the two refusals run everywhere. Choosing the Anthropic provider, which makes the SDK's own client, is `test_the_anthropic_provider_is_chosen_by_the_environment`, marked `requires("anthropic")`. Every assertion of the old test is kept. The other Anthropic tests pass a fake client deliberately and need no package.
  - Here, where the mirror refuses every release of `anthropic`, `check:workers` gives 211 passed and 1 skipped, and its last line names `anthropic (1 test)`. With `LATTICE_REQUIRE_ALL=1` the test is an error.
  - The testing skill's additions state the rule and how to write bytes in a test about line endings. STD-323 is enforced by CAP-107 for packages, and no check yet reads a skip by platform, which XP-6 adds.
- 2026-11-07: XP-4. `tools/claude-cloud-setup.sh` is unchanged, and its tests in `tools/test_vyvid_binding.py` run it under Git Bash on Windows.
  - Every path bash reads, in the fake `mise`, the environment and the `later` probe, goes through `bash_path`, which is the path itself on Linux and macOS and Git Bash's own `cygpath -u` on Windows. The fake `PATH` is then a POSIX list, so `C:` no longer splits it.
  - Every file bash reads is written with `\n`, since `write_text` wrote `\r\n` there, which broke the fake `mise` and put a `\r` into each deferred task's name.
  - On Windows the session's environment also carries `SYSTEMROOT`, `WINDIR`, `TEMP` and `TMP`, since Git Bash mounts `/tmp`, where `cygpath` puts the temporary folder, from `TEMP`.
  - The background process's pid is bash's own, so `kill -0` runs in bash, not as a program of its own, which Windows does not have.
  - `test_vm8_06` finds the fake `mise` in the test's folder rather than by splitting `PATH`. `test_vm8_03` had passed on Windows without the script running at all, and now also asserts the task was tried, so its staying deferred is the script's doing.
  - `check:vyvid-binding` 30 passed, none skipped, on Windows. Not run on Linux or macOS from here.
- 2026-11-07: at the maintainer's request, `VYVID_VERSION` moves to `0.2.15`, Вивід's release for text encodings and pipes, and it is tested against an editable install of that release. `bootstrap:vyvid` reports it installed. `build:knowledge` ran the quanta extractor, and `check:identifiers`, `check:skills` and `check:knowledge` pass. `check:knowledge`, not run after XP-0 and XP-1, found two faults of theirs, both fixed here: STD-178 pointed at the `mise` skill's old section "mise is the one entry point", now "Running tasks", and STD-323 named both CAP-107 and a reason it had no check, which the register refuses. 38 passed.
- 2026-11-07: XP-5.
  - `build:persistence-execution` and `build:minting-vectors` run `tools/persistence_builds.py`, which asks the catalogue for the Persistence module's spec, examples and folder and for the packages root. Under `cmd.exe` their bash scripts ran only `set -e` or `t=$(mktemp -d)` and reported success. Run here under Git Bash and as Python, the two gave the same 401 files of `execution` byte for byte, and the same 22 files of minting `testdata`, with no change to the committed copies. A failed `instantiate` now stops the build with its output, where the script stopped silently, and a failed minting compile stops before the committed files are removed.
  - `clean:python`, `clean:frontend`, `clean:build` and `clean:docs` run `tools/clean.py`, and `clean` no longer has a `run_windows` variant, so the `clean-win` tasks are gone. The script removes what both versions did, keeps a results folder's dotfiles as both did, removes a link or junction and never what it points at, and makes a read-only file writable before removing it. It no longer walks `.venv`, `node_modules` or `.git` for `__pycache__` and `*.egg-info`, which the shell version did. `tools/test_clean.py` (10 passed) runs each area over a scratch tree. `clean:build`, `clean:docs` and `clean:python` ran on this checkout and the editable packages still import from it. `clean:frontend` was not run here, since it removes `node_modules`.
  - Every other `&&` chain is a `run` array, one command per entry, and `check:spc` and `serve:jekyll` set `dir` instead of `cd`. `tools/time_ontology_tests.py` and `tools/validation_replay.py`, which read `check:ontology-catalog`'s run, read an array too, and read `mise.toml` as UTF-8. The tasks touched ran here and passed: `check:spc`, `check:python-root` (both its commands), `check:agent-guidance`, `check:owl-profile`, `check:ontology-versioning`, `check:site-sections`, `check:published-decisions` and `check:tutorial-snippets`.
  - `mise.toml` keeps two `run_windows` variants, the formal-methods installers, which install a platform's own toolchain. CAP-49, CAP-53, STD-193 and the `mise` skill's additions name the scripts. `check:portability` is part of `check`.
- 2026-11-07: XP-6. `tools/portability.py` (CAP-108), run by `check:portability` with its tests.
  - A task's `run` may not hold a multi-line script, a variable, a pipe, a redirect, a glob, `&&`, `||`, `;`, a backtick, `cd` or a POSIX-only command. `run_windows` and `shell` are refused but for the two installers it lists with their reasons.
  - Under `tools/`, `workers/`, `packages/` and `benchmark/`, a text read, write or subprocess call with no encoding is counted per file. The 267 calls in 79 files that predate it are `tools/portability-baseline.txt` and TD-154, a file's count may only go down, and `--lower-baseline` lowers counts and never adds or raises one.
  - A `skipif` on `os.name`, `sys.platform` or `platform.system()` fails. None is left.
  - STD-322 is enforced by CAP-108, and STD-323 by CAP-107 and CAP-108. The `mise` skill's additions name the check.
  - `check:portability` 25 passed and no problem on this tree. Adversarial probe: with the `&&` rule taken out in memory, `task_problems` let `python a.py && python b.py` through, which the parametrised test of each shell feature refuses.
- 2026-11-07: handoff. A whole `mise run --continue-on-error check` on Windows passed every task but `check:workers`, which read the Teaching Pack before `build:mtp` wrote it, the second task found with that missing dependency. It now depends on `build:mtp`, and alone after the output was removed gave 211 passed and 1 skipped, the skip naming `anthropic`. TD-153's timeout did not recur. The tools domain gains NOTE-12, Git Bash's `/tmp` mounted from `TEMP`, and NOTE-13, `subprocess` finding only `.exe` on Windows. The Validation Pack is written. Not run: Linux, macOS, `clean:frontend` on this checkout, and the suites `check` leaves out.
- 2026-11-07: XP-7, at the maintainer's word.
  - STD-322, STD-323 and STD-190's supersession are ratified.
  - The maintainer asked whether junctions are available on every Windows likely to be met, whether permissions govern them and whether a policy can disable them, and chose a junction with a copy as the fallback. `agent_guidance.link` makes a symbolic link, else a junction where Windows refuses the symbolic link with error 1314, else a copy marked `.lattice-copy`, per skill, and prints which. It makes the junction with Python's `_winapi.CreateJunction`, so `cmd.exe` is not needed, and runs `mklink /J` only on an interpreter without it. Windows no longer copies by default. `--copy` still forces a copy.
  - Tests: a refused symbolic link becomes a junction, and a skill that cannot be linked is copied and linked again on the next run, both by refusing the link in the test rather than skipping on a platform. `check:agent-guidance` 11 passed. `skills:link` into a scratch folder made a junction for each of the 15 skills here, unelevated.
  - [Directory links on Windows](../windows-links.md) explains the four ways to make a directory appear twice, how a junction resolves, its limits, who may make one, what a policy or security tool can do, how the tooling chooses, and how to inspect and remove one. Its claims cite Microsoft's documentation or were run on this machine, Windows 11 Enterprise build 26200, and it says which. Redirection Guard and ReFS are stated as not tested.
  - Probed here, in scratch folders: a symbolic link refused with 1314 and a junction made, a relative target stored as absolute, a dangling junction that `exists()` denies and `is_junction()` finds, `shutil.rmtree` refusing a junction and not entering one, and `rmdir`, `rd /s /q`, `Remove-Item -Recurse -Force` and `.Delete()` each removing a junction and keeping its target's file. Symbolic link evaluation reports the defaults.
  - The `tools` domain's `windows` skill gains a section on directory links, from NOTE-14 and NOTE-15, and LATTICE's additions point at the page.
- 2026-11-07: at the maintainer's request, the `agent-skills` sketch is marked historical, with a note naming what has changed since: fifteen composed skills, `skills:link` linking on Windows, tasks as Python scripts, and the hooks installed by bootstrap. The two documents that link it, ADR-A117's Unit line and the archived coordination index, say so. The knowledge index holds no entry from the sketch and no other entry stating that `skills:link` copies on Windows, asked by `vyd sparql` over every named graph.
