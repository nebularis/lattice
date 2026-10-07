# lattice repo — environment notes

- `mise` is not on PATH in this sandbox, and there is no system Python or `py` launcher.
- `uv` is available at `%USERPROFILE%\.local\bin\uv.exe`. `uv python install <ver> --system-certs`
  works (uses the OS cert store) and can fetch a Python build from GitHub releases successfully.
- However, `pypi.org`/`files.pythonhosted.org` package downloads are blocked by the network's
  proxy, which 307-redirects every request to a block-notice page.
  This is a deliberate network policy block, not a transient/technical issue — do not try to route
  around it (no alternate index, no manual wheel-URL fetch tricks). It affects `uv pip install`,
  plain `pip install`, and presumably any other PyPI-based installer.
- Net effect: `tools/persistence` (and likely other Python-based `tools/*` packages) cannot have
  their dependencies installed or their pytest suites run autonomously in this sandbox, even when
  the user grants "autonomous mode" for a slice. Do the code/test authoring work, verify with
  `get_errors` (static/import-level only), and hand off `mise run check:persistence` (or the
  equivalent) to the human to actually execute, being explicit that this is due to the network
  block, not a Default Mode choice.
- If a working venv with dependencies already exists somewhere in the repo from a prior human
  session, prefer reusing it over creating a new one.

## Plan execution pattern for this repo

- Plans under `docs/developer/plans/` routinely encode explicit multi-slice human validation
  gates ("no slice starts until X is reviewed"). When asked to "execute the plan in autonomous
  mode", treat that request itself as the go-ahead to author all slices, but still: (a) do not
  ratify ADRs yourself (leave status as Proposed), (b) flag any open design decision the plan
  left for human confirmation in the status record rather than silently picking one without a
  trace, (c) never claim a test/validation "passed" when it could not be executed here — say
  "authored, not yet executed" and hand off the exact command.
- Reference-resolver-style Python tooling for an ontology layer goes under `tools/<layer>/`
  mirroring `tools/persistence/`'s shape: `pyproject.toml` (setuptools, `src/<pkg>/` layout,
  a `test` extra with pytest/pyshacl), `README.md`, `src/<pkg>/{__init__,namespaces,model,...}.py`,
  `tests/conftest.py` with a `load_example`/`example` fixture pattern (no `__init__.py` in
  tests/, so use the pytest fixture, not a relative import, to reach conftest helpers). Wire
  `bootstrap:<pkg>` and `check:<pkg>` into `mise.toml`'s aggregate `bootstrap`/`check` tasks.
- Example: `tools/vocabulary/` (ADR-A85, scoped/temporal `voc:SchemeBinding` resolution) added
  2026-09-25 following exactly this template.
- A stdlib-only Python 3.11 interpreter IS available without any pip install:
  `%USERPROFILE%\.local\bin\python3.11.exe` (also at
  `%APPDATA%\uv\python\cpython-3.11.16-windows-x86_64-none\python.exe`), installed by `uv` in a
  prior session. Anything using only the standard library (argparse, re, pathlib, subprocess,
  tomllib, dataclasses — e.g. `tools/literate_extract.py`, `tools/repository_topology_check.py`,
  a new checker script) can actually be *run and validated* in this sandbox, not just
  statically reviewed. Only third-party packages (rdflib, pyshacl, pytest, etc.) are blocked.
  Always check for stdlib-only feasibility before assuming "no Python here."
- `tools/literate_extract.py --check` does **not** currently pass for Foundation/Vocabulary/Party
  (their `spec/*.ttl` predate the tool's own output format entirely — hand-authored/differently-
  generated Turtle, not a turtle-spec concatenation). Discovered 2026-09-25 while implementing
  `ontology-semantic-versioning`. Never run this tool in write mode against a layer without first
  running `--check` (with the correct `--shapes` arg count) and reading the diff — a real
  mismatch can silently blow away large amounts of unrelated hand-maintained content. For a
  narrow edit (e.g. bumping a version line) on a layer you haven't confirmed is clean, edit the
  README and generated file directly by hand instead.
- **Exception: Surface IS clean.** `python tools/literate_extract.py ontology/surface/README.md
  --layer surface --root ontology --shapes shapes/structural.ttl shapes/constraints.ttl --check`
  passes today (4 artefacts: spec/surface.ttl, vocab/surface-vocab.ttl, shapes/structural.ttl,
  shapes/constraints.ttl). For Surface specifically, always edit the README's turtle-spec/
  turtle-shapes/turtle-vocab blocks then regenerate via this exact command (write mode, no
  `--check`) rather than hand-editing the generated files — confirmed safe and used successfully
  in the `temporal-binding-consumer-hardening` unit. Note `srf:Law` individuals (R1, S2, etc.)
  live in the `turtle-vocab` block (→ `vocab/surface-vocab.ttl`), not `turtle-spec`.
