<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: SVA-X5, the secret-read guard's false refusals and its failure when it cannot run

**Unit:** [`studio-visual-authoring`](../status/studio-visual-authoring.md), slice SVA-X5, built on 2026-11-26 in autonomous mode. It fixes the two faults the maintainer reported that day in the guard SVA-H1 built, and builds what the maintainer decided on the same day. The slice's row already reads `building 2026-11-26`.

## Invariant

A call that does not open the studio stack's secrets is never refused, and a call that does is refused as before. A guard that cannot run lets the call through and says so. `tools/secret_read_guard.py` matches a wildcard by path segment, against the working directory and the repository root only, and tests it only where the program opens what the token names. It takes the root from the call's working directory first. It refuses through the hook's JSON decision and exits 0. The hook command in `.claude/settings.json` runs the script only where the file exists and `mise` is found, and otherwise prints a `systemMessage` and exits 0.

## The faults

**Fault 1, false refusals.** The wildcard branch of `names_secrets` matched a pattern with `fnmatch` against the stack's files under the checkout's absolute path, so a wildcard whose literal text occurs in that path was refused, for example `*sploot*` in a worktree named `studio-sploot` and `*lattice*` in every checkout. `fnmatch`'s `*` crosses `/`, which a shell glob's does not, so `*studio*`, `*broker*`, `*config*`, `*secret*` and `pass*` matched. A second test put `*/` in front of the pattern, so `[a-z]*` matched every target. The test applied to every token of every program, including programs that never open a file a pattern names, and Grep's regular expression was checked as if it were a path.

**Fault 2, a guard that cannot run blocks the session.** The hook command ran the script without checking that it exists. Python exits 2 when it cannot open its script, and the harness reads 2 from a hook as a refusal. In one session `CLAUDE_PROJECT_DIR` still named an earlier checkout after a move, the script there was gone, and every call failed.

## What changed

- **`tools/secret_read_guard.py`.** `segments_match` and `wildcard_names` are the matcher. `opened` says which tokens of a program a wildcard may name. `root_of` takes the working directory first. `decision` and `main` give the JSON decision. The program lists `READERS`, `FINDERS`, `EXPRESSION_FIRST`, `EXPRESSIONS` and `SHELLS` are new. The docstring says what the guard checks, how a wildcard is matched and where it is tested, how it refuses, how it fails and what it cannot catch.
- **`.claude/settings.json`.** The hook command, below.
- **`tools/test_secret_read_guard.py`.** 337 tests, 260 more than the 77 it held. The 28 spellings of a read keep their verdicts. One case changed, see choice 1.
- **No skill text.** No file under `.claude/skills` describes the guard, so none changed. The operator guide does not mention it either.

The hook command, one line of POSIX `sh`, so no script beside the guard is needed:

```sh
f="$CLAUDE_PROJECT_DIR/tools/secret_read_guard.py"; if [ ! -f "$f" ]; then w="the script is missing"; elif ! command -v mise >/dev/null 2>&1; then w="mise is not found"; elif o=$(mise exec -- python "$f"); then printf '%s' "$o"; exit 0; else w="the run exited non-zero"; fi; printf '{"systemMessage": "secret_read_guard did not run (%s), so this call was not checked"}\n' "$w"; echo "secret_read_guard did not run ($w), so this call was not checked" >&2; exit 0
```

It prints the guard's standard output only when the run exits 0, so a script that prints half a decision and then exits 2 gives the warning and no decision. It uses no program that could be missing, since `[`, `command`, `printf`, `echo` and `exit` are built into the shell.

## The decisions as built

