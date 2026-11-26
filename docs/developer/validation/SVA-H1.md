<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: SVA-H1, the studio stack's secrets out of the files people read, one redacted way to read its settings, and a guard on reading the secrets

**Unit:** [`studio-visual-authoring`](../status/studio-visual-authoring.md), slice SVA-H1, built on 2026-11-15 in autonomous mode. It follows a task that read the stack's generated broker configuration, which held the broker user's password in clear, and so printed it into a tool's output.

## Invariant

Every secret the stack keeps is in one owner-only folder, `.build/config-studio/infra/broker`, and no file a person is told to read holds one. The broker's main configuration, `infra/rabbitmq/rabbitmq.conf`, names no password and no path that carries the service's broker secret, and the broker loads those from `infra/broker/rabbitmq-secret.conf` beside it through `RABBITMQ_CONFIG_FILES`. What the stack prints about itself, `mise run studio:config`, goes through one function, `redact`, which replaces each secret value it holds and the password of any `scheme://user:password@`. A Claude Code `PreToolUse` hook, `tools/secret_read_guard.py`, refuses a shell command, a Read, a Grep or a Glob that names that folder, a file that holds a secret or a variable that carries one's path, and allows the commands that run the stack, list names or delete.

## What changed

- **`tools/config_studio_stack.py`.** `BROKER_CONF` keeps the user, the backends, `auth_http.http_method`, MQTT and Web MQTT. `BROKER_SECRET_CONF` holds `default_pass` and the four `auth_http.*_path` lines, which embed the service's broker secret. `rabbitmq_env` writes the second with `write_private` and names it in `RABBITMQ_CONFIG_FILES`. `broker_conf()` is the first and `broker_secret_conf(host)` the second. The subcommand `config`, `redact` and `describe_uri` are new.
- **`mise.toml`.** The task `studio:config`, and `tools/test_secret_read_guard.py` in `check:config-studio`.
- **`tools/secret_read_guard.py` and `.claude/settings.json`.** The guard, a second `PreToolUse` entry with the matcher `Bash|PowerShell|Read|Grep|Glob` that runs it through `mise exec` and does nothing where `mise` is not on the path, and `permissions.deny` rules for the Read tool on the folder and on the compose broker's configuration.
- **`docs/operator/configuration-studio-operations.md`.** Where the secrets are kept, that the main configuration holds none, `RABBITMQ_CONFIG_FILES`, and `studio:config`.

## Tests