- `--root` for `literate_extract.py` must be the `ontology/` directory (not repo root and not
  `.`), since the tool joins `--root` with a path like `surface/spec/surface.ttl` (no `ontology/`
  prefix baked in).
- A working stdlib-only Python 3.11 CAN run `test_architecture.py`-style AST-scan tests directly
  (no pytest needed): `python -c "import sys; sys.path.insert(0,'path/to/tests'); import
  test_architecture as t; t.test_foo()"`. Use this to mutation-probe such tests in-sandbox even
  though the full `rdflib`-dependent suite can't run.
- PowerShell here-strings (`@'...'@`) passed to `python -c` can mangle embedded quotes/newlines
  unpredictably in this tool's terminal — write a temp `.py` file instead (then delete it) for
  any multi-line Python snippet with string literals, rather than fighting `-c` quoting.
- **`tools/persistence` mustache templates**: a `{{! ... }}` comment must never quote a real tag's syntax as prose (e.g. writing `{{{mergeRelation}}}` inside the comment text to refer to that slot) — `chevron` does not treat the comment body as inert, so the embedded braces parse as a second, spurious tag and break rendering. Describe the slot in words instead. Confirmed 2026-09-25: this broke `key-claim-merge-rewrite.mustache` (authored autonomously, sandbox couldn't run tests to catch it), human fixed it, suite then passed (774/774). Also note: despite the PyPI block above, a human running outside this sandbox CAN and did successfully run `mise run check:persistence` — the block is sandbox-specific, not a repo-wide limitation.
- **SHACL-SPARQL authoring rules** (now in `.github/copilot-instructions.md`, learned from AIR-2.1
  verification defects — read that file's "Authoring SHACL-SPARQL shapes" section for the exact
  wording, but in short): (1) declare `PREFIX` lines inline at the top of every `sh:select`, never
  `sh:prefixes` pointing at a namespace IRI (pySHACL silently falls back to `@prefix` but other
  engines fail). (2) A counted pattern must be `OPTIONAL`, so a subject with zero matches still
  produces a row — otherwise "exactly one" silently passes for subjects with none. (3) One count:
  flat `OPTIONAL { ... } GROUP BY $this HAVING (COUNT(DISTINCT ?x) != 1)`. Two+ independent counts:
  one grouped sub-query per count, each anchored by re-asserting the subject's defining triple
  (e.g. `$this skos:inScheme ex:Scheme .`) before its own `OPTIONAL` — an unanchored sub-query
  drops zero-count subjects from the join. (4) Always write a negative test at zero, not just at
  "too many" — that's the case these bugs hide in.
- **No Java/Maven toolchain in this sandbox (superseded once mise is installed — see below).**
  Bare terminal has `mvn`/`mise` off PATH and only `java.exe` 1.8.0_491 (Client VM).
  `platform/pom.xml` needs `maven.compiler.release=25`, `mise.toml` pins `java = "25"`,
  `maven = "3.9"`. If `mise` truly isn't installed anywhere, hand off the command instead of
  attempting it.
- **Once a human has installed `mise` (e.g. via winget), it still isn't on PATH in an
  already-open terminal.** Binary lives at
  `%LOCALAPPDATA%\Microsoft\WinGet\Packages\jdx.mise_Microsoft.Winget.Source_*\mise\bin\mise.exe`
  — search `Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet" -Filter mise.exe -Recurse`, then
  prepend that directory to `$env:PATH` for the session. `%LOCALAPPDATA%\mise\shims\*.exe` exist
  too but are just shims that re-invoke `mise` internally, so they fail with "program not found"
  until the real `mise.exe` is on PATH — don't be fooled into thinking mise itself is missing.
  Once on PATH, `mise install` reports tools already installed and `mise -f platform/pom.xml ...`
  / `python -m pip` under the mise python work normally.
