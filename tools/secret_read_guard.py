# SPDX-License-Identifier: MPL-2.0
"""A Claude Code `PreToolUse` hook that refuses a tool call which would read the studio stack's secrets.

The stack keeps the broker user's password, the service's broker secret and the two URIs that carry the password as owner-only
files in `.build/config-studio/infra/broker`, and the broker's secret configuration and the compose broker's configuration beside
them. Reading them prints a secret into a tool's output, so a call that names that folder, one of those files or a variable that
holds one of their paths is refused. The reason names `mise run studio:config`, which prints the stack's settings with every secret
redacted. It never repeats the call's text, since the text may hold a secret.

    python tools/secret_read_guard.py < hook-input.json

What it checks. The hook's input is JSON on standard input, with `tool_name`, `tool_input` and usually `cwd`. A shell tool's command
is checked segment by segment, split at `;`, `&&`, `||`, `|`, a line end, `$(` and a backquote, since an allowed command may share a
line with a refused one. The command string of `bash -c`, `sh -c`, `pwsh -Command` and `eval`, and the command after `mise exec --`,
are checked the same way. A segment whose program is `ls`, `rm` or the like (it lists names or deletes, which is how the credentials
are rotated) or that runs a `studio:*` mise task or `config_studio_stack.py` (how the stack itself runs) is allowed even where it
names the folder. Read is checked on its path, Glob on its path and pattern, and Grep on its path and glob. Grep's `pattern` is a
regular expression and is never read as a path.

Where the root comes from. The working directory the call states, `cwd`, decides first, and the repository root is the nearest
folder above it that holds `mise.toml`. `CLAUDE_PROJECT_DIR` is used only where the call has no `cwd`, so a stale project directory
cannot decide what is refused.

How a wildcard is matched. A token with `*`, `?` or `[` is a pattern. It is matched by path segment, as a shell glob is. `*`, `?`
and `[...]` stay inside one segment and a segment `**` stands for any number of segments, none included. The pattern is resolved
against the working directory and against the repository root, and no other folder. It is never matched against the checkout's
absolute path as text and never given a leading `*/`, so a checkout whose name holds `studio` or `lattice` does not change a verdict.
It is refused when it matches the folder or a file in it, and, where the program opens files, a guarded file outside it.

Where a wildcard is tested. Only where the program opens what the token names, so for a reader (`cat`, `head`, `sed`, `cp`, `tar`,
`Get-Content` and the like), for a searcher's file operands, for the start points of `find` and for the path of the Read, Grep and
Glob tools. The values that are names or expressions are never tested, for example Grep's pattern and the first operand of
`grep`, and the values of `--list`, `--grep`, `-name`, `-regex`, `-g`, `--include` and `-Filter`. Nor are the arguments of `echo`,
`git` (the folder is untracked, and a `git log` pathspec after `--` is a pattern) and any program the lists do not name. A literal
path into the folder is refused for every program, as before.

How it refuses. A refusal is the hook's JSON decision on standard output, a `deny` with the reason above, and the exit status is 0.
Every other outcome, an allowed call, input it cannot parse and a fault inside the guard, exits 0 with nothing on standard output, so
a fault here never stops unrelated work. It reads the standard library and `mise.toml` only, starts no process and prints no
file's content.

How it fails. The hook command in `.claude/settings.json` runs this script only where the file exists and `mise` is found. Where the
file is missing, `mise` is missing or the run exits non-zero, which Python does with 2 when it cannot open its script and with 1 on
an error, the command prints a `systemMessage` that says the guard did not run, writes a line to standard error and exits 0, so the
call goes ahead and the person is told it was not checked. A status of 2 from the hook would be read as a refusal.

This is a seatbelt, not a sandbox. It cannot catch a path built at run time (`'infra/' + name`, a shell variable assembled from
parts), an interpreter that opens the file by a computed name, a `cd` into `infra` followed by `broker` and a read in a later
call, a read through a symbolic link, a wildcard given to a program the lists do not name, a wildcard in a value it takes for a name,
a Grep `glob` without a slash, which ripgrep matches at any depth, a pattern whose `..` follows a wildcard segment, or a recursive
search from the repository root, which reaches the folder where the searcher does not honour `.gitignore`. A recursive search that
starts at `.build`, `.build/config-studio` or `infra` is refused.
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
# Where those files are, for a wildcard, relative to the root.
GUARDED_PATHS = (".build/config-studio/infra/rabbitmq-secret.conf", ".build/config-studio/infra/compose/rabbitmq-studio.conf")
# The files the folder holds, for a wildcard.
FOLDER_FILES = ("password", "secret", "amqp-uri", "stream-uri", "rabbitmq-secret.conf")
# Paths that contain the folder, which a recursive search would read.
ANCESTORS = (".build", ".build/config-studio", ".build/config-studio/infra")
# Variables whose value is a secret or the path of a file holding one, in addition to those `mise.toml` assigns a path in the folder.
VARIABLES = ("LATTICE_AMQP_URI_FILE", "LATTICE_STREAM_URI_FILE", "LATTICE_STUDIO_BROKER_SECRET_FILE",
             "LATTICE_AMQP_URI", "LATTICE_STREAM_URI", "LATTICE_STUDIO_BROKER_SECRET")
SHELL_TOOLS = ("bash", "powershell")
# Programs that list names or delete, never read a file's content.
NAMES_ONLY = ("ls", "dir", "rm", "rmdir", "del", "rd", "remove-item", "ri")
SEARCHERS = ("grep", "egrep", "fgrep", "rg", "ag", "ack", "zgrep")
# Programs that open the files their operands name.
READERS = ("cat", "tac", "head", "tail", "less", "more", "most", "nl", "sed", "awk", "gawk", "mawk", "wc", "sort", "uniq", "cut", "paste", "od",
           "xxd", "hexdump", "strings", "base64", "file", "cp", "mv", "scp", "rsync", "tar", "zip", "unzip", "gzip", "gunzip", "zcat", "bzip2",
           "bunzip2", "xz", "unxz", "7z", "diff", "cmp", "comm", "join", "fold", "fmt", "column", "bat", "jq", "yq", "source", ".", "vi", "vim",
           "view", "nano", "emacs", "sha1sum", "sha256sum", "md5sum", "cksum", "type", "get-content", "gc", "select-string", "sls", "copy-item",
           "copy", "cpi", "move-item", "move", "mi", "get-item", "gi", "get-filehash", "import-csv", "import-clixml")
# Programs whose first operand is a pattern or a script, unless an option gives it, and never a path.
EXPRESSION_FIRST = SEARCHERS + ("sed", "awk", "gawk", "mawk", "jq", "yq")
FINDERS = ("find",)
SHELLS = ("sh", "bash", "zsh", "dash", "ksh", "pwsh", "powershell", "cmd")
SHELL_COMMAND_OPTIONS = ("-c", "-lc", "-command", "/c")
WRAPPERS = ("sudo", "time", "command", "nohup", "nice", "exec", "env")
# Options whose value is a name or an expression, never a path.
EXPRESSIONS = ("--list", "--grep", "--regexp", "--expression", "--include", "--exclude", "--exclude-dir", "--glob", "--iglob", "--pattern",
               "--name", "--match", "--type", "-g", "-name", "-iname", "-path", "-ipath", "-wholename", "-regex", "-iregex", "-filter",
               "-include", "-exclude", "-pattern")
SPLIT = re.compile(r"\|\||&&|[;|&\n]|\$\(|`|\)")
MESSAGE = ("secret_read_guard: refused, the {what} would read the stack's secrets ({folder}). "
           "Read the settings with `mise run studio:config`, which redacts every secret")


def root_of(payload: dict) -> str:
    """The repository root above the call's working directory, or above `CLAUDE_PROJECT_DIR` where the call states none."""
    given = payload.get("cwd")
    start = given if isinstance(given, str) and given else os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
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


