# SPDX-License-Identifier: MPL-2.0
"""A Claude Code `PreToolUse` hook that refuses a tool call which would read the studio stack's secrets.

The stack keeps the broker user's password, the service's broker secret and the two URIs that carry the password as owner-only
files in `.build/config-studio/infra/broker`, and the broker's secret configuration and the compose broker's configuration beside
them. Reading them prints a secret into a tool's output, so a call that names that folder, one of those files or a variable that
holds one of their paths is refused with status 2 and one line on standard error. The line names `mise run studio:config`, which
prints the stack's settings with every secret redacted. It never repeats the call's text, since the text may hold a secret.

    python tools/secret_read_guard.py < hook-input.json

The hook's input is JSON on standard input, with `tool_name`, `tool_input` and usually `cwd`. A shell tool's command is checked
segment by segment, split at `;`, `&&`, `||`, `|`, a line end, `$(` and a backquote, since an allowed command may share a line with a
refused one. A segment whose program is `ls`, `rm` or the like (it lists names or deletes, which is how the credentials are rotated) or
that runs a `studio:*` mise task or `config_studio_stack.py` (how the stack itself runs) is allowed even where it names the folder.
Read, Grep and Glob are checked on their path, pattern and glob.

It exits 0 with no output for every other call and for input it cannot parse, so a fault here never stops unrelated work. It reads
the standard library and `mise.toml` only, starts no process and prints no file's content.

This is a seatbelt, not a sandbox. It cannot catch a path built at run time (`'infra/' + name`, a shell variable assembled from
parts), an interpreter that opens the file by a computed name, a `cd` into `infra` followed by `broker` and a read in a later
call, a read through a symbolic link, a name that a pattern only matches by its wildcard where the literal text is short, or
a recursive search from the repository root, which reaches the folder where the searcher does not honour `.gitignore`. A recursive
search that starts at `.build`, `.build/config-studio` or `infra` is refused.
"""

from __future__ import annotations

import fnmatch
import json
import os
import posixpath
import re
import shlex
import sys

FOLDER = ".build/config-studio/infra/broker"
# Files that hold a secret outside the folder, by name.
GUARDED_FILES = ("rabbitmq-secret.conf", "rabbitmq-studio.conf")
# Paths that contain the folder, which a recursive search would read.
ANCESTORS = (".build", ".build/config-studio", ".build/config-studio/infra")
# Variables whose value is a secret or the path of a file holding one, in addition to those `mise.toml` assigns a path in the folder.
VARIABLES = ("LATTICE_AMQP_URI_FILE", "LATTICE_STREAM_URI_FILE", "LATTICE_STUDIO_BROKER_SECRET_FILE",
             "LATTICE_AMQP_URI", "LATTICE_STREAM_URI", "LATTICE_STUDIO_BROKER_SECRET")
SHELL_TOOLS = ("bash", "powershell")
# Programs that list names or delete, never read a file's content.
NAMES_ONLY = ("ls", "dir", "rm", "rmdir", "del", "rd", "remove-item", "ri")
SEARCHERS = ("grep", "egrep", "fgrep", "rg", "ag", "ack", "zgrep")
WRAPPERS = ("sudo", "time", "command", "nohup", "nice", "exec", "env")
SPLIT = re.compile(r"\|\||&&|[;|&\n]|\$\(|`|\)")
MESSAGE = ("secret_read_guard: refused, the {what} would read the stack's secrets ({folder}). "
           "Read the settings with `mise run studio:config`, which redacts every secret")


def root_of(payload: dict) -> str:
    start = os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or os.getcwd()
    here = os.path.abspath(start)
    while True:
        if os.path.exists(os.path.join(here, "mise.toml")):
            return here
        parent = os.path.dirname(here)
        if parent == here:
            return os.path.abspath(start)
        here = parent


def variables(root: str) -> tuple:
    """The stack's variables, and any `mise.toml` assigns a path in the folder."""
    names = set(VARIABLES)
    try:
        with open(os.path.join(root, "mise.toml"), encoding="utf-8") as stream:
            names.update(re.findall(r"\b([A-Z][A-Z0-9_]*)\s*=\s*\"[^\"]*infra/broker", stream.read()))
    except OSError:
        pass
    return tuple(sorted(names))


def spellings(token: str) -> list:
    """The ways a token may name a path: with a redirection or an option's `=` taken off, and with Windows separators."""
    forms = {token}
    for form in list(forms):
        forms.add(form.lstrip("<>&"))
        if "=" in form:
            forms.add(form.split("=", 1)[1])
    return [f.replace("\\", "/") for f in forms if f]