- **PyPI block now manifests as a pip hash mismatch, not a redirect notice.** Under mise's
  Python 3.14 + pip 26, `pip install <anything from PyPI>` fails with "THESE PACKAGES DO NOT
  MATCH THE HASHES FROM THE REQUIREMENTS FILE" even with no `-c`/hash-pinned requirements file
  given — pip fetched the real metadata (correct expected hash) but the proxy substituted the
  block-notice HTML page as the wheel body, so the downloaded bytes hash differently.
  Confirmed 2026-09-29 by fetching the exact `files.pythonhosted.org` wheel URL directly with
  `Invoke-WebRequest` and finding the response body is the same block-notice
  page, not the wheel. Same underlying network policy block as
  before, different symptom under mise. All `bootstrap:*` mise tasks that `pip install` from
  PyPI (python-root, workers, vocabulary, persistence, mork-compilers, surface, minting-python)
  will fail the same way until the human runs them off-network/VPN or via an allow-listed
  internal mirror. Don't waste time re-diagnosing as a corrupted-download or transient issue —
  it's deterministic (same wrong hash every retry).
- **`mise.toml` task glob-expansion bug (fixed 2026-09-29):** `check:ontology-catalog` used
  `tools/test_*.py`, a shell glob. Same class of bug as the pip-extras quoting bug above — bash
  expands it, `cmd.exe` (mise's default Windows shell) does not, and `pytest` doesn't glob its
  own args, so it failed with "file or directory not found". Fixed by enumerating the files
  explicitly in `mise.toml`. General rule: never rely on `mise.toml` `run` strings to shell-glob
  on Windows — enumerate explicitly, or the task silently does nothing/fails only on Windows.
- **`tools/reasoning_isolation_check.py` used raw `Path` in f-strings (fixed 2026-09-29):**
  `f"{relative}: declares {artifact}"` renders Windows backslash paths, but
  `test_reasoning_isolation.py` asserts forward-slash paths. Fixed with `.as_posix()`. General
  rule: any tool that prints a repo-relative path for a golden-file/assertion comparison must
  call `.as_posix()`, never rely on `str(Path)`.
- **`tools/spc/erlang` umbrella project is structurally broken on every OS, not just Windows**
  (found 2026-09-29, not yet fixed — needs a physical path move, which per repo topology
  governance needs human confirmation first): `mix.exs` declares `apps_path: "apps"`, but
  `spc_boundary/` and `spc_engine/` sit directly under `tools/spc/erlang/`, not under
  `tools/spc/erlang/apps/`. Every source file's own header comment (e.g. `# apps/spc_boundary/
  lib/...`) and `tools/spc/python/pipeline.sh` (`apps/spc_boundary/priv/...`) agree the intended
  path has `apps/` in it. Net effect: `mix test` silently finds zero apps and exits 0 — `check:spc`
  has been passing vacuously (0 tests run), not actually validating anything. Do not "fix" this by
  editing `mix.exs`'s `apps_path` instead of moving the directories, since every other reference
  (scripts, header comments) already assumes `apps/` is the real path.
- **`openssl` isn't on PATH on this machine but is bundled with Git for Windows** at
  `%LOCALAPPDATA%\Programs\Git\usr\bin\openssl.exe` (also `mingw64\bin`). Needed by
  `contracts/identity/verify-anchors.py` (`check:minting-anchors`). Fixed at the user-profile
  level (added to `$PROFILE`, same pattern as the mise PATH fix), not by hardcoding a path into
  any `mise.toml` task.
- **`bootstrap:mork` is blocked by a mirror-specific package gap, not a network policy block.**
  `tools/mork/pyproject.toml` (package name `mork-communities`) depends on `langchain-litellm`
  as a core (non-optional) dependency. The configured internal Artifactory PyPI mirror returns a
  consistent HTTP 403 fetching that one wheel (confirmed via direct `pip download`, not
  transient). This is the "specific dependency not available via a mirror" case documented in
  `.github/copilot-instructions.md`'s Toolchain section — hand off to the human/R rather than
  retrying. Downstream effect: `build:mtp`/`check:mtp` also fail (`No module named 'mtp'`),
  since the `mtp` package only gets installed as part of `tools/mork`'s install.
- **`mise run check` aborts all sibling tasks the moment any one task fails**, even parallel
  ones unrelated to the failure (e.g. `check:frontend`'s Node/corepack crash cut off
  `check:python-root` mid-run and never even started `check:java`/`check:spc`/etc.). Passing
  `--continue-on-error` did **not** change this in one observed run — still worth trying, but
  don't rely on the aggregate `check` task for a full picture when any known-broken task (like
  `check:frontend` here) is in the `depends` list. Run the remaining `check:*` tasks individually
  instead, e.g. `mise run check:java`, to get a true per-task pass/fail signal.
- **`yarn --version` on S blocks the terminal** at corepack's "download yarn? [Y/n]" prompt, and the
  next command typed is swallowed as the answer. Set `$env:COREPACK_ENABLE_DOWNLOAD_PROMPT = "0"`
  first, or avoid calling yarn until `NODE_EXTRA_CA_CERTS` is set (download fails on TLS anyway).
- **WA0 preflight on S (2026-10-01):** Maven Central resolves new artefacts (Javalin 6.7.0,
  Testcontainers 2.0.2, Jena 5.1.0 SHACL etc.). PyPI mirror serves rdflib, pika, jsonschema incl.
  rpds-py cp314. Docker Desktop is often not running (`dockerDesktopLinuxEngine` pipe missing):
  ask the human to start it, don't start it yourself. Edge is present for Playwright `msedge`.
- **Jena 5.1.0 SHACL: `ReportEntry.source()` (sh:sourceShape) is the shape that directly carries
  the failing constraint, not any enclosing named shape.** If a cardinality/datatype/class
  constraint is nested as `sh:property [ ... ]` (a blank node) under a named `sh:NodeShape`, every
  violation from it reports that blank node as `source()`, so regex-matching a shape's own IRI out
  of `source().toString()` (e.g. to recover a human-readable shape id) silently finds nothing for
  every "plain" property shape, while it works fine for constraints declared directly on the named
  shape (`sh:sparql`, `sh:xone`, etc., which aren't nested). Fix: give every plain property
  constraint its own top-level named shape (`sh:targetClass`/`sh:targetSubjectsOf` + `sh:path`
  directly on the named resource, no nested blank node). Found via the actual JUnit failures, not
  predictable from the API alone — when wiring up a SHACL validation report's shape-id extraction,
  write the test for it first and expect this exact failure mode.
- API classes for Jena 5.1.0 SHACL (`org.apache.jena.shacl`): `Shapes.parse(Graph)`,
  `ShaclValidator.get().validate(Shapes, Graph)` -> `ValidationReport`, whose `getEntries()`
  returns `Collection<org.apache.jena.shacl.validation.ReportEntry>` (NOT a nested
  `ValidationReport.Entry` — that class doesn't exist). `ReportEntry` has `.focusNode()`,
  `.source()`, `.severity()` (returns `org.apache.jena.shacl.validation.Severity`, compare against
  its static `Info`/`Warning`/`Violation` constants), `.message()`.
- networknt json-schema-validator 1.5.6: `JsonSchemaFactory.builder(JsonSchemaFactory.getInstance(SpecVersion.VersionFlag.V202012)).schemaLoaders(l -> l.schemas(mapOfIdToJsonString)).build()` then
  `factory.getSchema(URI.create(id))` works to preload a whole set of schemas keyed by `$id` with
  no network fetch, confirmed compiling and passing against real fixtures (not just plausible from
  memory).
- **`NODE_EXTRA_CA_CERTS` is now set at user level** (Zscaler root CA under
  `C:\Program Files (x86)\MSIRepair\Zscaler_Root_Certificate-*\`). A terminal opened before that
  lacks it: load it with `$env:NODE_EXTRA_CA_CERTS = [Environment]::GetEnvironmentVariable("NODE_EXTRA_CA_CERTS","User")`.
  Yarn 4.6.0 and the npm registry then work. Docker engine API on S is 1.56.
- **Formal-methods toolchains on S (2026-10-06, see `.local/formal-methods-toolchain-feasibility.md`):**
  Windows long paths are OFF (LongPathsEnabled=0, needs admin) -> install toolchains under a short
  root (`C:\fmx`); ghcup under `%LOCALAPPDATA%` failed on MAX_PATH. ghcup exe from
  downloads.haskell.org works (`GHCUP_INSTALL_BASE_PREFIX=C:\fmx`, then `ghcup set ghc`); Hackage OK.
  opam 2.6 Windows exe works (`opam init --cygwin-internal-install`, ~7 min; OCaml switch ~34 min).
  Native `ocamlopt` needs opam's `.cygwin\root\bin` AHEAD of Git's `usr\bin` on PATH (else as/flexlink
  fail: msys cygpath). Isabelle: TUM dist redirects to http host -> Zscaler 504; Cambridge mirror
  (`www.cl.cam.ac.uk/research/hvg/Isabelle/dist/`) works; extract with 7z, then run
  `java -Disabelle.root=... -cp contrib/isabelle_setup-*/lib/isabelle_setup.jar isabelle.setup.Setup classpath`
  once to trigger Cygwin init (errors after init, harmless). Docker pulls work; HTTPS INSIDE
  containers needs the Zscaler CA copied into the container + `NODE_EXTRA_CA_CERTS`. Direct
  registry.npmjs.org access is blocked entirely (307 to block page; npm reports EINTEGRITY).
  Reusable scripts, Dockerfiles and tests: `.local/formal-methods-spike/`. Native rocq-stdlib's
  `make install` copies one file per Cygwin process and crawls (endpoint scanning); prefer the
  container image for Rocq+Stdlib/MetaRocq. PowerShell gotchas hit: `-File` passes `-X a,b` as one
  string (split on commas), and `$tests`/`$Tests` are the same variable (case-insensitive).
- When a Python dataclass method needs a "was this explicitly supplied vs defaulted" distinction
  (e.g. a CLI `--now` flag defaulting to wall-clock time), put the guard at the CLI layer, not
  inside the library function — the library function typically already requires the parameter
  explicitly with no default, so the only place silent defaulting happens is the CLI's own
  argument-parsing/dispatch code.
- **`mise` tasks: `run_windows` + `shell = "powershell -c"` pattern, confirmed working
  2026-10-04.** Added `clean-win` (and `clean-win:python/frontend/build/docs`) as Windows-native
  equivalents of the POSIX `clean:*` tasks (which use `rm -rf`/`find -exec`, broken under
  `cmd.exe`). Wired `[tasks.clean]` with `run = [{ tasks = [...] }]` (not `depends` — `depends`
  always runs regardless of OS) plus `run_windows = [{ task = "clean-win" }]`, so Windows runs only
  `clean-win` and every other OS runs the original POSIX subtasks. Per-task `shell = "powershell
  -c"` forces Windows PowerShell 5.1 regardless of mise's own default-shell setting (`-NoProfile`
  is added automatically). **Gotcha:** `powershell -Command` sets the *process* exit code to 1 if
  *any* cmdlet raises a non-terminating error during the script, even one fully suppressed with
  `-ErrorAction SilentlyContinue` (e.g. `Remove-Item` on a path that doesn't exist) — confirmed by
  running the real task against a mix of existing/missing paths. Fix: put `$ErrorActionPreference
  = "SilentlyContinue"` as the first statement (not just per-cmdlet) and end the script with
  `exit 0`, mirroring the existing POSIX tasks' trailing `; true` for exactly the same reason.
  `mise tasks deps <task>` does not show tasks referenced via `run`'s `{ task = ... }`/`{ tasks =
  [...] }` form or via `run_windows` (only `depends` edges appear there) — expected per mise's own
  docs, not a bug.
- **The `clean*` tasks missed four real build-output locations (found and fixed 2026-10-04),
  worth about 33 MB uncompressed:** `.build/authoring/` (staged by `tools/authoring_stage.py` for
  the word-authoring-addin compose stack — 28.68 MB, the jar/wheels/addin dist copied there, not
  cleaned by anything before this fix), `apps/*/dist` (Vite build output, e.g.
  `apps/word-authoring-addin/dist`, 3.64 MB), `packages/minting/java/target` (a Maven module with
  its own `pom.xml`, entirely outside `platform/pom.xml`'s reactor, so `mvn -f platform/pom.xml
  clean` never touched it — fixed by adding a second `mvn -f packages/minting/java/pom.xml clean`
  step to `clean:java`), and `workers/build` (the intermediate dir `pip wheel --no-deps -w ...
  workers` leaves behind, from that same staging script). When adding a new `build:*`/staging task
  that writes outside the obvious `build/`/`.build/<name>/` convention, or a new Maven module not
  listed in `platform/pom.xml`'s `<modules>`, check `clean`/`clean-win` still cover it — there is
  no single generic glob that already catches everything, the tasks list exact paths on purpose
  (mirrors the repo's history of narrow, auditable rm lists rather than broad recursive globs).
  Verified with a repo-wide scan excluding `.git`/`node_modules` for dirs named
  `build|dist|target|__pycache__|*.egg-info|.pytest_cache`: zero matches after this fix, repo
  working tree (excl. `.git`) dropped from 44.98 MB to 12.2 MB.
- Running any `apps/word-authoring-addin` Playwright suite (`test:authoring-addin`,
  `check:authoring-stack`) deletes `.build/word-authoring-addin-test-results/.gitkeep` (Playwright
  clears its `outputDir` each run). Before committing, check `git status` for it and
  `git checkout -- .build/word-authoring-addin-test-results/.gitkeep` if deleted. The same likely
  applies to the other frontend workspaces' `.build/*-test-results/.gitkeep` files.
