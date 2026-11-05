LATTICE's repository is public.

## Sources and examples

Substrate and layer documents stay domain-neutral. See [GENAI_CONTRIBUTION.md](https://github.com/nebularis/lattice/blob/main/GENAI_CONTRIBUTION.md) §3 for AI-drafted examples.

## Delivery identifiers stay in working documents

Examples are `LG-1`, a phrase such as "not yet written in LG-2", `AIR-4.2`, `CCS-9b.3`, question identifiers `LG-Q3`, `P7-Q2`, labels `CCS` and `NRS`, and debt and test rows `TD-49` and `LG1-02`.

- **A migrated README cites only published decisions** (ADR-A127). The published-decisions check reports such a citation in a README not yet migrated and fails one in a README migrated to the ADR-A126 layout, which blocks a merge into `main`. On a branch a release note may cite the Proposed decision its change rests on, and before the merge the maintainer accepts that decision, or the note cites the published text that states the rule instead (PDD-16).

- **Check before handing off.** Search what you wrote under `ontology/` for slice, question and debt
  identifiers and for the word "slice". An extracted section carries the identifier into generated
  Turtle as well, so fix the README and regenerate.

## AI disclosure

[GENAI_CONTRIBUTION.md](https://github.com/nebularis/lattice/blob/main/GENAI_CONTRIBUTION.md) governs the disclosure rules.

- Substantial (tier A) and assisted (tier B) AI content is disclosed in every commit, with
  `Generated-by:` and `AI-Content: substantial | assisted` trailers, and in every pull request, with
  an "AI provenance" section. Review-only use (tier C) needs none.

## The deny-list check

It reads the first of these that exists, and passes when none does:

1. the file named by `LATTICE_DENY_TERMS`
2. `${XDG_CONFIG_HOME:-~/.config}/lattice/deny-terms` on macOS and Linux
3. `%APPDATA%\lattice\deny-terms` on Windows

It is one of the checks the commit hook runs, which `mise run bootstrap` installs (ADR-A133, skill `lattice-toolchain`).

## The private overlay

A maintainer's private guidance lives outside every repository, at `~/.config/lattice/private/`
(`%USERPROFILE%\.config\lattice\private\` on Windows), usually a link to a private checkout.
`AGENTS.md` says when it applies. Its content is held to the same rule as the deny-list. It never
appears in a repository, a commit or a pull request, in any form.
