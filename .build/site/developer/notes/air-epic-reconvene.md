The AIR epic has been idle since 2026-09-30. Most of what is left does not depend on CCS. Only Phase 5, the claims half of Phase 6, and substrate items S2 and S7 wait on CCS or NRS. Phases 2, 3 and 4 and AIR-6.1 can all be finished now, which covers milestones M1 to M3.

## Where the epic stands

| Phase | State |
|---|---|
| 0 Decisions, 1 Module split | complete |
| 2 Peril vocabulary | AIR-2.1 merged. AIR-2.2 briefed, not started |
| 3 Readings and crosswalks | AIR-3.1 and AIR-3.2 merged. AIR-3.3 briefed, not started |
| 4 Exposure | AIR-4.1 briefed, not started. `ontology/applied/insurance/exposure/` does not exist yet |
| 5 Contract module | deferred until CCS C9 is merged and the Open CBAA integration is done |
| 6, S | not started |

Round 3 (AIR-2.2, AIR-4.1, AIR-3.3) stopped when machine R moved to CCS. The status record was last updated 2026-09-30 and says the round-3 branches don't exist yet. They do exist on `origin`, but they are 276 commits behind `main` and hold only their brief commits, which `main` already contains (checked 2026-10-13, every `air/*` branch is an ancestor of `origin/main`). The status record and INDEX.md were out of date, and are now updated.

## What can run while CCS continues

| Work | Lane | Depends on CCS? | Before branching |
|---|---|---|---|
| **AIR-3.3** (SWRL and OWL readings) | R | No. CCS needs it: C13 waits on AIR-3.3 | needs a design answer first (see below) |
| **AIR-2.2** (characteristic schemes) | S | No. Only re-pins when CCS bumps a lower layer | brief needs its version numbers updated |
| **AIR-4.1** (exposure core) | S | No. Only re-pins | brief needs its version numbers updated |
| AIR-2.3 to 2.7, 4.2 to 4.6, 3.4, 3.5, 6.1 | S, with 3.5 on R | No | rolling-wave briefs still to write. Round 4's are AIR-2.3, 2.4, 4.2 and 4.4 |
| Substrate S6, spatial guidance (text only) | S | No | brief |

Not now:
- Phase 5 waits on CCS C9 and the C17 handoff.
- AIR-6.2 (claims) follows Phase 5.
- S2 is paired with CCS C9b3, and S7 with NRS N10.
- S1, S4 and S5 change substrate layers that CCS is still bumping. The lanes plan merges substrate branches after AIR-6.1 anyway.

## What changed under the briefs since 2026-09-30

1. **AIR-3.3 overlaps with CCS HQ-6a.2.** That branch (`ccs/hq6a2-closures-compilers`) is accepted but not merged. It changes `eligibility_ir.py`, `sparql_backend.py` and `test_set_readings.py`, and adds closed bindings to set readings. It leaves SWRL and OWL refusing set readings (HQ6a2-10), and AIR-3.3 is the slice that removes those refusals. The AIR-3.3 brief predates closures, so it has to say what SWRL and OWL do with a closed binding. HQ-6a.1 has also changed the two examples that AIR33-04 to 06 use. The design question is AIR-3.3-Q1:
   - **(a) Compile a closed binding as its open reading, with a mapping note.** My hypothesis is that SWRL stays sound. Each rule it emits is fixed by one value, which still holds under a closed reading, so a closure only adds decisions that SPARQL makes and SWRL does not. OWL's open-world reading would then also ignore the closure, which fits design-time checks.
   - **(b) Keep refusing closed bindings in SWRL and OWL.** This is simpler, but closures then never reach the reasoner routes.
   
   Either way, HQ-6a.2 should merge first and `air/3.3` should be rebuilt from `main`.
2. **AIR-2.2 and AIR-4.1 have old version numbers.** CCS cascades moved the layers these briefs pin:

   | Layer | Pinned in briefs | Now |
   |---|---|---|
   | peril | 0.1.0 | 0.4.0 |
   | common | 0.1.0 | 0.5.0 |
   | Foundation | 0.3.0 | 0.4.0 |
   | Vocabulary | 0.3.0 | 0.4.0 |
   | Quantification | 0.5.0 | 0.8.0 |
   | Party | 0.5.0 | 0.9.0 |

   No design change is needed. `pty:Actor` and `pty:RoleOccupancy` still exist, and AIR-4.1 already uses `fnd:Key`. CCS slice C16c will remove Party's shares later. That is worth a check against `aeo:controlShare`, but it doesn't block AIR-4.1.
3. **Re-pins will recur.** Every CCS bump of Foundation, Vocabulary, Quantification or Party forces an in-flight AIR branch to re-pin at rebase (lanes §6 step 3). It is mechanical, but S branches should be kept short and merged promptly.

## Proposed order

1. On `main`, update the AIR-2.2 and AIR-4.1 briefs and their Validation Pack skeletons. Update the status record and INDEX too. I can do this now if you want.
2. You answer AIR-3.3-Q1. HQ-6a.2 merges, and then I amend the AIR-3.3 brief.
3. S builds AIR-2.2, then AIR-4.1, on one new branch from `main`, `air/applied-reference`, not on the rebuilt per-slice branches. The old branches are deleted. AIR-3.3 is rebuilt from `main` later, on its own branch (lanes §2, §3).
4. In parallel, R drafts the round-4 briefs (AIR-2.3, 2.4, 4.2, 4.4). The lanes plan says R verifies S bundles before continuing other work. That rule should now apply to CCS slices as well as NRS ones.

🔴 PLAN FIRST: AIR-2.2 and AIR-4.1 need their briefs updated on `main`, AIR-3.3 needs AIR-3.3-Q1 answered and its brief amended after HQ-6a.2 merges, and AIR-2.3, AIR-2.4, AIR-4.2 and AIR-4.4 need briefs drafted before their branches.