def split_path(path: str) -> list:
    return [s for s in path.split("/") if s and s != "."]


def is_absolute(path: str) -> bool:
    return path.startswith("/") or re.match(r"^[A-Za-z]:/", path) is not None


def segments_match(pattern: list, target: list) -> bool:
    """Whether a glob's segments match a path's segments. `*`, `?` and `[...]` stay in one segment and a segment `**` is any number, none included."""
    reached = {0}
    for segment in pattern:
        following = set()
        if segment == "**":
            for position in reached:
                following.update(range(position, len(target) + 1))
        else:
            for position in reached:
                if position < len(target) and fnmatch.fnmatchcase(target[position], segment):
                    following.add(position + 1)
        reached = following
        if not reached:
            return False
    return len(target) in reached


def wildcard_names(form: str, root: str, cwd: str, guarded: bool) -> bool:
    """Whether a wildcard, resolved against the working directory and the root only, matches the folder, a file in it or, if `guarded`, a guarded file."""
    base = root.replace("\\", "/")
    absolute = posixpath.normpath(base + "/" + FOLDER).lower()
    targets = [absolute] + [absolute + "/" + name for name in FOLDER_FILES]
    if guarded:
        targets += [posixpath.normpath(base + "/" + path).lower() for path in GUARDED_PATHS]
    pattern = split_path(posixpath.normpath(form.lower()))
    if is_absolute(form):
        return any(segments_match(pattern, split_path(t)) for t in targets)
    ups = 0
    while pattern and pattern[0] == "..":
        ups += 1
        pattern.pop(0)
    for anchor in dict.fromkeys((posixpath.normpath(cwd.replace("\\", "/")).lower(), posixpath.normpath(base).lower())):
        folders = split_path(anchor)
        if ups > len(folders):
            continue
        # The folders above the anchor that the pattern keeps are literal text, so they are compared and never matched.
        kept = folders[:len(folders) - ups]
        for target in map(split_path, targets):
            if target[:len(kept)] == kept and segments_match(pattern, target[len(kept):]):
                return True
    return False


