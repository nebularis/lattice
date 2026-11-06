<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: VM-8, cloud setup within its limit

**Unit:** [vyvid-migration](../plans/vyvid-migration.md)
**Status record:** [vyvid-migration](../status/vyvid-migration.md)

## Invariant

A slow network or a larger bootstrap must not push a cloud environment's setup past about five minutes, which would stop it being cached, and an agent must have the index from its first question whichever way setup went. A step is never killed, so nothing is left half installed.

## Tests

| ID | Given / When / Then | Level | Invariant | Pass | Kind |
|---|---|---|---|---|---|
| test_vm7_02 | the setup script / read and syntax checked / the domains, then the index's packages, then the index in the background beside the dependencies | L1 | the order | assertion | positive |
| test_vm7_03 | the session hook / run with `CLAUDE_CODE_REMOTE` absent, false and true / the pin is kept only when true, and the hook exits 0 | L1 | a person's machine | assertion | positive and negative |
| test_vm8_01 | nothing deferred / a session starts / only the pin is kept, and nothing is printed | L1 | no cost when setup fitted | assertion | positive |
| test_vm8_02 | two tasks deferred / a session starts / it says so, both run in the background and the file goes | L1 | the rest is finished | assertion | positive |
| test_vm8_03 | a deferred task that fails / a session starts / it stays named | L1 | nothing lost | assertion | negative |
| test_vm8_04 | a step's limit of 150 / the clock at 10, 149, 150 and 400 / it starts below the limit and is deferred at or above it | L1 | the limit | assertion | positive and negative |
| test_vm8_06 | a task that reads all its standard input / the deferred list is finished / every task still runs and the file goes | L1 | nothing lost | assertion | negative |
| test_vm8_05 | `mise.toml` / read / the index's packages need only pip and Вивід, `build:knowledge` starts no second pip, and the dependencies and the index together are bootstrap | L1 | the split | assertion | positive |

`test_vm7_03` was rewritten here, since the hook now runs the script's `--session` rather than `bootstrap:vyvid` itself, and it still proves the same two things.

## One command

```bash
mise run check:vyvid-binding
```

## Artefacts

`tools/claude-cloud-setup.sh`, `.claude/settings.json`, the tasks `bootstrap:index-packages` and `bootstrap:dependencies`, and AGENTS.md's line for a cloud session.

## Results

Sessions on the LATTICE environment, 2026-11-06, with the index built ahead of the dependencies. One session's own setup reached the dependencies at about 127 seconds and finished in 4 minutes. The snapshot's run reached them at 154 seconds, past the limit of 150, so it finished in about 3 minutes 11 seconds and they were deferred. A later session's hook then ran `bootstrap:dependencies` behind the proxy in 111.71 seconds, with no error, and the file went. That session's checkout was newer than the snapshot, and its first `find` rebuilt and ranked in 13.9 seconds while pip was running.

A snapshot without the dependencies costs every session of it about two minutes, so they now run beside the index, and `bootstrap:testing-oxigraph` left setup, since `bootstrap:python` already installs that package.

The next snapshot's run still reached them at 156 seconds, with Isabelle taking 79 seconds that held up every step after it, and it finished in about 3 minutes 47 seconds without them. No step before the end of setup uses Isabelle, so it is now waited for last, which on that run's times would have reached them at about 125 seconds.

## Not covered here

Whether the dependencies now fit in the snapshot, and setup's time with them beside the index. The limits of 150 and 250 seconds are chosen from these few runs, and a list of several tasks deferred for real has run only against a fake `mise`.
