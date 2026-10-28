<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Configuration Studio: Runbook

**Purpose:** Symptom, diagnosis and remedy for the problems met running the Configuration Studio
**Status:** Supported, single machine
**Companion:** [Configuration Studio operations guide](configuration-studio-operations.md), which has the ports, environment, paths and shutdown rules these procedures rely on

---

## Before any procedure

Run every command from the repository root and through `mise`. In the commands below, `RMQ` stands for the downloaded RabbitMQ's `sbin` directory, `.build/config-studio/infra/rabbitmq_server-4.4.0/sbin`, using the version `tools/config_studio_stack.py` pins. Where the stack runs with `--docker`, use the Docker form given.

```bash
mise run studio:status
```

shows each part's process id and whether its port is listening. A part that shows a process id and "not listening" has started and failed to serve. Its log is `.build/config-studio/run/{name}.log`.

```bash
tail -n 50 .build/config-studio/run/service.log
```

---

## Scenario 1: A port is already in use

**Symptom.** `studio:up` stops with "service: port 8090 is in use by another process" (or "web: port 4175" with `--dev`), or with "{name} did not listen on 127.0.0.1:{port}" and the last lines of the log. Or `up` prints "fuseki: already listening on 3130" or "rabbitmq: already listening on 5673" and starts nothing.

**Diagnosis.** The ports are `8090` (service), `4175` (dev server), `3130` (Fuseki), `5673` (RabbitMQ AMQP) and `25673` (RabbitMQ Erlang distribution). Find who holds the port.

```bash
lsof -nP -iTCP:8090 -sTCP:LISTEN
```

On Windows, `netstat -ano | findstr :8090`, then `tasklist /FI "PID eq {pid}"`.

Before it starts the service or the dev server, `up` refuses a port that a process it did not start holds, and skips one its own earlier `up` holds. For `3130` and `5673` it cannot tell, so "already listening" may be your own stack from an earlier `up`, a part you started in a terminal, or something else, and the studio then talks to whatever holds the port.

**Remedy.**

1. If the holder is the studio's own earlier stack, stop it.

   ```bash
   mise run studio:down
   ```

2. If the holder is another program, stop it, or free the port. The service's port can be moved with `LATTICE_STUDIO_PORT`, which the service and the dev server's proxy both read, but `studio:up` always waits for `8090` and reports its address as `8090`, so move it only when running each part in its own terminal, with the same value set for `studio:service` and `studio:web`. The ports of Fuseki and RabbitMQ are fixed in the script, the compose file and `mise.toml`, and are moved by stopping what holds them.
3. Start again, and check that the service is the studio's.

   ```bash
   mise run studio:up
   curl -s http://127.0.0.1:8090/api/health
   ```

   It answers `ok`. Anything else is not the studio.


---

## Scenario 2: A download is refused for its checksum

**Symptom.** `studio:up` prints `{url} has SHA-256 {actual}, not the pinned {expected}. Refused` and exits. No file is kept.

**Diagnosis.** The script downloaded a file whose SHA-256 is not the one pinned. Causes, in order of likelihood.

| Cause | Sign |
|---|---|
| A proxy, mirror or captive portal returned an HTML page or a different file | The `{actual}` differs on each try, or a download of the URL by `curl -sI` shows a content type of `text/html` |
| The download was cut short or corrupted | The `{actual}` differs on each try. A second `up` gets it right |
| The publisher replaced the file at that URL | The `{actual}` is the same on every try and on every network |
| The pin was edited wrongly | `git diff tools/config_studio_stack.py` shows a changed constant |

**Remedy.**

1. Run `mise run studio:up` once more. A refused download leaves no file, so nothing needs cleaning.
2. If it fails the same way, download the URL by hand on a network without a proxy into an empty directory outside the repository, and compare.

   ```bash
   shasum -a 256 {file}
   ```

   On Windows, `certutil -hashfile {file} SHA256`.
