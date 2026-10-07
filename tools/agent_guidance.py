#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Agent guidance: AGENTS.md, the skill library and the plugin marketplace (ADR-A117).

  build   writes .github/copilot-instructions.md from AGENTS.md
  check   fails if that file has drifted, a skill is malformed, AGENTS.md's skill table and
          .claude/skills/ disagree, the marketplace is wrong, or a link does not resolve
  link    links (copies on Windows) the skills into a personal skills directory, by default
          ~/.copilot/skills, for Copilot in projects other than LATTICE

Standard library only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = Path(".claude/skills")
COPILOT = Path(".github/copilot-instructions.md")
MARKETPLACE = Path(".claude-plugin/marketplace.json")
REPO_URL = "https://github.com/nebularis/lattice/blob/main/"
HEADER = "<!-- Generated from AGENTS.md by `mise run build:agent-guidance`. Edit AGENTS.md, not this file. -->\n\n"
LINK = re.compile(r"\]\(([^)\s]+)\)")
NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def render_copilot(agents: str) -> str:
    """AGENTS.md as Copilot's file, its relative links rewritten to resolve from .github/."""
    def relink(m: re.Match) -> str:
        target = m.group(1)
        if re.match(r"^[a-z]+:|^#|^/", target):
            return m.group(0)
        return f"](../{target})"
    return HEADER + LINK.sub(relink, agents)


def frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end < 0:
        return {}
    fields = {}
    for line in text[4:end].splitlines():
        key, sep, value = line.partition(":")
        if sep:
            fields[key.strip()] = value.strip()
    return fields


def skill_problems(root: Path) -> list[str]:
    problems = []
    skills_dir = root / SKILLS
    names = sorted(p.name for p in skills_dir.iterdir() if p.is_dir()) if skills_dir.is_dir() else []
    if not names:
        problems.append(f"{SKILLS}: no skills")
    for name in names:
        path = skills_dir / name / "SKILL.md"
        if not path.is_file():
            problems.append(f"{SKILLS / name}: no SKILL.md")
            continue
        fields = frontmatter(path.read_text(encoding="utf-8"))
        if fields.get("name") != name:
            problems.append(f"{SKILLS / name / 'SKILL.md'}: name must be '{name}'")
        if not NAME.match(name) or len(name) > 64:
            problems.append(f"{SKILLS / name}: a skill name is lowercase words joined by hyphens, at most 64 characters")
        description = fields.get("description", "")
        if not description or len(description) > 1024:
            problems.append(f"{SKILLS / name / 'SKILL.md'}: description must be 1 to 1024 characters")
    agents = root / "AGENTS.md"
    listed = set(re.findall(r"^\| `([a-z0-9-]+)` \|", agents.read_text(encoding="utf-8"), re.M)) if agents.is_file() else set()
    if listed != set(names):
        problems.append(f"AGENTS.md's skill table lists {sorted(listed)}, {SKILLS} holds {names}")
    return problems


def marketplace_problems(root: Path) -> list[str]:
    path = root / MARKETPLACE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        return [f"{MARKETPLACE}: {error}"]
    plugins = data.get("plugins", [])
    if not data.get("name") or not data.get("owner", {}).get("name"):
        return [f"{MARKETPLACE}: needs a name and an owner name"]
    if [(p.get("name"), p.get("source")) for p in plugins] != [("lattice", "./.claude")]:
        return [f"{MARKETPLACE}: must list one plugin, 'lattice', whose source is './.claude'"]
    return []


def link_problems(root: Path, files: list[Path]) -> list[str]:
    problems = []
    for path in files:
        for target in LINK.findall(path.read_text(encoding="utf-8")):
            target = target.split("#", 1)[0]
            if target.startswith(REPO_URL):
                resolved = root / target[len(REPO_URL):]
            elif not target or re.match(r"^[a-z]+:", target):
                continue
            else:
                resolved = (path.parent / target).resolve()
            if not resolved.exists():
                problems.append(f"{path.relative_to(root)}: link to {target} does not resolve")
    return problems


def check(root: Path) -> list[str]:
    problems = skill_problems(root) + marketplace_problems(root)
    agents = root / "AGENTS.md"
    copilot = root / COPILOT
    if not copilot.is_file() or copilot.read_text(encoding="utf-8") != render_copilot(agents.read_text(encoding="utf-8")):
        problems.append(f"{COPILOT} has drifted from AGENTS.md. Run `mise run build:agent-guidance`")
    files = [agents, copilot] + sorted((root / SKILLS).rglob("*.md"))
    return problems + link_problems(root, [f for f in files if f.is_file()])


def link(root: Path, target: Path, copy: bool) -> list[str]:
    target.mkdir(parents=True, exist_ok=True)
    done = []
    for skill in sorted(p for p in (root / SKILLS).iterdir() if p.is_dir()):
        dest = target / skill.name
        if dest.is_symlink() or (dest.is_dir() and (dest / ".lattice-copy").exists()):
            dest.unlink() if dest.is_symlink() else shutil.rmtree(dest)
        elif dest.exists():
            raise SystemExit(f"{dest} exists and was not made by this task. Remove it first.")
        if copy:
            shutil.copytree(skill, dest)
            (dest / ".lattice-copy").write_text("Copied by `mise run skills:link`. Re-run it after pulling.\n")
        else:
            dest.symlink_to(skill, target_is_directory=True)
        done.append(dest.name)
    return done


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["build", "check", "link"])
    parser.add_argument("--target", type=Path, default=Path.home() / ".copilot" / "skills",
                        help="for link: the personal skills directory (default ~/.copilot/skills)")
    parser.add_argument("--copy", action="store_true", help="for link: copy instead of linking (the default on Windows)")
    args = parser.parse_args(argv)
    if args.command == "build":
        (ROOT / COPILOT).write_text(render_copilot((ROOT / "AGENTS.md").read_text(encoding="utf-8")), encoding="utf-8")
        print(f"wrote {COPILOT}")
        return 0
    if args.command == "check":
        problems = check(ROOT)
        for problem in problems:
            print(problem)
        print(f"agent guidance: {len(problems)} problem(s)")
        return 1 if problems else 0
    done = link(ROOT, args.target.expanduser(), args.copy or os.name == "nt")
    print(f"{'copied' if args.copy or os.name == 'nt' else 'linked'} {', '.join(done)} into {args.target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
