# Environment lessons

Problems met while developing LATTICE, kept for the next agent who meets them. Each is general. A
note true of one machine belongs in that person's own configuration, not here.

## Python

- **Stdlib-only tools still run where packages cannot install.** `tools/literate_extract.py`,
  `tools/repository_topology_check.py` and similar scripts need only the standard library. Check
  before concluding that nothing can be run.
- **An AST-scan test can run without pytest**, by importing the test module and calling the test
  function, which is useful for probing a test against a deliberately broken implementation.
- **Write multi-line Python to a temporary file** rather than passing it to `python -c` from
  PowerShell, whose quoting mangles embedded quotes and newlines.
- **Guard "supplied or defaulted" at the CLI.** When a library function requires a parameter
  explicitly, the only place it can be silently defaulted, such as a `--now` flag defaulting to the
  wall clock, is the CLI's own argument handling.

## Templates and shapes

- **A mustache comment must not quote a real tag.** `chevron` parses `{{! … }}` bodies, so writing
  `{{{slot}}}` inside a comment opens a spurious tag. Describe the slot in words.
- **Jena SHACL reports the shape that carries the failing constraint.** A constraint nested as
  `sh:property [ … ]` under a named node shape reports the blank node as its source, not the named
  shape. Where a report's shape identifier matters, give each property constraint its own named,
  targeted shape.
- **Jena 5 SHACL's report entries** are `org.apache.jena.shacl.validation.ReportEntry`, with
  `focusNode()`, `source()`, `severity()` and `message()`. There is no nested `ValidationReport.Entry`.
- **networknt's JSON Schema validator** can preload a set of schemas by `$id`, with no network
  fetch, through `JsonSchemaFactory.builder(…).schemaLoaders(l -> l.schemas(map))`.

## Node and the frontends

- **`yarn --version` can block** at Corepack's download prompt and swallow the next command as its
  answer. Set `COREPACK_ENABLE_DOWNLOAD_PROMPT=0` first.
- **Playwright clears its output directory**, deleting the `.gitkeep` in
  `.build/*-test-results/`. Restore it with `git checkout` before committing.

## Windows

- **A shim is not the binary.** `mise`'s shims re-invoke `mise`, so they fail with "program not found"
  until the real `mise.exe` is on `PATH`. A newly installed `mise` is not on `PATH` in a terminal
  opened before the install.
- **Long paths are often off.** Install large toolchains, such as GHC or opam, under a short root.
- **opam's Cygwin before Git's** on `PATH`, or native OCaml's assembler and linker fail.
- **PowerShell `-File` passes `-X a,b` as one string**, and variable names are case-insensitive.
- **`openssl`** ships with Git for Windows if it is not otherwise on `PATH`. Add it at user level,
  never by hard-coding a path into a task.