def names_secrets(token: str, root: str, cwd: str, searcher: bool = False, wildcards: str = "full") -> bool:
    """Whether a path or pattern, in any spelling, is the folder, a file in it, a guarded file or, for a searcher, a folder that holds it.

    `wildcards` is `full` where a wildcard names what the program opens, `names` where it only names what a tool lists or filters
    (so a guarded file outside the folder does not count) and `off` where the token is a name or an expression and a wildcard is
    no path. A literal path is tested in every mode.
    """
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
        if wild and wildcards != "off" and wildcard_names(form, root, cwd, wildcards == "full"):
            return True
    return False


def expands_variable(token: str, names: tuple) -> bool:
    for name in names:
        if re.search(r"(\$\{?|\$env:|%)" + re.escape(name) + r"\b", token, re.IGNORECASE):
            return True
    return False


def program_of(tokens: list) -> tuple:
    """The program a segment runs, skipping assignments and wrappers, the tokens after it and where they start."""
    i = 0
    while i < len(tokens) and (re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", tokens[i]) or tokens[i].lower() in WRAPPERS):
        i += 1
    if i >= len(tokens):
        return "", [], len(tokens)
    program = posixpath.basename(tokens[i].replace("\\", "/")).lower()
    return (program[:-4] if program.endswith(".exe") else program), tokens[i + 1:], i + 1


def runs_the_stack(program: str, rest: list) -> bool:
    """A `studio:*` mise task or the stack script, which is how the stack itself is run."""
    if program == "mise" and len(rest) >= 2 and rest[0] == "run" and rest[1].startswith("studio:"):
        return True
    return any(posixpath.basename(t.replace("\\", "/")).endswith("config_studio_stack.py") for t in rest[:6]) and program in (
        "python", "python3", "py", "uv")


def opened(program: str, rest: list) -> set:
    """The positions in `rest` of the tokens the program opens as files or folders, which are the ones a wildcard may name."""
    if program in FINDERS:
        found = set()
        for i, token in enumerate(rest):
            if token in ("-H", "-L", "-P"):
                continue
            if token.startswith(("-", "!", "(")):
                break
            found.add(i)
        return found
    searcher = program in SEARCHERS
    if not searcher and program not in READERS:
        return set()
    first_is_expression = program in EXPRESSION_FIRST
    expression_given = first_is_expression and any(t in ("--regexp", "--file", "--expression") or t.startswith(("--regexp=", "--file=", "--expression="))
                                                   or re.fullmatch(r"-[A-Za-z]*[ef]", t) for t in rest)
    found, skip = set(), False
    for i, token in enumerate(rest):
        if skip:
            skip = False
            continue
        name = token.lower().split("=", 1)[0]
        if token.startswith("-") and len(token) > 1:
            if name in EXPRESSIONS or (first_is_expression and re.fullmatch(r"-[A-Za-z]*e", token)) or (searcher and token in ("-t", "-T", "-A", "-B", "-C", "-m")):
                skip = "=" not in token
            elif "=" in token:
                found.add(i)
            continue
        if first_is_expression and not expression_given:
            expression_given = True
            continue
        found.add(i)
    return found


def segment_refused(segment: str, root: str, cwd: str, names: tuple) -> bool:
    for text in {segment, segment.replace("\\", "/")}:
        try:
            tokens = shlex.split(text, posix=True)
        except ValueError:
            tokens = text.replace("'", " ").replace('"', " ").split()
        program, rest, start = program_of(tokens)
        if not program or program in NAMES_ONLY or runs_the_stack(program, rest):
            continue
        if program == "mise" and rest[:1] in (["exec"], ["x"]) and "--" in rest:
            inner = rest.index("--") + 1
            program, rest, _ = program_of(rest[inner:])
            start = len(tokens) - len(rest)
            if not program or program in NAMES_ONLY or runs_the_stack(program, rest):
                continue
        if program in SHELLS:
            for i, token in enumerate(rest[:-1]):
                if token.lower() in SHELL_COMMAND_OPTIONS and shell_refused(rest[i + 1], root, cwd, names):
                    return True
        if program == "eval" and shell_refused(" ".join(rest), root, cwd, names):
            return True
        searcher = program in SEARCHERS
        if program == "printenv" and any(t.lower() in tuple(n.lower() for n in names) for t in rest):
            return True
        opens = {start + i for i in opened(program, rest)}
        for index, token in enumerate(tokens):
            if names_secrets(token, root, cwd, searcher, "full" if index in opens else "off") or expands_variable(token, names):
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
            if kind == "grep" and key == "pattern":
                continue
            value = given.get(key)
            if isinstance(value, str) and names_secrets(value, root, cwd, searcher=kind == "grep", wildcards="full" if key == "path" else "names"):
                return f"{tool} {key}"
    return ""


def decision(reason: str) -> str:
    """The hook's JSON decision that refuses a call."""
    return json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": reason}})


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read())
        if not isinstance(payload, dict):
            return 0
        what = refusal(payload)
        if what:
            print(decision(MESSAGE.format(what=what, folder=FOLDER)))
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