1. **A wildcard is matched by path segment.** `*`, `?` and `[...]` match inside one segment with `fnmatch.fnmatchcase`, and a segment `**` stands for any number of segments, none included. The pattern is made relative to the working directory and to the root. Its leading `..` segments climb the anchor, the folders it keeps are compared as literal text, and the rest is matched against the rest of the target's segments. The checkout's own text is therefore never a pattern, and a root named `[a-z]*` changes no verdict. A pattern is never prefixed with `*/`. `pathlib.PurePath.full_match` exists in the checkout's Python 3.14.10, and the matcher is written out anyway, since `mise` may give another interpreter and the matcher is tested directly.
2. **A wildcard is tested only where the program opens what it names.** These are the readers (`cat`, `head`, `sed`, `cp`, `tar`, `Get-Content` and the like), the file operands of a searcher, the start points of `find`, and the path of the Read, Grep and Glob tools. The pattern or script that is the first operand of a searcher, `sed`, `awk` or `jq` is skipped unless an option gave it, and so are the values of `--list`, `--grep`, `--glob`, `--include`, `-name`, `-iname`, `-path`, `-regex`, `-g`, `-Filter` and the like. `git`, `echo`, `ls` and any program no list names are never tested for a wildcard, a `git log` pathspec after `--` among them. The string after `bash -c`, `pwsh -Command` and `eval`, and the command after `mise exec --`, are checked as a command of their own, so a wildcard in them is tested by the program it reaches. A literal path into the folder is refused for every program as before.
3. **Grep's `pattern` is never read as a path.** Grep is checked by `path`, with the wildcard test, and by `glob`, with the wildcard test against the stack's folder and its files. Glob's `pattern` is a path and is checked as before, against the folder and its files.
4. **The root comes from the call's `cwd` first**, the repository root above it found as before, and `CLAUDE_PROJECT_DIR` only where `cwd` is absent, empty or not a string.
5. **A refusal is the hook's JSON decision.** The guard prints `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "<the line it gave before>"}}` and exits 0, with nothing on standard error. Every other outcome exits 0 with nothing on standard output.
6. **A guard that cannot run lets the call through with a warning.** The command above, for a missing script, a missing `mise` and a non-zero exit.

## Choices the brief did not settle

1. **One existing case is now allowed.** A Grep with the pattern `infra/broker/password` and no path was refused, and decision 3 makes it a regular expression that opens nothing, so it is allowed and its test case is removed from the refused list. The same text as a Grep `path`, or as a Bash command, is still refused.
2. **The length rule is gone.** A wildcard was tested only if it held three literal characters, to hold down false refusals. Matching by segment makes the rule unneeded, so `cat *` from inside the folder is now refused, which it was not before.
3. **A command run from inside the folder is refused, whatever it is.** Every literal token is resolved against the working directory, as before, so `git log` run there is refused for naming `log`. Only `ls`, `rm` and the like and the commands that run the stack are allowed. The brief asks only for `cat pass*` there, and the rule is not changed.
4. **The guarded files outside the folder count for a wildcard only where the program opens it.** Glob and Grep's `glob` list or filter names, so `**/*studio*` is allowed although it would match the name `rabbitmq-studio.conf`, and `cat .build/config-studio/infra/compose/rabbitmq-s*.conf` is refused.
5. **A wildcard that matches the folder's files is allowed for a program no list names**, and for `echo`, `ls` and `git`, since none opens a file by it. The shell expands an unquoted pattern for any program, so `echo .build/*/infra/*/pass*` prints the names and no content. An unknown program that opens a file by a pattern is not caught, and the docstring says so.
6. **Grep's `password.*` with no path and `secret` over `docs` were allowed before** in the three roots built here, under the old code run from the same inputs. They are tested anyway, as the report names them.

## Verdicts of the inputs the brief lists

Each input was run through the old guard (`git show HEAD:tools/secret_read_guard.py`, `CLAUDE_PROJECT_DIR` set to the root) and the new one, with the call's `cwd` set to the root, from a Python file with no pattern on a command line. The three roots were folders with an empty `mise.toml`, named `studio-sploot`, `lattice` and `plain`. Where the roots differ the old verdict is given for each in that order.

