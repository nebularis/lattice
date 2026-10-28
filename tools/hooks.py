#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Run the checks a change needs, at the moments ADR-A133 names.

  python tools/hooks.py run pre-commit          the commit checks over what is staged
  python tools/hooks.py run pre-merge-commit    the merge checks, when merging into main
  python tools/hooks.py run post-merge          rebuild the knowledge index after a merge
  python tools/hooks.py merge [--against main]  the merge checks for the current branch, by hand
  python tools/hooks.py install [--bootstrap]   install the hooks into the shared hooks directory

A check runs only when the change touches a path it governs, and judges only the touched files
(ADR-A133 decision 3). A commit to main while a merge or a squash is in progress is a merge. No hook
runs at a push. LATTICE_HOOKS_SKIP names checks to skip, separated by commas, or "all".

Standard library only. A check whose tool needs a package that is not installed warns instead of
failing, and says to run `mise run bootstrap`.
"""

from __future__ import annotations

import argparse
import fnmatch
import importlib.util
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence

HOOK_MARK = "# lattice hooks (ADR-A133)"
OLD_MARKS = ("# lattice deny-terms hook",)
HOOKS = ("pre-commit", "pre-merge-commit", "post-merge")
MERGE_TARGET = "main"
BLOCK, WARN = "block", "warn"

HOOK_SCRIPT = f"""#!/bin/sh
{HOOK_MARK}
# Installed by `mise run hooks:install`. Runs the checks a change needs (tools/hooks.py).
hook=$(basename "$0")
if [ -f tools/hooks.py ]; then
  if command -v mise >/dev/null 2>&1; then exec mise exec -- python tools/hooks.py run "$hook"; fi
  if command -v python3 >/dev/null 2>&1; then exec python3 tools/hooks.py run "$hook"; fi
  exec python tools/hooks.py run "$hook"
fi
# A checkout from before the dispatcher: the deny-list check alone, as the old hook ran it.
if [ "$hook" = pre-commit ] && [ -f tools/deny_terms.py ]; then
  if command -v python3 >/dev/null 2>&1; then exec python3 tools/deny_terms.py; fi
  exec python tools/deny_terms.py
fi
exit 0
"""


def git(*args: str, cwd: Path, check: bool = True) -> str:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=check,
                          encoding="utf-8", errors="replace").stdout


@dataclass(frozen=True)
class Change:
    """What a commit, or a merge into main, brings. ``against`` is the revision the added lines are
    read against, None for the index."""
    root: Path
    files: tuple[str, ...]
    merge: bool
    against: str | None = None

    def added_lines(self) -> Iterable[tuple[str, int, str]]:
        """(path, line number, text) for every line the change adds."""
        args = ["diff", "-U0", "--no-color", "--no-ext-diff"]
        args += [f"{self.against}...HEAD"] if self.against else ["--cached"]
        path, number = None, 0
        for line in git(*args, cwd=self.root).splitlines():
            if line.startswith("+++ "):
                path = None if line[4:] == "/dev/null" else line[6:]
            elif line.startswith("@@"):
                number = int(line.split("+", 1)[1].split(",")[0].split(" ")[0])
            elif line.startswith("+") and path:
                yield path, number, line[1:]
                number += 1


@dataclass(frozen=True)
class Outcome:
    check: str
    severity: str
    messages: tuple[str, ...]


@dataclass(frozen=True)
class Check:
    """A check, the paths it governs (globs, "*" for anything), how it fails at a commit and at a
    merge, and what it runs: a function of the change and the touched files, returning messages."""
    name: str
    governs: tuple[str, ...]
    run: Callable[[Change, list[str]], list[str]]
    on_commit: str = BLOCK
    on_merge: str = BLOCK
    merge_only: bool = False

    def touched(self, files: Sequence[str]) -> list[str]:
        return [f for f in files if any(fnmatch.fnmatch(f, glob) for glob in self.governs)]


def staged_files(root: Path) -> tuple[str, ...]:
    out = git("diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z", cwd=root)
    return tuple(p for p in out.split("\0") if p)


def branch_files(root: Path, against: str) -> tuple[str, ...]:
    out = git("diff", "--name-only", "--diff-filter=ACMR", "-z", f"{against}...HEAD", cwd=root)
    return tuple(p for p in out.split("\0") if p)


def current_branch(root: Path) -> str:
    return git("rev-parse", "--abbrev-ref", "HEAD", cwd=root, check=False).strip()


def merging(root: Path, hook: str) -> bool:
    """A merge into main: the pre-merge-commit hook, or a commit to main while a merge or a squash is
    in progress (a merge with conflicts, and a squash, are both completed by `git commit`)."""
    if current_branch(root) != MERGE_TARGET:
        return False
    if hook == "pre-merge-commit":
        return True
    return any((root / git("rev-parse", "--git-path", name, cwd=root).strip()).exists()
               for name in ("MERGE_HEAD", "SQUASH_MSG"))


def skipped() -> set[str]:
    return {name.strip() for name in os.environ.get("LATTICE_HOOKS_SKIP", "").split(",") if name.strip()}


class Unavailable(Exception):
    """A check's tool cannot run here, for want of a package or a file. The check warns."""


