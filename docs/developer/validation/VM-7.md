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

## Results

A first session on the LATTICE environment, 2026-11-06, at `3ef90a2`. `vyd` 0.2.13 installed and the five domains cloned. The project was trusted through `trusted_repositories`, `vyd check skills` passed with 15 composed, `lattice-quanta` ran, and two `find`s ranked in about 1.9 seconds each. That session's own setup ran from about 11:29:33 to 11:33:09, about 3 minutes 36 seconds against the limit of about five, of which `mise run bootstrap` took 162 seconds and its knowledge step 49.66.

## Not covered here

Reuse of the snapshot, a rebuild on a checkout newer than the snapshot, and the hook's effect when a branch pins a newer `vyd`.
