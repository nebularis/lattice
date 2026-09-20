<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# AI-Assisted Contributions to LATTICE

## Position

Using generative AI tooling to help draft ontology content, documentation, or reference-implementation code is a legitimate way to contribute to LATTICE. This document doesn't govern whether you may use such tooling — you may. It governs what a contribution has to disclose when you do, and what that disclosure obligates you and the project to. The short version: label it clearly, and be able to stand behind it.

This policy draws on the [Apache Software Foundation's guidance on AI-generated contributions](https://www.apache.org/legal/generative-tooling.html), adapted to LATTICE's licensing model, which has no Contributor License Agreement to lean on the way ASF projects do.

---

## Scope

This applies to any contribution — ontology artefacts (`.ttl`), documentation and specifications (`.md`), reference-implementation code (`tools/`), and diagrams or other images added anywhere in the repository — where a generative AI tool produced content that appears, in whole or in part, in what you're submitting. It applies regardless of which layer or directory the change touches.

It does not apply to using an AI tool purely to review, critique, or test content you authored yourself, where no AI-generated material ends up in the contribution. See [Disclosure tiers](#disclosure-what-is-required) below for where that line sits in practice.

---

## The legal basis, and why LATTICE has no CLA to lean on

LATTICE has no Contributor License Agreement. Most large open-source foundations use one to obtain an explicit, signed representation from every contributor that their submission is original or properly licensed. LATTICE doesn't ask for a signature — the representation instead comes from the licence governing the file itself, the same way it already does for every other contribution, AI-assisted or not.

For every `.ttl` file and everything under `tools/`, [MPL 2.0](../LICENSE) §2.5 already states it plainly:

> Each Contributor represents that the Contributor believes its Contributions are its original creation(s) or it has sufficient rights to grant the rights to its Contributions conveyed by this License.

That representation attaches automatically the moment you open a pull request touching an MPL-governed file. There's no separate form. There's also no exception in it for content a tool helped you produce — the representation is exactly as real, and exactly as much yours to make honestly, whether you typed every character or an AI tool drafted the first version and you shaped it into something you're willing to stand behind.

CC BY-SA 4.0's legal code, which governs every `.md` file, doesn't carry an equivalent explicit representation clause. For documentation, the same standard applies as a project norm rather than as licence text: opening a PR that touches a `.md` file is understood to carry the same representation MPL states outright for ontology files.

---

## Before you submit: three checks

### 1. Check the tool's terms of use

The terms governing the specific account or plan you used need to grant you rights broad enough to submit the output under MPL 2.0 (for `.ttl` and `tools/` content) or CC BY-SA 4.0 (for documentation) — ownership of the output, or a licence wide enough to sublicense it on those terms. Find the clause that actually addresses output ownership or use rights; don't infer it from the tool's marketing material. Consumer-tier and enterprise/API-tier terms for the same tool sometimes differ on exactly this point, so check the terms attached to the account you actually used.

Don't second-guess a vendor's terms of use beyond what they say. You're bound by the whole of the stated terms, and you're not expected to look past the text for further interpretation.

### 2. Confirm at least one of the following

- **The output isn't copyrightable subject matter**, and wouldn't be even if a human had produced it. Treat this alone as thin ground — whether purely AI-generated output is copyrightable at all is currently unsettled and varies by jurisdiction. If a purely AI-generated portion turns out to carry no copyright, it doesn't break anything (it sits in an MPL- or CC-BY-SA-governed file the way public-domain material might), but relying on this condition alone ties your contribution to a legal question nobody has answered yet. Prefer one of the two conditions below where you can.
- **No third-party material is included in the output.**
- **Any third-party material that is included is used under a licence compatible with the governing licence of the file it's going into**, and you've complied with that licence's terms (attribution and so on).

Where the tool you're using offers a feature that flags output similar to its training data, use it — that's the most direct way to get reasonable certainty on the second or third condition. Most tools don't currently offer this, and code-similarity scanning only catches matches against known open-source material, so full certainty won't always be available. Use what's available; note in your PR description if you couldn't check further.

LATTICE doesn't currently maintain a list of licences it treats as compatible with MPL 2.0 or CC BY-SA 4.0 for included third-party material. That's a gap worth closing before this condition gets exercised in practice rather than after — flag it to the maintainers if you hit it.

### 3. Confirm the content holds the line on domain neutrality

This one is specific to LATTICE and has no ASF equivalent, because it isn't a copyright concern — it's an architectural one. If you're touching an ontology layer (`spec/`, `shapes/`, `vocab/`, `projection/` in any of `ontology/foundation/`, `ontology/vocabulary/`, `ontology/party/`, `ontology/instrument/`, `ontology/eligibility/`, `ontology/behaviour/`), the content has to clear the same generality bar as anything a person drafts by hand: nothing in a layer's specification should require knowing what industry or domain is consuming it, and `vocab/` in particular holds mechanism-intrinsic enumerations only, never business or domain vocabulary (see [CONTRIBUTING.md](../CONTRIBUTING.md#where-new-content-belongs)).

Generative models are pattern-completion engines. The more strongly a domain is represented in a model's training data, the more an unprompted continuation tends to drift toward that domain's shape — a model asked to draft an example `Obligation` will reach for an insurance premium or a loan repayment before it reaches for something genuinely neutral, because those are the patterns most heavily represented in what it's seen. That drift is worth watching for specifically, the same way it was watched for when this project's own worked examples were built by hand across employment, lending, SaaS, and clinical-trial domains precisely to test for it. AI-assisted content isn't exempt from that test; if anything it's the content most likely to need it.

---

## Disclosure: what is required

Not every use of an AI tool carries the same weight, and the disclosure obligation scales with it.

**Tier A — Substantial.** The tool produced most or all of an initial draft; a human reviewed it and made non-trivial edits before submission. This is where most meaningful AI involvement in a contribution will sit.

**Tier B — Assisted.** The tool acted as an advanced completion or refactoring aid on content a human was already actively authoring — line completions, phrasing suggestions, boilerplate expansion, mechanical restructuring of something already substantively written.

**Tier C — Reviewed only.** The tool was used to review, critique, explain, or test content, but produced no content that appears in the contribution itself.

Tier C needs no disclosure — there's no AI-authored material in the submission to disclose. **Tiers A and B must be disclosed, in both of the following places, for every commit and every pull request they appear in.** This isn't a recommendation; it's a condition of the contribution, in the same sense the SPDX header is.

### Commit trailer

Every commit containing Tier A or Tier B content carries a trailer:

```
Generated-by: <tool name and version or model identifier, and date>
AI-Content: substantial | assisted
```

For example:

```
Generated-by: Claude Opus 4.5 (Anthropic), 2026-09
AI-Content: substantial
```

If a single commit mixes files at different tiers, the trailer reflects the highest tier present in that commit, and the PR description (below) carries the per-file breakdown — a commit-level trailer alone doesn't give a reviewer enough resolution to know which specific file deserves the closer look Tier A warrants.

### Pull request description

Alongside the trailer, every PR containing Tier A or Tier B content includes an "AI provenance" section. A template to paste in and fill out:

```markdown
## AI provenance

- Tool(s) used: <name and version/model, and date>
- Tier A (substantial) files: <list, or "none">
- Tier B (assisted) files: <list, or "none">
- Terms-of-use check (§1): <confirmed / not applicable>
- Third-party material check (§2): <which condition applies, and how you confirmed it>
- Domain-neutrality check (§3): <confirmed, if ontology content is touched>
```

### Surviving a squash merge

Where this repository's merge settings squash a PR's commits into one on landing, the trailer has to survive into that final commit message — editable in GitHub's merge UI before confirming. A reviewer approving a Tier A or Tier B PR should check this at merge time, not only when the PR was opened, since the trailer can otherwise silently disappear at exactly the point it matters most for the permanent history.

---

## If you later discover a problem

If you learn, after a contribution has been merged, that AI-generated output you submitted reproduced material under an incompatible licence, or that something you represented at the time turns out not to have been accurate, tell the maintainers as soon as you know. `[Maintainer contact channel to be added once established — see repository for the current mechanism.]` This mirrors an ordinary good-faith correction obligation; it isn't a punitive process, and finding and reporting the issue yourself is always better than someone else finding it later.

---

## Publishing AI-generated content publicly

Separate from contributing to the repository: if LATTICE publishes AI-drafted text publicly under the project's name — README updates, release notes, security advisories, announcements — a different rule applies, because the audience for that text isn't reviewing a diff, they're reading a public statement on trust.

Under the EU AI Act, in force since 2 August 2026, such text must be labelled as AI-generated unless a person reviewed it before publication and takes responsibility for it. Ordinary maintainer review of a pull request that updates public-facing content — the same review any other contribution gets — satisfies this; nothing beyond that is required. Content published without that review, for instance by an automated process posting directly, must carry a visible AI-generated label.

In short: review it before you publish it, or label it.

---

## Tools

This document doesn't name approved or prohibited tools, and isn't going to. Use whatever you find useful, subject to the checks above being genuinely satisfied for the account and terms you're actually using.

---

## This will change

AI tooling, the law around it, and this project's own experience of what disclosure actually needs to look like in practice are all moving targets. This policy will be revisited as any of them shift — a model that can flag its own training-data overlaps changes what's achievable under §2 above; a change in applicable law changes what's required; the project's own experience with a first few Tier A contributions may reveal that the tiering above needs adjustment. Treat this as the current position, not a settled one.