def evaluate(change: Change, checks: Sequence[Check], skip: set[str]) -> list[Outcome]:
    outcomes = []
    for check in checks:
        if check.name in skip or "all" in skip:
            continue
        if check.merge_only and not change.merge:
            continue
        touched = check.touched(change.files)
        if not touched:
            continue
        severity = check.on_merge if change.merge else check.on_commit
        try:
            messages = check.run(change, touched)
        except Unavailable as reason:
            severity, messages = WARN, [f"not run: {reason}. Run `mise run bootstrap`."]
        outcomes.append(Outcome(check.name, severity, tuple(messages)))
    return outcomes


def report(change: Change, outcomes: Sequence[Outcome], moment: str) -> int:
    failed = [o for o in outcomes if o.messages and o.severity == BLOCK]
    print(f"hooks: {moment}{' (a merge into ' + MERGE_TARGET + ')' if change.merge else ''}, "
          f"{len(change.files)} file(s), {len(outcomes)} check(s) run")
    for outcome in outcomes:
        state = "ok" if not outcome.messages else ("FAILED" if outcome.severity == BLOCK else "warning")
        print(f"  {state:8} {outcome.check}")
        for message in outcome.messages:
            print(f"           {message}")
    if failed:
        names = ",".join(o.check for o in failed)
        print(f"hooks: {len(failed)} check(s) failed. Fix them, or skip with LATTICE_HOOKS_SKIP={names} "
              "(or every check with --no-verify) and record why in the slice's Validation Pack.")
    return 1 if failed else 0


# ---- the checks -------------------------------------------------------------------------------

def tools_dir(change: Change) -> Path:
    """The checkout's tools: the dispatcher's own directory, since a hook runs the committing
    checkout's copy of it."""
    return Path(__file__).resolve().parent