| Input | Before | After, in all three roots |
|---|---|---|
| Bash `git branch -a --list '*sploot*'` | deny, allow, allow | allow |
| Bash `git branch -a --list '*studio*'` | deny in all | allow |
| Bash `git branch --list '*lattice*'` | allow, deny, allow | allow |
| Bash `find . -name '*broker*'` | deny in all | allow |
| Bash `find docs -name '*config*'` | deny in all | allow |
| Bash `git log --oneline -- '*secret*'` | deny in all | allow |
| Bash `git log --grep 'pass*'` | deny in all | allow |
| Bash `echo [a-z]*` | deny in all | allow |
| Glob `**/*studio*` | deny in all | allow |
| Glob `*config-studio*` | deny in all | allow |
| Grep pattern `password.*`, no path | allow in all | allow |
| Grep pattern `secret`, path `docs` | allow in all | allow |
| Bash `ls *work*` | allow in all | allow |
| Bash `git for-each-ref 'refs/heads/*sploot'` | allow in all | allow |
| Glob `**/*broker*.py` | allow in all | allow |
| Glob `**/*.md` | allow in all | allow |
| Bash `cat .build/config-studio/infra/broker/password` | deny in all | deny |
| Bash `cat .build/*/infra/*/pass*` | deny in all | deny |
| Bash `cat .build/config-studio/infra/broker/*` | deny in all | deny |
| Bash `cat pass*`, `cwd` the folder | deny in all | deny |
| Read of `.build/config-studio/infra/broker/password` | deny in all | deny |
| Grep, `path` the folder | deny in all | deny |

## Tests

All are in `tools/test_secret_read_guard.py`. A test that takes a root runs under the three roots, built in the test as folders with a `mise.toml` inside the test's temporary folder, with `CLAUDE_PROJECT_DIR` naming the real checkout so a stale project directory is part of every case.

| ID | Given / When / Then | Level | The break tried | The failure it gave |
|---|---|---|---|---|
| X5-T1 | the harmless commands of the report and more names, expressions and patterns that match nothing / Bash and PowerShell, each root / allowed | L1, positive | the matcher made to let a star cross a slash | 70 failures over six tests, the matcher's and the refused cases among them |
| X5-T2 | the inputs of Glob, Grep and Read that read nothing of the folder / each root / allowed | L1, positive | Grep's `pattern` read as a path again | `test_a_glob_a_pattern_and_a_regular_expression_that_read_nothing_of_the_folder_are_allowed_under_each_root`, 3 failures, the regular expression `infra/broker/password` refused |
| X5-T3 | wildcards that name the folder or a file in it, given to a reader, a searcher, `find`, a shell string, `mise exec` and `eval` / each root / refused | L1, negative | a leading `*/` put before each pattern | 63 failures, the refused cases among them, since `**` and the anchor no longer lined up |
| X5-T4 | the folder by each tool, with the working directory the root, the folder and `tools` / each root / refused or allowed as stated | L1, negative and positive | the project directory put before `cwd` | 4 failures, in this test and in T9 |
| X5-T5 | 26 patterns and paths / `segments_match` / the rule for `*`, `?`, `[...]`, `**`, `..` and an embedded `**` | L1, positive and negative | a star made to cross a slash | `test_a_wildcard_is_matched_by_path_segment` fails, with the others in T1 |
| X5-T6 | 24 patterns, three roots whose own text holds `studio-sploot`, `[a-z]*` and a drive letter / `wildcard_names` / the verdict does not change with the root, and a pattern is resolved against the working directory and the root only | L1, positive and negative | a leading `*/` put before each pattern | `test_a_wildcard_is_resolved_against_the_working_directory_and_the_root_only` fails for every root |
| X5-T7 | 22 programs and their operands / `opened` / the positions a wildcard may name, and none for `git`, `echo`, `ls` and an unknown program | L1, positive and negative | the option values no longer skipped | 2 failures, `test_a_wildcard_is_tested_only_where_the_program_opens_what_it_names` |
| X5-T8 | a pattern that matches the folder's files, given to `echo`, `git`, `find -path` / each root / allowed | L1, positive | every token tested as a wildcard | 12 failures, all in T1's test, and no other |
| X5-T9 | a stale project directory, a missing one and no `cwd` / `root_of` and the guard / the working directory decides first, the project directory only without one | L1, positive and negative | the project directory put before `cwd` | `test_the_root_comes_from_the_calls_working_directory_before_the_project_directory` and T4 fail |
| X5-T10 | a refusal as a process and in process / the output / one JSON object with the three fields, exit 0, nothing on standard error, and nothing on standard output for an allowed call | L1, positive and negative | a refusal made to exit 2 with a line on standard error | 108 failures, `test_a_refusal_is_the_hooks_json_decision_and_the_exit_status_is_0` among them |
| X5-T11 | the hook command run through `sh`, with `CLAUDE_PROJECT_DIR` naming a folder without the script, a script that exits 2 after printing, a script that raises and a script with a syntax error / the command / exit 0, the system message with the reason, a line on standard error, and none of the script's output | L1, negative | the old hook command put back | 4 failures, `test_a_guard_that_is_missing_lets_the_call_through_with_a_warning` among them |
| X5-T12 | the command with no `mise` on the path / exit 0 and the message `mise is not found` | L1, negative | the old hook command put back | `test_a_mise_that_is_not_found_lets_the_call_through_with_a_warning` fails |
| X5-T13 | the real guard under the command, on a Read of the folder, a Bash that is allowed and input that does not parse / the decision as the guard gives it, and exit 0 with nothing for the other two, once through a stand-in `mise` that runs the test's interpreter and once through the real `mise` | L2, positive and negative | a refusal made to exit 2 | both tests fail, with T10's |

