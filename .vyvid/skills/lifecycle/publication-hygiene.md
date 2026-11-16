LATTICE's repository is public.

## Sources and examples

Substrate and layer documents stay domain-neutral. See [GENAI_CONTRIBUTION.md](https://github.com/nebularis/lattice/blob/main/GENAI_CONTRIBUTION.md) §3 for AI-drafted examples.

## Delivery identifiers stay in working documents

Examples are `LG-1`, a phrase such as "not yet written in LG-2", `AIR-4.2`, `CCS-9b.3`, question identifiers `LG-Q3`, `P7-Q2`, labels `CCS` and `NRS`, and debt and test rows `TD-49` and `LG1-02`.

- **A migrated README cites only published decisions** (ADR-A127). The published-decisions check reports such a citation in a README not yet migrated and fails one in a README migrated to the ADR-A126 layout, which blocks a merge into `main`. On a branch a release note may cite the Proposed decision its change rests on, and before the merge the maintainer accepts that decision, or the note cites the published text that states the rule instead (PDD-16).

- **Check before handing off.** Search what you wrote under `ontology/` for slice, question and debt identifiers and for the word "slice". An extracted section carries the identifier into generated Turtle as well, so fix the README and regenerate.

- **The commit hook refuses the identifiers.** The writing check fails a line a change adds to a layer README that names a register entry, a question, or a slice the developer index defines, in prose or inside a fenced block. It does not read delivery phrasing, so the search above is still yours.

## A decision is named in the Design decisions section and nowhere else

A decision record is the contract between those who build, agents and maintainers, for what is built and how it works. It is not written for a reader of a layer. That reader needs the constraint or the feature a decision gives, and never how it was arrived at (STD-337).

- **Cite a decision only in the README's Design decisions section**, section 5.1 of the ADR-A126 layout, as a link to the record. That section is where a reader who wants the background finds it. A release note may also cite the decision its change rests on.
- **Everywhere else, state the rule as a fact of the layer.** Write "the two documents share one version", never "the two documents share one version (ADR-A131 decision 2)". This holds for the README's other sections, the documents generated from it, a shape's comment and its message, and an example.
- **Never a bare "decision 6".** A number with no record named resolves to nothing, and a reader cannot tell whether it means a bullet of the README or a decision somewhere else.
- **The exception is rare.** Cite a decision outside that section only where the reader is meant to read it, for example because it teaches something about a technology that the layer's own text cannot. Link it, and say why it is worth reading.
- **Existing occurrences are debt, not precedent** (TD-163). Almost every layer README has them. Do not copy them, and do not add to them. Remove them from text you edit, and regenerate where the text is extracted.
- **The commit hook refuses it.** The writing check fails a line a change adds to a layer README that cites a decision outside the Design decisions section and the release notes, in prose or inside a fenced block, and a bare decision number anywhere. `mise exec -- python tools/writing_rules.py ontology/<layer>/README.md` lists what a README still holds.

## AI disclosure

[GENAI_CONTRIBUTION.md](https://github.com/nebularis/lattice/blob/main/GENAI_CONTRIBUTION.md) governs the disclosure rules.

- Substantial (tier A) and assisted (tier B) AI content is disclosed in every commit, with `Generated-by:` and `AI-Content: substantial | assisted` trailers, and in every pull request, with an "AI provenance" section. Review-only use (tier C) needs none.

## The deny-list check

It reads the first of these that exists, and passes when none does:

1. the file named by `LATTICE_DENY_TERMS`
2. `${XDG_CONFIG_HOME:-~/.config}/lattice/deny-terms` on macOS and Linux
3. `%APPDATA%\lattice\deny-terms` on Windows

It is one of the checks the commit hook runs, which `mise run bootstrap` installs (ADR-A133, skill `lattice-mise`).

## The private overlay

A maintainer's private guidance lives outside every repository, at `~/.config/lattice/private/` (`%USERPROFILE%\.config\lattice\private\` on Windows), usually a link to a private checkout. `AGENTS.md` says when it applies. Its content is held to the same rule as the deny-list. It never appears in a repository, a commit or a pull request, in any form.
