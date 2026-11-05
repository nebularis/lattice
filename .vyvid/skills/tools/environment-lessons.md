Problems met while developing LATTICE, kept for the next agent who meets them.

## Python

- **Stdlib-only tools still run where packages cannot install.** `tools/literate_extract.py`, `tools/repository_topology_check.py` and similar scripts need only the standard library. Check before concluding that nothing can be run.

## Node and the frontends

- **A `.venv` made by `uv` has no pip, and parallel pip corrupts one.** Every Python `bootstrap:*` task depends on `bootstrap:pip`. Run several of them with `mise run --jobs 1`, because concurrent installs of two versions of a package (`pytest` showed it, as an `ImportError` in `_pytest`) interleave files. The repair is `rm -rf .venv && mise run bootstrap`.