3. If the checksum differs from the pin on a clean network, do not edit the pin to match. Compare the file with the publisher's own digest (Maven Central's `.sha1` for Fuseki, the GitHub release's published SHA-256 for RabbitMQ). If the publisher's digest matches your file and not the pin, the pin is wrong or the release was replaced. Follow [Moving a pinned version](configuration-studio-operations.md#moving-a-pinned-version) and treat an unexplained replaced release as a report to the maintainer first.
4. Where a registry or proxy blocks the host from the machine but not from Docker, `mise run studio:up -- --docker` builds Fuseki's image with `ADD --checksum` against the same pin and pulls RabbitMQ's image.

---

## Scenario 3: RabbitMQ will not start

**Symptom.** `studio:up` stops with "rabbitmq did not listen on 127.0.0.1:5673" after up to 180 seconds, or at once with "RabbitMQ needs Erlang. Run this through mise, which installs it".

**Diagnosis.** Read RabbitMQ's two logs.

```bash
tail -n 50 .build/config-studio/run/rabbitmq.log
ls .build/config-studio/infra/rabbitmq/log
```

| Log or message shows | Cause |
|---|---|
| `RabbitMQ needs Erlang` | `erl` is not on the path. The script was run outside `mise`, or the Erlang toolchain is not installed |
| An error about `ERLANG_HOME`, or that `erl` cannot be found | `ERLANG_HOME` is wrong or points at a removed Erlang. The stack derives it from the `erl` on the path, so a bare shell with an old `ERLANG_HOME` exported, or a Erlang that mise has since replaced, causes this |
| `address already in use`, or `eaddrinuse` | Another program holds `5673` or `25673`. See Scenario 1 |
| `nodedown`, or the node name is already in use | A RabbitMQ node named `studio@localhost` is still running from an earlier start (a stale node) |
| `cookie` or `authentication failed` | The Erlang cookie does not match (see below) |

**Remedy.**

1. Erlang and `ERLANG_HOME`. Run through mise, and unset a stale variable.

   ```bash
   mise install
   mise exec -- erl -noshell -eval 'io:format("~s~n",[code:root_dir()]), halt().'
   mise run studio:up
   ```

   If your shell exports `ERLANG_HOME`, remove it. The stack sets its own.
2. A stale node. Look for an Erlang VM still running as `studio@localhost`.

   ```bash
   mise exec -- epmd -names
   ps aux | grep "[s]tudio@localhost"
   ```

   If the node answers, stop it cleanly.

   ```bash
   mise exec -- $RMQ/rabbitmqctl -n studio@localhost shutdown
   ```

   If `rabbitmqctl` cannot reach it, stop the process by its id with `kill {pid}`, wait a minute, and use `kill -9 {pid}` only if it is still there. Then remove a leftover pid file, `rm -f .build/config-studio/run/rabbitmq.pid`, and start again.
3. The Erlang cookie. `rabbitmqctl` and the node authenticate with the cookie in `~/.erlang.cookie` (`%USERPROFILE%\.erlang.cookie` on Windows). If the file was changed or deleted while the node was running, the node keeps the old cookie. Stop the node by its process id as above, which does not need the cookie, then start again. If the file's permissions are too open, Erlang refuses it. Restrict it to your user (`chmod 400 ~/.erlang.cookie`).
4. A broken data directory. If the log shows the node failing while recovering its data, and nothing in the queue matters, remove it and start again (Scenario 9, "Reset RabbitMQ only").

With Docker, `docker compose -f deployment/compose/config-studio/docker-compose.yml logs rabbitmq` is the log, and `docker compose -f deployment/compose/config-studio/docker-compose.yml up -d --wait` shows whether the health check passes.

---

## Scenario 4: RabbitMQ will not stop

**Symptom.** `studio:down` prints RabbitMQ's shutdown lines and then hangs, or prints "process {pid} did not stop within 60 s of SIGTERM, so it is killed", or a later `up` finds the port still listening.

**Diagnosis.** `down` runs `rabbitmqctl -n studio@localhost shutdown` and then ends the process group. If `rabbitmqctl` cannot reach the node (a cookie or node-name mismatch, or the node already gone), it fails quickly and `down` goes on to the signal. If the node is slow to stop, `shutdown` waits for it. An unclean stop is what the clean shutdown exists to avoid, and the next start recovers from it, which takes longer.

```bash
mise exec -- epmd -names
lsof -nP -iTCP:5673 -sTCP:LISTEN
```

**Remedy.**

1. Wait. A node with many messages or a slow disk may need a minute.
2. Try the shutdown yourself and read its message.

   ```bash
   mise exec -- $RMQ/rabbitmqctl -n studio@localhost shutdown
   ```

3. If it cannot reach the node because of the cookie or an `ERLANG_HOME` problem, follow Scenario 3, steps 1 and 3.
4. If the process remains, stop it by its id, `kill {pid}`, then `kill -9 {pid}` after a minute. Remove the stale pid file (Scenario 5) and run `mise run studio:status` to confirm nothing is listening.

On Windows `down` ends the tree at once after `rabbitmqctl shutdown` has returned, so a hang is in `rabbitmqctl` itself. Stop the tree by hand with `taskkill /PID {pid} /T /F`.

---

## Scenario 5: A stale process id file

**Symptom.** `studio:status` shows `running as {pid}` for a part that is not running, or `not started here` for one that is. `studio:down` stops a program you did not start.

**Diagnosis.** `.build/config-studio/run/{name}.pid` records the process id `up` wrote. The script treats a pid file as current if a process with that id exists, and does not record when the process started. If the part died (a crash, a reboot, `kill -9`) and the operating system has since given its id to another process, the file points at the wrong one, and `down` would send that process `SIGTERM` to its whole group. A file that names a process that has exited is harmless, and `status` and `down` ignore and remove it.

```bash
cat .build/config-studio/run/service.pid
ps -p $(cat .build/config-studio/run/service.pid) -o pid,command
```

**Remedy.**

1. Compare the command with what the part runs. The service is `java -jar .../config-studio-service.jar`, the worker `python -m lattice_workers.config_studio_main`, Fuseki `java -jar jena-fuseki-server-...jar`, and RabbitMQ an Erlang VM (`beam.smp`).
2. If the command is not the part's, delete the file before running `down`.

   ```bash
   rm -f .build/config-studio/run/service.pid
   ```

3. If the part is running but the file is missing, stop it by its process id, or find it with `lsof` for its port, and start again.
4. Run `mise run studio:down` and `mise run studio:status`. All five lines should read "not started here" with no port listening.

---

## Scenario 6: Jobs stay queued

**Symptom.** A validation or compilation never leaves `Queued` in the Build view, and `GET /api/jobs/{job}` shows `cst:status cst:Queued` and no `cst:startedAt`.

**Diagnosis.** A job is written to Fuseki as queued, its IRI is published to RabbitMQ, and only a worker moves it on. Check the three links in order.

1. Did the service start with an AMQP URI? Without `LATTICE_AMQP_URI`, the service records jobs and never delivers them.

   ```bash
   grep "LATTICE_AMQP_URI is not set" .build/config-studio/run/service.log
   ```

   `studio:up` and `studio:service` set it, so this means the service was started by hand without the variable.
2. Is a worker connected? The worker stops at start if `LATTICE_AMQP_URI` or `LATTICE_FUSEKI_URL` is unset ("is required"), and stops if it meets an unexpected error, such as Fuseki being unreachable, after returning the message to the queue.

   ```bash
   mise run studio:status
   tail -n 30 .build/config-studio/run/worker.log
   mise exec -- $RMQ/rabbitmqctl -n studio@localhost list_queues name messages consumers
   ```

   `lattice.studio.jobs` should show `consumers` 1. With 0, no worker is connected, and `messages` counts the jobs waiting.
3. Do the service and worker agree? Their `LATTICE_FUSEKI_URL`, `LATTICE_FUSEKI_DATASET` and `LATTICE_AMQP_URI` must name the same Fuseki, dataset and broker. A worker on a different dataset consumes the message and fails it with "job graph not found", which moves it to the dead-letter queue (`lattice.studio.dead`) rather than leaving it queued.

**Remedy.**

1. No AMQP URI in the service. Restart the service with the stack's values. With `mise run studio:service` they are set. Then resubmit the job, since the queued jobs of the old run were never published.
2. No worker. Start one.

   ```bash
   mise run studio:worker
   ```

   Or stop and start the whole stack. A worker that starts takes the messages already in the queue, since they are persistent.
3. A worker that keeps stopping on the same message has met an error it requeues, and the message returns to the queue and is delivered again. Read the end of `worker.log` for the error. If it is Fuseki being unreachable, start Fuseki. If the message itself is the cause, remove it.

   ```bash
   mise exec -- $RMQ/rabbitmqctl -n studio@localhost purge_queue lattice.studio.jobs
   ```

   Docker form: `docker compose -f deployment/compose/config-studio/docker-compose.yml exec rabbitmq rabbitmqctl purge_queue lattice.studio.jobs`. The jobs it held stay `Queued` in Fuseki. Delete them in the browser, or resubmit.
4. Messages in `lattice.studio.dead`. These are messages the worker rejected as malformed or naming a missing job graph. Their jobs were deleted, or are from before a Fuseki restart. Clear them with `purge_queue lattice.studio.dead`.

---

## Scenario 7: A job fails

**Symptom.** A job reaches `Failed`, and the Build view shows a message.

**Diagnosis.** There are two outcomes that look alike and are different.

| Outcome | Meaning |
|---|---|
| `cst:Succeeded` with `cst:conforms false` | The job ran. The configuration does not validate or compile. The report lists each finding. This is an authoring result, not an operation problem |
| `cst:Failed` with `cst:failureMessage` | The job could not run. The message says why |

Read the message. Fetch the job from the service.

```bash
curl -s http://127.0.0.1:8090/api/jobs/{job} | grep -i "failureMessage\|status"
```

| `failureMessage` | Cause and remedy |
|---|---|
| `the job could not be handed to the worker: {exception}` | The service wrote the job but could not publish it to RabbitMQ, or the broker did not confirm within five seconds. The broker is down or stalled. Check Scenario 3, then resubmit |
| `configuration graph {iri} not found` | The job's input graph is missing. The job was deleted while queued, or Fuseki was restarted between submission and the run (Scenario 8). Resubmit |
| `job lacks a known kind, a known target or a submission time` | The job graph is malformed, which a job the service wrote does not produce. Delete it and resubmit, and report it with the logs (Scenario 10) if it recurs |
| Any other text | An error from the validation or compilation itself. Read `.build/config-studio/run/worker.log`, and report it with the logs |

A job that fails is final. The worker does not retry it. Resubmit from the browser, or with `POST /api/workspaces/{ws}/jobs`. A job the worker had not finished when it stopped is redelivered and run again, giving the same graph but for its times.

---

## Scenario 8: The browser shows an error from the service

**Symptom.** The browser application shows an error whose text is the service's response, or a "graph changed" conflict message.

**Diagnosis.** The service's own text is in the response body, and the status says what an author should do.

| Status | Means | What the author does |
|---|---|---|
| `400` | The body did not parse as its `Content-Type`, or it was RDF/XML with a DTD, or a job's `kind` or `target` is not one the service accepts, or the `Slug` is not percent-encoded UTF-8 | Fix the Turtle or RDF/XML syntax at the line the service's log reports. Remove a DTD. A job with another kind or target is a browser fault and a report |
| `404` | The workspace or job is unknown, or a route does not exist, or `/api/vocabulary` or `/api/samples` has no staged file | The workspace was deleted or Fuseki was restarted (Scenario 9). For the vocabulary or samples, run `mise run build:config-studio-assets` and restart the service |
| `405` | The method is not allowed on that path. The `Allow` header lists those that are | A browser fault. Report it |
| `406` | The author asked for RDF/XML, and the graph holds a predicate RDF/XML cannot write, one whose IRI does not end in an XML name | Fetch it as Turtle. The graph is not damaged |
| `412` | The save named a revision, in `If-Match`, that is no longer current. The workspace was saved from another tab, window or session since this one loaded it | Reload the graph, re-apply the change, and save. The response's `ETag` names the current revision. A graph with a subject of another part gets `422` even when its revision is also stale |
| `413` | The body is over 5 MiB | Split the configuration, or remove data that does not belong in it. The limit is fixed |
| `415` | The `Content-Type` is not `text/turtle` or `application/rdf+xml` | A browser fault when it comes from the application. Report it. From a script, set the header |
| `422` | A saved graph holds a subject that belongs to another part by the rule the browser's import uses. The text names up to five | Move that subject to the part it belongs to, or remove it |
| `428` | The save had no `If-Match` header | A browser fault when it comes from the application. From a script, send the revision's `ETag` in `If-Match` |
| `500` | An unexpected error in the service. The response says only `internal error` | The cause is in `service.log`. Collect it (Scenario 10) |
| A gateway error from the dev server, or a network error | In the dev server, the service is down or has not finished starting. With the built application, the service itself is unreachable | `mise run studio:status`. Start or restart the service |

---

## Scenario 9: Workspaces are lost after a restart

**Symptom.** After `studio:down` and `studio:up`, or a restart of Fuseki alone, the workspace list is empty, a workspace the browser had open answers `404`, and saved jobs are gone.

**Diagnosis.** Fuseki's dataset is in memory (`--mem`). Stopping Fuseki, for any reason, empties it, and nothing is written to disk. A persistent dataset is planned work, not yet built. If the service was started without `LATTICE_FUSEKI_URL`, it holds an in-memory dataset of its own and loses it when it exits, and the worker, which needs Fuseki, cannot read its jobs.

**Remedy.** There is no recovery of lost workspaces. To avoid it, keep the configuration as Turtle files in the repository, upload it to a new workspace, and download or copy the edited graphs out of the browser before stopping Fuseki. After a restart, create the workspace again from the sample or the uploaded files. Restarting only the service, the worker or RabbitMQ does not lose workspaces. The queue's persistent messages survive a RabbitMQ restart, while their jobs live in Fuseki.

---

## Scenario 10: Resetting everything

Use the smallest reset that fits.

| Reset | Commands |
|---|---|
| Restart, losing the workspaces | `mise run studio:down` then `mise run studio:up` |
| Clear the job queue only | `mise exec -- $RMQ/rabbitmqctl -n studio@localhost purge_queue lattice.studio.jobs`, and the same for `lattice.studio.dead` |
| Reset RabbitMQ only | `mise run studio:down`, then `rm -rf .build/config-studio/infra/rabbitmq`, then `mise run studio:up`. The node starts with empty data |
| Reset everything, keeping the downloads | `mise run studio:down`, then `rm -rf .build/config-studio/run .build/config-studio/infra/rabbitmq .build/config-studio/infra/fuseki-base`, then `mise run studio:up` |
| Reset everything, downloads too | `mise run studio:down`, then `rm -rf .build/config-studio`, then `mise run studio:up`. This downloads about 80 MB again and rebuilds the staged assets |
| Docker | `mise run studio:down`, which runs `docker compose down`. The compose file declares no volumes, so Fuseki and RabbitMQ start empty on the next `up --docker` |

On Windows, delete the directories with `Remove-Item -Recurse -Force`. Always run `studio:down` first. Deleting `.build/config-studio/run` while the stack runs leaves processes the script no longer knows, which then hold their ports (Scenario 1). `mise run clean` removes `.build/config-studio` among other build output.

If you deleted the run directory with the stack up, find the processes by their ports (`lsof -nP -iTCP:8090 -iTCP:3130 -iTCP:5673 -sTCP:LISTEN`) and stop them with `kill`. For RabbitMQ use `rabbitmqctl shutdown` first.

---

## Scenario 11: Collecting logs for a report

**Symptom.** A fault you cannot resolve, and a report to the maintainers.

**Procedure.** Record the state, then bundle the logs.

```bash
mise run studio:status > studio-status.txt
mise exec -- java -version 2> studio-versions.txt
mise exec -- python --version >> studio-versions.txt
mise exec -- erl -noshell -eval 'io:format("~s~n",[erlang:system_info(otp_release)]), halt().' >> studio-versions.txt
git rev-parse HEAD >> studio-versions.txt
tar -czf studio-logs.tgz studio-status.txt studio-versions.txt .build/config-studio/run .build/config-studio/infra/rabbitmq/log
```

With Docker, add the containers' logs.

```bash
docker compose -f deployment/compose/config-studio/docker-compose.yml logs --no-color > studio-docker.log
```

Add the request that failed with its status and body (`curl -si ...`), the time, and what the author did. The logs hold the service's errors with their stack traces, the Turtle syntax errors the service met in submitted bodies, the worker's output and Fuseki's request log. They can hold fragments of the author's configuration, so read them before sending them anywhere, and send nothing that is confidential. They do not hold the AMQP password.
