#!/usr/bin/env python3
"""The Persistence builds that `mise` runs, the same on Windows, Linux and macOS (STD-322).

`execution` compiles every example under the Persistence module's examples and writes its SPARQL and minting recipes
to the module's `execution` folder, which is generated and ignored by git (CAP-53). An example the compiler refuses
gets a `refused.txt` with the compiler's output instead.

`minting-vectors` compiles the identity-minting anchor and coverage fixtures and writes the committed recipes and
conformance vectors into the minting package's `testdata` (CAP-49).

Both run the Persistence command line, `python -m persistence`, with this interpreter, from the repository root."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lattice_repo_catalogue as rc  # noqa: E402

# The example that is compiled over another as a capability spec, never on its own.
CAPABILITY_SPEC = "capability-spec-example"
CAPABILITY_BASE = "baseline-single-class.ttl"
MINTING_FIXTURES = ("identity-minting-anchors.ttl", "identity-minting-coverage.ttl")


def persistence(root: Path, *args: str, capture: bool = False) -> subprocess.CompletedProcess:
    """`python -m persistence <args>` from the root, its output UTF-8 whatever the console's code page."""
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    if capture:
        return subprocess.run([sys.executable, "-m", "persistence", *args], cwd=root, env=env, text=True,
                              encoding="utf-8", errors="replace", stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return subprocess.run([sys.executable, "-m", "persistence", *args], cwd=root, env=env)


def without(text: str, folder: Path) -> str:
    """``text`` with the temporary folder's prefix taken out of every path, in either spelling of its separator."""
    for prefix in {f"{folder}{os.sep}", f"{folder.as_posix()}/"}:
        text = text.replace(prefix, "")
    return text


def execution(catalogue: rc.Catalogue) -> int:
    root = catalogue.root
    module = catalogue.module("persistence")
    spec = (module.directory("spec") / "persistence.ttl").as_posix()
    examples = module.directory("examples")
    out = root / module.path / "execution"
    if out.is_dir():
        for child in out.iterdir():
            if child.is_dir() and not child.name.startswith("."):
                shutil.rmtree(child)
    with tempfile.TemporaryDirectory() as scratch:
        temp = Path(scratch)
        for example in sorted((root / examples).glob("*.ttl")):
            name = example.stem
            source = (examples / example.name).as_posix()
            args = [(examples / CAPABILITY_BASE).as_posix(), "--capability-spec", source] if name == CAPABILITY_SPEC else [source]
            target = out / name
            target.mkdir(parents=True, exist_ok=True)
            compiled = temp / f"{name}.ttl"
            done = persistence(root, "compile", spec, *args, "--out", str(compiled), capture=True)
            if done.returncode != 0:
                (target / "refused.txt").write_text(without(done.stdout, temp), encoding="utf-8", newline="\n")
                continue
            made = persistence(root, "instantiate", str(compiled), "--out", str(target / "sparql"), capture=True)
            if made.returncode != 0:
                print(f"persistence instantiate failed for {name}:\n{made.stdout}", file=sys.stderr)
                return made.returncode
            persistence(root, "export-recipes", str(compiled), "--out", str(target / "recipes"), capture=True)
            recipes = target / "recipes"
            if recipes.is_dir() and not any(recipes.iterdir()):
                recipes.rmdir()
    return 0


def minting_vectors(catalogue: rc.Catalogue) -> int:
    root = catalogue.root
    module = catalogue.module("persistence")
    spec = (module.directory("spec") / "persistence.ttl").as_posix()
    fixtures = [(module.directory("examples") / name).as_posix() for name in MINTING_FIXTURES]
    testdata = catalogue.area("packages") / "minting" / "testdata"
    with tempfile.TemporaryDirectory() as scratch:
        compiled = Path(scratch) / "compiled.ttl"
        done = persistence(root, "compile", spec, *fixtures, "--out", str(compiled))
        if done.returncode != 0:
            return done.returncode
        for stale in [*(root / testdata).glob("*.recipe.json"), *(root / testdata).glob("*.vectors.json")]:
            stale.unlink()
        return persistence(root, "export-recipes", str(compiled), "--vectors", "--out", testdata.as_posix()).returncode


BUILDS = {"execution": execution, "minting-vectors": minting_vectors}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("build", choices=sorted(BUILDS))
    args = parser.parse_args(argv)
    return BUILDS[args.build](rc.load())


if __name__ == "__main__":
    sys.exit(main())