def names_secrets(token: str, root: str, cwd: str, searcher: bool = False) -> bool:
    """Whether a path or pattern, in any spelling, is the folder, a file in it, a guarded file or, for a searcher, a folder that holds it."""
    absolute = posixpath.normpath(root.replace("\\", "/") + "/" + FOLDER).lower()
    for form in spellings(token):
        wild = any(c in form for c in "*?[")
        norm = posixpath.normpath(form).lower() if not wild else form.lower()
        relative = posixpath.normpath(posixpath.join(cwd.replace("\\", "/"), form)).lower() if not wild else ""
        for path in (norm, relative):
            if not path:
                continue
            if re.search(r"(^|/)infra/broker(/|$)", path) or (path + "/").startswith(absolute + "/") or path == absolute:
                return True
            if posixpath.basename(path) in GUARDED_FILES:
                return True
            if searcher and (path.rstrip("/").endswith(tuple("/" + a for a in ANCESTORS)) or path.rstrip("/") in ANCESTORS):
                return True
        if wild and len(re.sub(r"[*?\[\]]", "", form)) >= 3:
            targets = [absolute, absolute + "/password", absolute + "/secret", absolute + "/amqp-uri", absolute + "/stream-uri",
                       absolute + "/rabbitmq-secret.conf"]
            if any(fnmatch.fnmatchcase(t, form.lower()) or fnmatch.fnmatchcase(t, "*/" + form.lower().lstrip("/")) for t in targets):
                return True
    return False


def expands_variable(token: str, names: tuple) -> bool:
    for name in names:
        if re.search(r"(\$\{?|\$env:|%)" + re.escape(name) + r"\b", token, re.IGNORECASE):
            return True
    return False


def program_of(tokens: list) -> tuple:
    """The program a segment runs, skipping assignments and wrappers, and the tokens after it."""
    i = 0
    while i < len(tokens) and (re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", tokens[i]) or tokens[i].lower() in WRAPPERS):
        i += 1
    if i >= len(tokens):
        return "", []
    program = posixpath.basename(tokens[i].replace("\\", "/")).lower()
    return (program[:-4] if program.endswith(".exe") else program), tokens[i + 1:]


def runs_the_stack(program: str, rest: list) -> bool:
    """A `studio:*` mise task or the stack script, which is how the stack itself is run."""
    if program == "mise" and len(rest) >= 2 and rest[0] == "run" and rest[1].startswith("studio:"):
        return True
    return any(posixpath.basename(t.replace("\\", "/")).endswith("config_studio_stack.py") for t in rest[:6]) and program in (
        "python", "python3", "py", "uv")


def segment_refused(segment: str, root: str, cwd: str, names: tuple) -> bool:
    for text in {segment, segment.replace("\\", "/")}:
        try:
            tokens = shlex.split(text, posix=True)
        except ValueError:
            tokens = text.replace("'", " ").replace('"', " ").split()
        program, rest = program_of(tokens)
        if not program or program in NAMES_ONLY or runs_the_stack(program, rest):
            continue
        searcher = program in SEARCHERS
        if program == "printenv" and any(t.lower() in tuple(n.lower() for n in names) for t in rest):
            return True
        if any(names_secrets(t, root, cwd, searcher) or expands_variable(t, names) for t in tokens):
            return True
    return False


def shell_refused(command: str, root: str, cwd: str, names: tuple) -> bool:
    return any(segment_refused(s, root, cwd, names) for s in SPLIT.split(command) if s.strip())


def refusal(payload: dict) -> str:
    """What the call would read, or an empty string for a call that is allowed."""
    tool = str(payload.get("tool_name", ""))
    given = payload.get("tool_input")
    if not isinstance(given, dict):
        return ""
    root = root_of(payload)
    cwd = str(payload.get("cwd") or root)
    kind = tool.lower()
    if kind in SHELL_TOOLS:
        command = given.get("command")
        if isinstance(command, str) and shell_refused(command, root, cwd, variables(root)):
            return f"{tool} command"
    elif kind == "read":
        path = given.get("file_path")
        if isinstance(path, str) and names_secrets(path, root, cwd):
            return "path to read"
    elif kind in ("grep", "glob"):
        for key in ("path", "pattern", "glob"):
            value = given.get(key)
            if isinstance(value, str) and names_secrets(value, root, cwd, searcher=kind == "grep" and key != "pattern"):
                return f"{tool} {key}"
    return ""


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read())
        if not isinstance(payload, dict):
            return 0
        what = refusal(payload)
    except Exception:
        return 0
    if what:
        print(MESSAGE.format(what=what, folder=FOLDER), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
