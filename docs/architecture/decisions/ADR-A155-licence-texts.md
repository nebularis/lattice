<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A155: The texts of the licences the repository's files name

**Status:** Proposed
**Date:** 2026-11-25 (proposed)
**Related:** [ADR-A121](ADR-A121-repository-catalogue.md) (the catalogue declares each root), [ADR-A77](ADR-A77-repository-topology-and-documentation-governance.md) (a new root needs an accepted decision)
**Unit:** [`studio-visual-authoring`](../../developer/plans/studio-visual-authoring.md)

## Context

Each file states its licence with an SPDX identifier, in a header or, for a file that cannot carry one, in `REUSE.toml`. The tracked files name `MPL-2.0` and `CC-BY-SA-4.0`, `vyvid.toml` names `MIT`, and `REUSE.toml` gives the copies of OASIS LegalRuleML files `LicenseRef-OASIS-IPR-Policy`, an identifier of our own since the OASIS notice has no SPDX identifier. The texts of the first two are in `LICENSE` and `LICENSE-DOCS.md`, in forms written for a reader, and the other two have no text in the repository at all. The REUSE specification, which `REUSE.toml` follows, expects the text of every licence a file names in a root directory `LICENSES/`, one file for each identifier, named `<identifier>.txt`, so a tool can tell from the repository alone which terms govern a file. Without it, a copy of a third-party file names a licence that a reader of the repository cannot find, and a check such as `reuse lint` fails.

## Decision

1. **A root directory `LICENSES/`**, holding one file for each licence identifier a tracked file's header or `REUSE.toml` names, named `<identifier>.txt` and holding that licence's text and nothing else. The catalogue declares it as a root.
2. **The texts of SPDX licences are SPDX's**, copied from the SPDX License List's published texts, unmodified, so `MIT.txt` keeps its placeholders.
3. **A licence of our own naming is `LicenseRef-<name>.txt`.** `LicenseRef-OASIS-IPR-Policy.txt` holds the OASIS copyright notice and the permissions it grants, as the OASIS specification states them. The OASIS IPR Policy it refers to is not copied, since the notice names where it is found.
4. **`LICENSE` and `LICENSE-DOCS.md` stay** at the root as the statement a reader looks for first, saying which licence covers which part of the repository. They are not licence texts in this decision's sense.
5. **A check holds it.** `mise run check:licences` fails where a tracked file or `REUSE.toml` names an identifier with no text in `LICENSES/`, and where `LICENSES/` holds a text no file names, and it runs in `mise run check`.

## Consequences

A new licence enters the repository with its text, since the check refuses a header that names one without it. A copy of a third-party file under terms of its own needs a `LicenseRef-` identifier and its text, as the OASIS copies have. The repository can be checked with `reuse lint`, which is not yet part of any task. `MIT` is named by one file, and the check keeps its text for as long as it is.

## Provenance

Proposed on 2026-11-25, when the copies of OASIS LegalRuleML files gave the repository a licence it held no text for, and the maintainer asked for the directory and its files.
