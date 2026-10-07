---
name: lattice-publication-hygiene
description: What may and may not be published from LATTICE and projects built on it. Use before committing, before opening or describing a pull request, and whenever writing anything that will be public, such as documentation, code comments, commit messages, examples, release notes, environment notes or agent memory kept in the repository.
---

# Publication hygiene

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

The file holds one case-insensitive regular expression per line, with `#` for comments. A line
starting `!` names a path glob to skip, for a file where a term is legitimate. By default the check
reads only the lines being committed (`git diff --cached`), and `--all` scans the tracked tree. A
finding names the file, the line and the pattern's line number in the list, never the pattern.
`mise run hooks:install` adds an optional pre-commit hook that runs it.

## When something slipped through

Remove it in a new commit, and tell the human. Rewriting published history is the human's decision,
never the agent's.
