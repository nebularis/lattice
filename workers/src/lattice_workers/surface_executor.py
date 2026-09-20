"""Trusted execution adapter for existing Surface compiler operations."""

from __future__ import annotations

import hashlib
import shutil
import tempfile
from pathlib import Path
from typing import Callable, Protocol, Sequence

from .graph_validation import GraphReference


class GraphMaterializer(Protocol):
    """Resolves an authorized immutable graph reference to canonical local bytes."""

    def materialize(self, reference: GraphReference, destination: Path) -> Path:
        """Write canonical bytes below destination whose SHA-256 equals revision_hash."""


class GraphMaterializationError(ValueError):
    """Raised when a materialized file cannot prove its immutable graph reference."""


class SurfaceCompilerRunner(Protocol):
    """Runs a fixed argument vector against the existing Surface compiler."""

    def __call__(self, arguments: Sequence[str]) -> int:
        """Return the compiler exit status without accepting untrusted commands."""


class SurfaceOutputPublisher(Protocol):
    """Persists verified compiler output outside the worker temporary directory."""

    def publish(self, source: Path, media_type: str, digest: str) -> dict[str, str]:
        """Persist source by digest and return a stable output descriptor."""


class SurfaceCompilerExecutor:
    """Executes graph-reference jobs using fixed CLI argument construction."""

    def __init__(self, materializer: GraphMaterializer, compiler: SurfaceCompilerRunner, work_root: Path | None = None, output_publisher: SurfaceOutputPublisher | None = None):
        self._materializer = materializer
        self._compiler = compiler
        self._work_root = work_root
        self._output_publisher = output_publisher

    def __call__(
        self,
        job_type: str,
        contract_graph: GraphReference,
        profile_graph: GraphReference,
        source_graphs: list[GraphReference],
        manifest_graph: GraphReference | None,
    ) -> tuple[list[dict[str, str]], list[str]]:
        if job_type not in {"generation", "parity", "invalidation"}:
            return [], [f"unsupported Surface job type: {job_type}"]
        with tempfile.TemporaryDirectory(dir=self._work_root) as temporary:
            try:
                work_directory = Path(temporary)
                contract_path = self._materialize(contract_graph, work_directory, "contract")
                profile_path = self._materialize(profile_graph, work_directory, "profile")
                source_paths = [self._materialize(reference, work_directory, f"source-{index}") for index, reference in enumerate(source_graphs)]
                declarations = [str(contract_path), str(profile_path)]

                if job_type == "generation":
                    output_directory = work_directory / "generated"
                    status = self._compiler(["compile", "--contracts", *declarations, "--sources", *map(str, source_paths), "--out", str(output_directory), "--verify-determinism", "--parity"])
                    diagnostics = self._diagnostics(status)
                    return ([] if diagnostics else self._outputs(output_directory)), diagnostics
                if job_type == "parity":
                    status = self._compiler(["parity", "--contracts", *declarations, "--sources", *map(str, source_paths)])
                    return [], self._diagnostics(status)
                if manifest_graph is None:
                    return [], ["invalidation requires a generated manifest graph reference"]
                manifest_path = self._materialize(manifest_graph, work_directory, "manifest")
                status = self._compiler(["check", "--manifest", str(manifest_path), "--contracts", *declarations, "--sources", *map(str, source_paths)])
                return [], self._diagnostics(status)
            except GraphMaterializationError as error:
                return [], [str(error)]

    def _materialize(self, reference: GraphReference, work_directory: Path, name: str) -> Path:
        destination = work_directory / name
        materialized = self._materializer.materialize(reference, destination).resolve()
        if not materialized.is_relative_to(work_directory.resolve()):
            raise GraphMaterializationError("materialized graph escaped the worker directory")
        if not materialized.is_file():
            raise GraphMaterializationError("materializer did not return a graph file")
        actual_hash = f"sha256:{hashlib.sha256(materialized.read_bytes()).hexdigest()}"
        if actual_hash != reference.revision_hash:
            raise GraphMaterializationError(f"materialized graph hash does not match revision: {reference.graph_iri}")
        return materialized

    @staticmethod
    def _diagnostics(status: int) -> list[str]:
        return [] if status == 0 else [f"Surface compiler exited with status {status}"]

    def _outputs(self, output_directory: Path) -> list[dict[str, str]]:
        if not output_directory.exists():
            return []
        outputs = []
        for path in sorted(output_directory.rglob("*.ttl")):
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            descriptor = {"mediaType": "text/turtle", "digest": f"sha256:{digest}"}
            outputs.append(self._output_publisher.publish(path, descriptor["mediaType"], descriptor["digest"]) if self._output_publisher else descriptor)
        return outputs


class FilesystemSurfaceOutputPublisher:
    """Reference publisher that retains output by digest for local integration tests."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def publish(self, source: Path, media_type: str, digest: str) -> dict[str, str]:
        filename = digest.removeprefix("sha256:") + ".ttl"
        destination = self._root / "sha256" / filename
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            shutil.copyfile(source, destination)
        return {"mediaType": media_type, "digest": digest, "uri": destination.resolve().as_uri()}