| ID | Given / When / Then | Level | Pass |
|---|---|---|---|
| H1-T1 | a stack with credentials / `broker_conf()` and `broker_secret_conf(host)` / the first names the user and the backends and holds no `default_pass`, no `/api/broker/` and neither secret, and the second holds the password and the four paths under the secret | L1, positive | `test_the_brokers_main_configuration_holds_no_secret_and_the_secret_part_is_private` |
| H1-T2 | a stack that writes its broker environment / `rabbitmq_env` / the main file holds no secret value and no `default_pass`, `RABBITMQ_CONFIG_FILES` names the owner-only secret file in forward slashes, and the file starts with the password | L1, positive | `test_a_stack_the_script_starts_loads_the_secret_part_beside_a_main_file_that_names_none` |
| H1-T3 | secrets, a URI and texts around them / `redact` / each secret, in its plain and percent-encoded form and with nothing around it, becomes `<redacted>`, a `scheme://user:password@` loses its password for any scheme, and a text with none is returned unchanged | L1, positive and negative | `test_redaction_hides_each_secret_a_uri_and_leaves_a_text_without_one_alone` |
| H1-T4 | a URI / `describe_uri` / its scheme, user, host, port and path, and the password as `<redacted>` | L1, positive | `test_a_uri_is_described_without_its_password` |
| H1-T5 | a stack with credentials, a main file that holds a secret by mistake and no broker running / `config` / the settings print, the leaked value is redacted, each secret shows `<redacted, N characters>`, no value, no whole URI and no `default_pass` is in the output, and the limits say the broker is not running | L1, positive | `test_the_config_command_prints_the_settings_and_no_secret` |
| H1-T6 | a stack with no credentials made / `config` / it makes none, says each is not made yet and still prints | L1, negative | `test_the_config_command_makes_no_secret_and_says_so_when_there_is_none` |
| H1-T7 | the 28 spellings of a read: relative, `./`, absolute, through `..` and `//` and `/./`, quoted in parts, with Windows separators, redirected, as an option's `=` value, in `bash -c`, `python -c` and `$( )`, after an allowed command, by a glob, through each `*_FILE` variable and the two others, by `printenv`, the secret and compose configuration files, and a recursive search from `.build` / Bash and PowerShell / exit 2 and one line on standard error that names `mise run studio:config` | L1, negative | `test_each_way_of_reading_the_secrets_from_the_shell_is_refused` |
| H1-T8 | a working directory inside the stack's folders / a relative path / exit 2 | L1, negative | `test_a_command_run_from_inside_the_stacks_folders_is_refused_by_its_working_directory` |
| H1-T9 | six spellings of a file's path / Read / exit 2 | L1, negative | `test_a_read_of_a_file_in_the_folder_is_refused` |
| H1-T10 | the folder or a folder that holds it, as a path, a glob or a pattern / Grep and Glob / exit 2 | L1, negative | `test_a_search_of_the_folder_or_a_folder_that_holds_it_is_refused`, `test_a_glob_of_the_folder_is_refused` |
| H1-T11 | `ls` and `rm` of the folder, `mise run studio:*`, `config_studio_stack.py`, a search for a variable's name, a recursive search from the root, the main configuration | L1, positive | `test_the_commands_that_run_the_stack_list_names_or_delete_pass` |
| H1-T12 | unrelated calls, an Edit of a guarded path, empty and malformed input, and a fault inside the guard / the hook / exit 0 and no output | L1, positive | `test_an_unrelated_call_passes`, `test_input_the_guard_cannot_parse_passes`, `test_a_fault_inside_the_guard_passes` |
| H1-T13 | a command that holds a made-up secret and a guarded path / the refusal / the line holds no part of the call | L1, negative | `test_the_refusal_holds_no_part_of_the_call` |
| H1-T14 | `mise.toml` / the guard's variables / the ones `mise.toml` assigns a path in the folder, and the defaults where it is missing | L1, positive | `test_the_variables_are_read_from_mise_toml` |
| H1-T15 | the script as a process with no `PATH` / a refused Read, an allowed command and `{` / exit 2 with one line, and exit 0 with nothing | L1, positive and negative | `test_the_hook_exits_2_with_one_line_as_a_process_and_0_otherwise` |
| H1-T16 | a stack started on a fresh broker node / `up`, then a request to the service / the broker loads its user and password from the secret file, the service, writer, workers and transforms connect with the stored credentials, and the service answers `200` | L3, positive | by hand, under Results |

**The one command:** `mise exec -- python -m pytest tools/test_config_studio_stack.py tools/test_secret_read_guard.py -q`, from the repository root. `mise run check:config-studio` runs both with the rest of the studio's checks.

## Artefacts to inspect

- `tools/config_studio_stack.py`, the templates `BROKER_CONF` and `BROKER_SECRET_CONF`, `rabbitmq_env`, `redact` and `Stack.config`.
- The output of `mise run studio:config`, with the stack up and down. It is the way to see the stack's settings. Do not open `.build/config-studio/infra/broker`.
- `.claude/settings.json`, the second `PreToolUse` entry and `permissions`.
- The docstring of `tools/secret_read_guard.py`, which lists what it cannot catch.

## Deliberate non-coverage

