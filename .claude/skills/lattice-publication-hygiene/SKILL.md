---
name: lattice-publication-hygiene
description: What may and may not be published from LATTICE and projects built on it. Use before committing, before opening or describing a pull request, and whenever writing anything that will be public, such as documentation, code comments, commit messages, examples, release notes, environment notes or agent memory kept in the repository.
---

# Publication hygiene

Ask the knowledge index first, as AGENTS.md's "Asking the knowledge index" says, with `mise run graph:ask -- find <the task in your own words>` and every facet value that fits the task at hand, then `read` each entry that answers. Read each row's flags and the line under it, where an entry's boundary, its successor and the debt against it are named. This skill's tasks span the activities documentation, licensing-and-ip, secrets-management and privacy-engineering, with the qualities confidentiality and privacy, and a task often needs several of them, named together and separated by commas. `--activity`, `--quality` and `--tech` raise matching entries and hide none, while `--kind` filters exactly, so leave `--kind` off unless only one kind of entry will do. The index finds the rules this skill does not mention, and the entries related to the ones it does.

LATTICE's repository is public, and so is everything it publishes. Anything committed stays in its
history, so the time to catch a problem is before the commit.

## Never publish

- names or details that identify a person or a client, beyond what the project itself names
- credentials, tokens, keys, private hostnames, internal URLs, mirror or index addresses, private
  repository paths
- notes true of one machine or one person's setup, such as local paths, installed versions,
  network behaviour or remotes. Keep them in that person's own configuration or agent memory
- text from a confidential source, quoted or close to it

## Sources and examples

- **Anonymise a real source** before it enters a sketch or an example. Replace organisations,
  people, places and reference numbers with neutral placeholders, and keep what the example needs to
  show.
- **Substrate and layer documents stay domain-neutral.** Their examples come from several domains,
  and never cite a downstream project. Sketches and plans may name downstream projects.
- **Generated content drifts toward the domains a model has seen most.** Check AI-drafted
  examples for it, as [GENAI_CONTRIBUTION.md](https://github.com/nebularis/lattice/blob/main/GENAI_CONTRIBUTION.md) §3 asks.
- **Placeholder IRIs use `example.org`**, never a real organisation's domain.

## Delivery identifiers stay in working documents

How work was planned and delivered is not part of what a layer means. Production text never names it.
Production text is everything under `ontology/` (READMEs, the documents generated from them, shapes,
examples and the comments in them), the site's pages, and published ADRs outside their Provenance
section (ADR-A127 decision 4, ADR-A126 decision 11).

- **Never in production text:** slice and phase identifiers (`LG-1`, `AIR-4.2`, `C9b3`), question
  identifiers (`LG-Q3`, `P7-Q2`), unit, epic and plan names used as labels (`CCS`, `NRS`), technical
  debt and test row identifiers (`TD-49`, `LG1-02`), and delivery phrasing such as "this slice", "the
  plan's brief", "flagged at", "at verification", "not yet written in LG-2" or "open for the maintainer".
- **Say what instead.** State the fact the identifier stood for. A term not yet specified is "not yet
  specified". A rule decided in an ADR cites the ADR. A modelling choice is stated as the choice, with
  its reason. A release note says what changed, never which slice changed it.
- **A migrated README cites only published decisions** (ADR-A127). The published-decisions check reports such a citation in a README not yet migrated and fails one in a README migrated to the ADR-A126 layout, which blocks a merge into `main`. On a branch a release note may cite the Proposed decision its change rests on, and before the merge the maintainer accepts that decision, or the note cites the published text that states the rule instead (PDD-16).
- **Working documents keep them.** Sketches, plans, status records, review requests, Validation Packs,
  the developer index, commit messages and agent memory use delivery identifiers freely, since that is
  what they are for.
- **Existing occurrences are debt, not precedent.** Some older READMEs and release notes still name
  slices. Do not copy them. Remove them when you next edit that text.
- **Check before handing off.** Search what you wrote under `ontology/` for slice, question and debt
  identifiers and for the word "slice". An extracted section carries the identifier into generated
  Turtle as well, so fix the README and regenerate.

## AI disclosure

If an AI agent is making commits, then [GENAI_CONTRIBUTION.md](https://github.com/nebularis/lattice/blob/main/GENAI_CONTRIBUTION.md) governs the disclosure rules. In short:

- Substantial (tier A) and assisted (tier B) AI content is disclosed in every commit, with
  `Generated-by:` and `AI-Content: substantial | assisted` trailers, and in every pull request, with
  an "AI provenance" section. Review-only use (tier C) needs none.
- The trailer must survive a squash merge.
- AI-drafted text published under the project's name is reviewed by a person first, or labelled as
  AI-generated.

If a human is making the commit then disclosure is their responsibility.

## The deny-list check

`mise run check:deny-terms` checks text about to be committed against a personal list of terms,
which is never published. It reads the first of these that exists, and passes when none does:

1. the file named by `LATTICE_DENY_TERMS`
2. `${XDG_CONFIG_HOME:-~/.config}/lattice/deny-terms` on macOS and Linux
3. `%APPDATA%\lattice\deny-terms` on Windows

The file holds one case-insensitive regular expression per line, with `#` for comments. A line starting `!` names a path glob to skip, for a file where a term is legitimate. By default the check reads only the lines being committed (`git diff --cached`), and `--all` scans the tracked tree. A finding names the file, the line and the pattern's line number in the list, never the pattern. It is one of the checks the commit hook runs, which `mise run bootstrap` installs (ADR-A133, skill `lattice-toolchain`).

## The private overlay

A maintainer's private guidance lives outside every repository, at `~/.config/lattice/private/`
(`%USERPROFILE%\.config\lattice\private\` on Windows), usually a link to a private checkout.
`AGENTS.md` says when it applies. Its content is held to the same rule as the deny-list. It never
appears in a repository, a commit or a pull request, in any form.

## When something slipped through

Remove it in a new commit, and tell the maintainer. Rewriting published history is the maintainer's decision,
never the agent's.
