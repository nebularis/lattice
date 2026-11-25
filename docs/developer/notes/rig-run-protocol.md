<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# What passes between a rig's owner and this repository

**Unit:** `v-rig`, prefix VR ([plan](../plans/v-rig.md), [status](../status/v-rig.md)). **Status:** proposed 2026-11-25, at the maintainer's request, outside any slice. It is a protocol for people and agents and adds no code. Nothing in it is decided until the maintainer says so.

## 1. The two sides

A verification rig is held outside this repository, and so is everything known about how it was made (the plan's scope). This repository holds the tool, the format and the [list of what a rig states](../sketches/v-rig-what-a-rig-states.md). A rig's owner holds the rig, its extension, the outputs of a run and the triage of its findings.

The tool runs in a checkout of this repository and reads the rig in place. So a run puts private files inside a checkout of a public repository, in its ignored folder, and what a run found has to come back here as words. This note says which words.

## 2. What the owner takes from here

| Thing | Where |
|---|---|
| the tool, at a commit the run record names | `tools/v_rig`, run with `mise run v-rig -- --rig <path>` (CAP-109) |
| the format version the tool supports | the tool's refusal names it, and the manifest states it as `format_version` |
| the list of what a rig states, with its cases | the sketch, sections 2 and 3 |
| a finding's identifier, stable across runs of one rig | `findings.ttl` |
| the outputs, inside the checkout's ignored folder and nowhere else | `.local/v-rig/<rig digest>/`. The maintainer decided on 2026-11-25 to keep the refusal of any other place, as a safety net |

## 3. What comes back

Each is written by the rig's owner, never by the tool, and each is handed to the maintainer.

| What | Its form | Where it lands here |
|---|---|---|
| the run's identity | the rig digest, the format version and this repository's commit. Nothing else names a rig | the status record's history |
| the counts | findings by kind, shape violations by layer, questions with no answer | the status record's history |
| the coverage | for each row of the list, whether the rig declares the fact, states it only in its text, or does not state it, with a count of documents and no locator | a pass over the list, row by row |
| a gap in a layer | one sentence that names the layer and what it cannot state, and the kind of agreement that states it. For example "Ledger cannot state an amount held back for one rank of claims, which a fund's terms state where claims are paid in classes" | a backlog row, a debt row or a line in the brief of an unbuilt module, as the plan's VR-Q7 says |
| a fault in the tool | a reproduction on an invented example small enough to commit beside the synthetic mini-rig | a test and a fix |
| a request for the format | the key wanted and the kind of statement it carries | the format's next version |

Not every finding comes back. The owner decides what is sent, and nothing the owner holds back is asked for.

## 4. What never crosses

No text of a rig, and no name, form number, amount, date, document identifier or locator from one, enters a tracked file here, a commit message, a pull request or a note kept in the repository. A sentence of section 3 is written from the missing term and never from the clause that showed it.

## 5. The check on this side

A run writes a deny list of the rig's identifiers, titles, values and first sentences. As generated it also holds headings and common words, so it reports ordinary text and cannot gate a commit (TD-182). Until that is settled, anyone who has read a rig and then commits here derives a stricter list first, every entry of the generated list that matches no tracked line of the checkout, and runs the deny-terms check on the staged lines with it, beside the check the commit hook already runs:

```bash
LATTICE_DENY_TERMS=<the stricter list> mise exec -- python tools/deny_terms.py
```

A pass prints nothing about a finding and exits 0. The stricter list is a private file and stays in the ignored folder beside the run.

## 6. The order

1. The owner runs the tool at a commit and keeps the outputs.
2. The owner triages the findings and writes the return of section 3.
3. The maintainer reads the return and passes on what belongs here.
4. This side files each gap where section 3 says, checks the staged lines as section 5 says, and answers a request for the format in the format's next version.
5. Where a layer or the format then changes, the owner runs again. A run is cheap, and the rig is written again only where it does not state a fact the list asks for.

## 7. Questions for the maintainer

**VR-Q19. Whether the coverage of a rig may be recorded here as counts.** For example that a rig declares nine of sixty rows and states thirty more only in its text. (a) Yes, counts and rows, since they describe the list and name nothing of the rig. (b) No, the coverage stays with the owner and only its consequences come back, a row added or a key asked for. *Leaning (a).* The counts are what shows whether the next rig is a matter of declaring what the text already says or of writing new documents, and they carry no content.
