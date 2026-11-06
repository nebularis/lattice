<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: VM-8, cloud setup within its limit

**Unit:** [vyvid-migration](../plans/vyvid-migration.md)
**Status record:** [vyvid-migration](../status/vyvid-migration.md)

## Invariant

A slow network or a larger bootstrap must not push a cloud environment's setup past about five minutes, which would stop it being cached, and an agent must have the index from its first question whichever way setup went. A step is never killed, so nothing is left half installed.

## Tests

| ID | Given / When / Then | Level | Invariant | Pass | Kind |
|---|---|---|---|---|---|
| test_vm7_02 | the setup script / read and syntax checked / the domains, then the index, then the dependencies | L1 | the order | assertion | positive |
| test_vm7_03 | the session hook / run with `CLAUDE_CODE_REMOTE` absent, false and true / the pin is kept only when true, and the hook exits 0 | L1 | a person's machine | assertion | positive and negative |
| test_vm8_01 | nothing deferred / a session starts / only the pin is kept, and nothing is printed | L1 | no cost when setup fitted | assertion | positive |
| test_vm8_02 | two tasks deferred / a session starts / it says so, both run in the background and the file goes | L1 | the rest is finished | assertion | positive |
| test_vm8_03 | a deferred task that fails / a session starts / it stays named | L1 | nothing lost | assertion | negative |
| test_vm8_04 | a step's limit of 150 / the clock at 10, 149, 150 and 400 / it starts below the limit and is deferred at or above it | L1 | the limit | assertion | positive and negative |
| test_vm8_06 | a task that reads all its standard input / the deferred list is finished / every task still runs and the file goes | L1 | nothing lost | assertion | negative |
| test_vm8_05 | `mise.toml` / read / the index needs only pip and Вивід, and the dependencies and the index together are bootstrap | L1 | the split | assertion | positive |

`test_vm7_03` was rewritten here, since the hook now runs the script's `--session` rather than `bootstrap:vyvid` itself, and it still proves the same two things.

## One command

```bash
mise run check:vyvid-binding
```

## Artefacts

`tools/claude-cloud-setup.sh`, `.claude/settings.json`, the tasks `bootstrap:index` and `bootstrap:dependencies`, and AGENTS.md's line for a cloud session.

## Not covered here

The limits of 150 and 250 seconds are chosen from one session, where the dependencies took about 112 seconds and the last two steps about 22. A real session on the LATTICE environment must show `bootstrap:index` under Python 3.14, and `lattice-quanta` running with only the two packages. Deferral itself has been run only against a fake `mise`, since a real setup rarely reaches the limit. Yarn and pip behind the session's proxy in the background run are unproven.
