<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: VM-7, cloud sessions

**Unit:** [vyvid-migration](../plans/vyvid-migration.md)
**Status record:** [vyvid-migration](../status/vyvid-migration.md)

## Invariant

A cloud session has no terminal, so what a person states in the environment's pasted setup script must give it this repository's trust and Вивід's domains, the domains must exist before the index is built, and nothing changes on a person's own machine ([ADR-A152](../../architecture/decisions/ADR-A152-vyvid-adoption.md), its addendum of 2026-11-06).

## Tests

| ID | Given / When / Then | Level | Invariant | Pass | Kind |
|---|---|---|---|---|---|
| test_vm7_01 | the lines the script's header says to paste / run on an empty home / the configuration lists this repository and `vyvid.toml`'s domains, each `own` | L1 | the grant | assertion | positive |
| test_vm7_02 | the setup script / read and syntax checked / the domains step comes before bootstrap | L1 | the order | assertion | positive |
| test_vm7_03 | the session hook / run with `CLAUDE_CODE_REMOTE` absent, false and true / `bootstrap:vyvid` runs only when true, and the hook exits 0 | L1 | a person's machine | assertion | positive and negative |

## One command

```bash
mise run check:vyvid-binding
```

## Artefacts

`tools/claude-cloud-setup.sh`, its header's pasted lines and hosts, `.claude/settings.json`, `mise.toml`'s `VYVID_VERSION`.

## Not covered here

The script itself has not run from this change. Its parts were measured on another cloud environment on 2026-11-06 with no `mise`, so what needs a real session on the LATTICE environment is `bootstrap:vyvid` under the linked Python 3.14, the `lattice-quanta` extractor with `mise` present, setup staying under about five minutes with the embedding in it, a rebuild on a checkout newer than the snapshot, and the hook.
