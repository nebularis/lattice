---
name: lattice-constrained-environments
description: Working in an environment where a package registry, mirror or proxy blocks some fetches outright. Use when a bootstrap, install or download fails with a registry-level refusal (not a missing file, a dependency conflict or a code error), when deciding whether a blocked package can be worked around safely, or when the same block might recur on another machine or checkout.
---

# Working in a constrained environment

Some networks reach a package registry only through a mirror or a proxy that refuses some fetches. This skill is about diagnosing that refusal correctly and responding to it without pretending a missing capability is present.

## First, tell the two kinds of block apart

A registry-level refusal (a 403, a timeout, a redirect to an unrelated page, a hash mismatch with no hash-pinned requirements file) has two different shapes, and they call for different responses.

1. **Only a package's newest release is refused.** An older release of the same package installs cleanly. This is the common case, a mirror's cache lags the registry, or a scanning step only covers a release once it has aged. The fix is choosing an older release, and it is routine, not a workaround of anything.
2. **Every release of a package is refused**, old and new, wheel and source distribution alike. This is not a mirror lagging behind. It reads as a deliberate decision that this package, or the family it belongs to, does not reach this network. Overriding it is not yours to decide.

**Never conclude it is the second kind from one or two refusals at the newest release.** Test an old release directly, on its own, before drawing either conclusion. One real case looked categorical after the newest release and four more, spread across the package's whole history, were all refused, and turned out to be the first kind after all, every one of those five happened to be releases a later, unrelated constraint also excluded, and the release that actually satisfied the real requirement had never been tried.

## Where only the newest release is blocked

Pin the dependency to an older release that still satisfies whatever needs it, and move on. A transitive chain, where the pinned package's own dependency is also refused at its newest release, and that one's dependency too, can run surprisingly deep before every package in it is pinned to a release that installs. Depth alone is not a sign to stop. Each step is the same small, well-understood fix, so if the chain has not bottomed out after two or three manual tries, script the loop instead of giving up:

1. Attempt the install.
2. Read which single package the refusal names, and the exact version string the refused file belongs to.
3. Ask the registry for that package's available versions, and pick its next-older one, or better, read the real constraint that is forcing a version (a floor another already-pinned package states) and try that version precisely, rather than guessing.
4. Re-run the whole install with that one addition pinned. A pin chosen for one package can itself conflict with a different package's own stated floor or ceiling, found only once both are pinned together, so expect to revisit an earlier pin occasionally, not only add new ones.
5. Repeat until the install succeeds or a package in the chain shows the second kind of block.

Keep the final, working set of pins written down somewhere that is specific to this machine, never in a document the project publishes or a dependency file every checkout reads, since another machine without the same block should still get the newest release. Re-apply the pins after any fresh environment setup on this machine, since the project's own bootstrap still asks for the newest release by default and will hit the same block again.

## Where a whole package, or a family, is blocked

Do not try a different transport, a different host, or a build from source to reach the same package by another route. That is routing around a control someone else put there on purpose, which is a decision for whoever owns the policy, never one to make unilaterally to get a task finished.

Two honest paths remain.

- **Ask.** Tell whoever owns the environment precisely what is blocked and why the work needs it, and let them decide whether to allow it, provide it another way, or tell you to work without it.
- **Work without it, honestly.** If what actually needs to run does not exercise the blocked package's real behaviour anywhere, that is worth confirming before giving up. Trace every path that would reach it from what you are trying to run. If none does, the gap is an import or a declaration only, and recording that plainly, then running what does not depend on it, is a legitimate outcome, a known, named gap, not a hidden one.

**Never build a stand-in, a stub, or a mock for a blocked package so that something which needs its real behaviour appears to pass anyway.** A test that would exercise the real package is a test of that capability, and a stand-in makes it pass without checking anything, which is worse than an honest skip or an honest failure, a reader who sees it pass has no way to know it checked nothing. A stand-in is only ever appropriate for a dependency injected deliberately and visibly for the purpose of testing something else, never as a quiet substitute for a capability a registry refuses.

## Recording what happened

Write down, for whoever hits the same block next on the same machine, which package, which kind of block it turned out to be, and the exact pin set or decision that followed, with enough detail to redo it without repeating the investigation. Keep this where it will survive a rebuilt environment on this machine, never inside the project's own tracked files, since the block is a fact about this network, not about the project.