The 28 spellings, the working-directory cases, the Read, Grep and Glob cases and the cases that run the stack are the tests of SVA-H1 (H1-T7 to H1-T15), with the verdict read as the JSON decision. Their status is now `deny` and `allow` and not 2 and 0.

## Checks run

On 2026-11-26. Every output was read whole.

| Command | Result |
|---|---|
| `mise exec -- python -m pytest tools/test_secret_read_guard.py -q` | 337 passed, 13 warnings from a dependency, in about 1 second |
| the breaks above | each applied alone and the file restored after it, and the suite put back to 337 passed |
| `mise run check:config-studio`, run alone | exit 0 in 170.55s. Python 586 passed. The app's check, 36 test files and 564 tests passed. `check:authoring-domain`, 4 files and 21 tests passed. The Java modules print no counts through the task, and no failure or error line other than the logged errors of the tests that provoke them |
| `mise run check:identifiers` | passed, 2399 identifiers in 1009 files, 0 unresolved, 0 defined twice |
| `mise run check:published-decisions` | passed, 6 tests, `sources: 0 failure(s)` |
| `mise exec -- python tools/writing_rules.py docs/developer/validation/SVA-X5.md` | 0 failures, 0 warnings |

The reviewer ran these again on 2026-11-26: the guard's tests 337 passed, `check:config-studio` exit 0 with 586 Python tests, the Java modules' 9, 254, 10 and 85 tests with none failing, and the app's 564 tests, `check:identifiers` and `check:published-decisions` passed, and the writing rules on this pack with no finding. The reviewer also ran the hook command from `.claude/settings.json` through `sh` on a Bash call that names the folder by a literal path, and it printed the deny decision and exited 0. The session that reviewed it had started outside the checkout, so its harness loaded no project hooks and could not show that a deny decision at exit 0 is honoured.

## Left open

- A live check in a session started in the checkout, that a call naming the folder is refused with the guard's reason and a harmless wildcard such as `git branch --list '*studio*'` is allowed.

- **A hook is never exercised by a live harness here.** The tests run the command through `sh` and the guard as a process. Whether a harness reads `permissionDecision` of `deny` on standard output at exit 0 as a refusal is the harness's documented behaviour and was not shown by a call refused in this session.
- **The guard still cannot catch** a wildcard given to a program no list names, a wildcard in a value it takes for a name, a Grep `glob` without a slash (ripgrep matches it at any depth, the guard anchors it), a pattern whose `..` follows a wildcard segment, and the rest the docstring lists.
- **The SVA-H1 pack** still says the guard exits 2, and its test names that expect it. That pack is the record of its build and is not changed.
- **`mise run check:config-studio` printed no Java test counts**, so none are given.

## Placement

T0. The guard, its tests and the hook belong to the studio's open developer tooling. The pack carries no third-party material, and nothing in it comes from a wording, a form or a client's document.