def run_tool(change: Change, *args: str) -> list[str]:
    """Run a tool with this interpreter from the repository root. Nothing when it passes, its output
    when it fails. A tool that is absent, or wants a package that is not installed, is Unavailable."""
    if not (change.root / args[0]).is_file():
        raise Unavailable(f"{args[0]} is not in this checkout")
    result = subprocess.run([sys.executable, *args], cwd=change.root, capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
    if result.returncode == 0:
        return []
    output = (result.stdout + result.stderr).splitlines()
    missing = next((line.strip() for line in output if "ModuleNotFoundError" in line), None)
    if missing:
        raise Unavailable(missing)
    lines = [line for line in output if line.strip() and not line.startswith("=")]
    return lines[-20:] or [f"{args[0]} failed with exit code {result.returncode}"]


def tool_module(change: Change, name: str):
    """Import one of the repository's tools from this checkout."""
    if not (tools_dir(change) / f"{name}.py").is_file():
        raise Unavailable(f"tools/{name}.py is not in this checkout")
    path = tools_dir(change) / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"_hooks_{name}_{abs(hash(str(path)))}", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    sys.path.insert(0, str(tools_dir(change)))
    try:
        spec.loader.exec_module(module)
    except ModuleNotFoundError as error:
        sys.modules.pop(spec.name, None)
        raise Unavailable(str(error))
    finally:
        sys.path.pop(0)
    return module


def deny_terms(change: Change, touched: list[str]) -> list[str]:
    deny = tool_module(change, "deny_terms")
    path = deny.list_path()
    if path is None:
        return []
    patterns, skips = deny.load(path)
    return deny.findings(change.added_lines(), patterns, skips)


def literate(change: Change, touched: list[str]) -> list[str]:
    """Each literate module the change touches: its README and the files it generates agree."""
    if not (change.root / "repository-catalogue.md").is_file():
        return []
    catalogue = tool_module(change, "lattice_repo_catalogue").load(change.root)
    messages = []
    for module in catalogue.modules.values():
        if not module.literate:
            continue
        prefix = module.path.as_posix().rstrip("/") + "/"
        if not any(path.startswith(prefix) for path in touched):
            continue
        readme = (module.path / "README.md").as_posix()
        args = ["tools/literate_extract.py", readme, "--layer", module.name, "--root", ".", "--check"]
        if "isabelle-spec" in (change.root / readme).read_text(encoding="utf-8"):
            args += ["--proofs-root", "tools/proofs", "--reference-root", "tools/reference"]
        failed = run_tool(change, *args)
        if failed:
            messages += [f"{readme} and the files it generates disagree. Extract it, or restore the hand edit:"]
            messages += [f"  {line}" for line in failed]
    return messages


def links(change: Change, touched: list[str]) -> list[str]:
    files = [f for f in touched if not f.startswith(("docs/_includes/", "node_modules/")) and "/vendor/" not in f]
    root = change.root.resolve()
    found = tool_module(change, "repository_topology_check").check_links_in(root / f for f in files)
    return [line.replace(f"{root.as_posix()}/", "") for line in found]


def catalogue(change: Change, touched: list[str]) -> list[str]:
    """The catalogue against the tree, without the exceptions it lists as known."""
    return [line for line in run_tool(change, "tools/lattice_repo_catalogue.py", "check")
            if ", known:" not in line]


def published_decisions(change: Change, touched: list[str]) -> list[str]:
    """At a commit, the findings about the touched documents. At a merge, every finding."""
    found = (run_tool(change, "tools/published_decisions.py", "check")
             + run_tool(change, "tools/sources_check.py", "--quiet"))
    if change.merge:
        return found
    return [line for line in found if any(path in line for path in touched)]


def writing_findings(change: Change, touched: list[str]):
    files = set(touched)
    rules = tool_module(change, "writing_rules")
    return rules.check(change.root, (line for line in change.added_lines() if line[0] in files))


def writing(change: Change, touched: list[str]) -> list[str]:
    """The writing rules that fail: a semicolon in prose, "this document" in a literate README."""
    return [str(f) for f in writing_findings(change, touched) if f.blocking]


def wrapping(change: Change, touched: list[str]) -> list[str]:
    """Hard-wrapped lines, one message a file, since an edit to an older wrapped section adds many."""
    lines: dict[str, list[int]] = {}
    for finding in writing_findings(change, touched):
        if not finding.blocking:
            lines.setdefault(finding.path, []).append(finding.line)
    return [f"{path}: {len(numbers)} hard-wrapped line(s), from line {min(numbers)}. Keep a paragraph or a list "
            "entry on one line" for path, numbers in sorted(lines.items())]


def whole(*args: str) -> Callable[[Change, list[str]], list[str]]:
    """A check that judges a set of files as a whole, once any of them is touched."""
    return lambda change, touched: run_tool(change, *args)


def checks() -> list[Check]:
    """The registry, in the order they run (ADR-A133 decision 5)."""
    return [
        Check("deny-terms", ("*",), deny_terms),
        Check("literate", ("ontology/*",), literate),
        Check("agent-guidance", ("AGENTS.md", "CLAUDE.md", ".github/copilot-instructions.md", ".claude/skills/*",
                                 ".claude-plugin/*", "repository-catalogue.md"),
              whole("tools/agent_guidance.py", "check")),
        Check("catalogue", ("repository-catalogue.md", "ontology/*", "tools/*", "packages/*", "benchmark/*",
                            "contracts/*"),
              catalogue),
        Check("import-guard", ("ontology/*.ttl", "ontology/*README.md"), whole("tools/import_guard.py")),
        Check("links", ("*.md",), links),
        Check("formal-freshness", ("tools/proofs/*", "tools/reference/*", "ontology/*README.md"),
              whole("tools/check_formal_freshness.py")),
        Check("site-sections", ("docs/*", "ontology/*README.md", "README.md"), whole("tools/site_sections.py", "check")),
        Check("writing", ("*.md",), writing, on_commit=BLOCK, on_merge=WARN),
        Check("wrapping", ("*.md",), wrapping, on_commit=WARN, on_merge=WARN),
        Check("published-decisions", ("*.md",), published_decisions, on_commit=WARN, on_merge=BLOCK),
        Check("identifiers", ("docs/developer/*", "docs/architecture/decisions/*",
                              "docs/architecture/triple-store-discovery.md"),
              whole("tools/knowledge/identifiers.py")),
        Check("ontology-versioning", ("ontology/*",),
              lambda change, touched: (run_tool(change, "tools/ontology_version_check.py")
                                       + run_tool(change, "tools/ontology_releases.py", "check")),
              merge_only=True),
    ]


# ---- installation -----------------------------------------------------------------------------

def hooks_dir(root: Path) -> Path:
    path = Path(git("rev-parse", "--git-path", "hooks", cwd=root).strip())
    return path if path.is_absolute() else root / path


def install(root: Path, bootstrap: bool = False) -> list[str]:
    """Install every hook into the shared hooks directory, which covers every worktree. Never replace
    a hook this task did not write: fail, or under bootstrap warn and carry on."""
    try:
        directory = hooks_dir(root)
    except subprocess.CalledProcessError:
        if bootstrap:
            return ["hooks: not a git checkout, no hooks installed"]
        raise SystemExit("hooks: not a git checkout")
    directory.mkdir(parents=True, exist_ok=True)
    lines = []
    for name in HOOKS:
        hook = directory / name
        if hook.exists():
            text = hook.read_text(encoding="utf-8", errors="replace")
            if HOOK_MARK not in text and not any(mark in text for mark in OLD_MARKS):
                message = (f"hooks: {hook} exists and was not installed by this task. Add "
                           f"`python tools/hooks.py run {name}` to it by hand, or move it aside and run "
                           "`mise run hooks:install`.")
                if bootstrap:
                    lines.append(message)
                    continue
                raise SystemExit(message)
        hook.write_text(HOOK_SCRIPT, encoding="utf-8", newline="\n")
        hook.chmod(0o755)
        lines.append(f"hooks: installed {hook}")
    return lines


# ---- entry ------------------------------------------------------------------------------------

def post_merge(root: Path) -> int:
    """After a merge, derive the knowledge index again so it is never stale (ADR-A133 addendum).
    The merge has already happened, so this never fails it."""
    change = Change(root, (), False)
    try:
        lines = run_tool(change, "tools/knowledge/extract.py")
    except Unavailable as reason:
        lines = [f"not rebuilt: {reason}. Run `mise run build:knowledge`"]
    print("hooks: post-merge, knowledge index " + ("rebuilt" if not lines else "\n  ".join(["not rebuilt"] + lines)))
    return 0


def run(root: Path, hook: str, registry: Sequence[Check] | None = None) -> int:
    if hook == "post-merge":
        return post_merge(root)
    change = Change(root, staged_files(root), merging(root, hook))
    return report(change, evaluate(change, registry or checks(), skipped()), hook)


def merge(root: Path, against: str, registry: Sequence[Check] | None = None) -> int:
    change = Change(root, branch_files(root, against), True, against)
    return report(change, evaluate(change, registry or checks(), skipped()), f"merge of HEAD into {against}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    run_parser = sub.add_parser("run", help="run the checks for a hook")
    run_parser.add_argument("hook", choices=HOOKS)
    merge_parser = sub.add_parser("merge", help="run the merge checks for the current branch")
    merge_parser.add_argument("--against", default=MERGE_TARGET)
    install_parser = sub.add_parser("install", help="install the hooks")
    install_parser.add_argument("--bootstrap", action="store_true", help="warn, never fail")
    args = parser.parse_args(argv)
    if args.command == "install":
        try:
            root = Path(git("rev-parse", "--show-toplevel", cwd=Path.cwd()).strip())
        except subprocess.CalledProcessError:
            if args.bootstrap:
                print("hooks: not a git checkout, no hooks installed")
                return 0
            raise
        for line in install(root, args.bootstrap):
            print(line)
        return 0
    root = Path(git("rev-parse", "--show-toplevel", cwd=Path.cwd()).strip())
    if args.command == "run":
        return run(root, args.hook)
    return merge(root, args.against)


if __name__ == "__main__":
    sys.exit(main())