- **The guard is a seatbelt.** It cannot catch a path built at run time, an interpreter that opens a file by a computed name, a `cd` into `infra` followed by a read of `broker` in a later call, a read through a symbolic link, a wildcard whose literal text is under three characters, or a recursive search from the repository root with a searcher that does not honour `.gitignore`. It refuses a command that merely names the folder in an `echo` or a `python -c`, since it cannot tell a name from a read. It runs only where the client runs the project's hooks and `mise` is on the path.
- **The compose broker.** `compose_up` still writes both parts into the one owner-only file `infra/compose/rabbitmq-studio.conf`, because `deployment/compose/config-studio/docker-compose.yml` mounts one file at `conf.d/30-studio.conf` and that file is outside this slice. The guard and the deny rule cover the file. Splitting it needs a second mount in the compose file, which the official image would load as another file of `conf.d`. This variant, with and without `--docker`, and `infra`, were not run here.
- **Windows.** The glob in `RABBITMQ_CONFIG_FILES` is written in forward slashes and `rabbitmqctl.bat` is used where the script already used it. Neither was run on Windows. The PowerShell tool is covered by the guard's tests on its separators only.
- **A broker whose data an older stack made.** `ensure_broker_user` still passes the password to `rabbitmqctl add_user` as an argument, which a process list shows for an instant. It runs only for a broker that lacks the user, never for a new one, and was not changed.
- **`mise run studio:config` inside `mise run`.** The task cannot read the broker's limits where Erlang is not on the path, as in this environment, and says so. The limits were read by running the script under `mise exec` with Erlang added to the path.
- **A broker's limits beyond four.** Web MQTT's frame and message settings are not read.

## Results

What the builder ran on 2026-11-15, in autonomous mode:

- **Mechanism.** In RabbitMQ 4.4.0, `RABBITMQ_CONFIG_FILE` names the main file and `RABBITMQ_CONFIG_FILES` a file or a glob of files loaded with it. This was shown on a scratch node, ports of its own, a throwaway password and a main file with no `default_pass`. `rabbitmqctl authenticate_user` accepted the user with the password the second file held, and refused a wrong one. The shipped scripts name neither variable, so the fallback of setting the password with `rabbitmqctl` after start was not needed.
- `mise exec -- python -m pytest tools/test_config_studio_stack.py tools/test_secret_read_guard.py -q`, `95 passed` (18 and 77), and it was run again after the settings and the task were added.
- `up` on a fresh node, under `mise exec` with Erlang added to the path, built the application and exited 0. `studio:status` showed fuseki, rabbitmq, writer, service, worker, worker-long, transforms and add-in running, and `web` not started. `GET /api/status` with the developer principal answered `200`. The writer, service, worker, worker-long and transforms logs held no refusal or authentication failure, and the broker's log held none and 38 lines naming the user `studio`.
- A check in Python that prints only a verdict. The main `rabbitmq.conf` holds none of the four secret values and no `default_pass`, `True`, and the secret file holds a `default_pass` line, `True`.
- `studio:config` with the broker up, 49 lines, none holds a secret value or `default_pass`, `True`. Run with Erlang on the path it printed `max_message_size` 16777216, MQTT authenticated packet size 16777216, unauthenticated 65536 and `mailbox_soft_limit` 200, in 51 lines, with the same verdict `True`. Run through `mise run`, which resets the path, it said the limits were not read.
- `down` stopped every part and the broker through `rabbitmqctl shutdown`, and `studio:status` showed nothing running. `studio:config` with the stack down printed the rest and said the broker was not running, 49 lines, verdict `True`.
- The guard by hand, from input files. `cat ./.build/config-studio/infra/../infra/broker/password` as a Bash call, exit 2. `rm -f` of one file in the folder and `mise run studio:config` in one command, exit 0 and no output. A Grep with an absolute path to the folder, exit 2. Each refusal printed the one line naming `mise run studio:config`.
- `ontology/mork/mtp/data/pins.lock.json` was not rewritten by any check.
- Not run: `mise run check:config-studio` as a whole, the compose variants, Windows, and any run of the stack in a browser.

## Follow-up, 2026-11-26

SVA-X5 changed how the guard refuses and what it matches. It refuses through the hook's JSON deny decision and exits 0, matches a wildcard by path segment against the working directory and the repository root, and a guard that cannot run lets the call through with a warning. Where this pack says the guard exits 2, read [SVA-X5](SVA-X5.md).
