import hashlib
from pathlib import Path

from lattice_workers.graph_validation import GraphReference
from lattice_workers.surface_executor import FilesystemSurfaceOutputPublisher, SurfaceCompilerExecutor

GRAPH_BYTES = b"<https://example.test/graph> <https://example.test/p> <https://example.test/o> ."
GRAPH_DIGEST = f"sha256:{hashlib.sha256(GRAPH_BYTES).hexdigest()}"


class Materializer:
    def materialize(self, reference: GraphReference, destination: Path) -> Path:
        destination.write_bytes(GRAPH_BYTES)
        return destination


def graph(name: str) -> GraphReference:
    return GraphReference("tenant", "project", f"https://example.test/graphs/{name}", GRAPH_DIGEST)


def test_generation_uses_fixed_compiler_arguments_and_returns_output_digests(tmp_path):
    received = []

    def compiler(arguments):
        received.append(arguments)
        output_directory = Path(arguments[arguments.index("--out") + 1])
        output_directory.mkdir()
        (output_directory / "manifest.ttl").write_text("@prefix ex: <https://example.test/> .", encoding="utf-8")
        return 0

    outputs, diagnostics = SurfaceCompilerExecutor(Materializer(), compiler, tmp_path)("generation", graph("contract"), graph("profile"), [graph("source")], None)

    assert diagnostics == []
    assert received[0][0] == "compile"
    assert "--verify-determinism" in received[0]
    assert "--parity" in received[0]
    assert outputs[0]["digest"].startswith("sha256:")


def test_invalidation_requires_a_generated_manifest_reference(tmp_path):
    outputs, diagnostics = SurfaceCompilerExecutor(Materializer(), lambda arguments: 0, tmp_path)("invalidation", graph("contract"), graph("profile"), [], None)

    assert outputs == []
    assert diagnostics == ["invalidation requires a generated manifest graph reference"]


def test_hash_mismatch_prevents_compiler_execution(tmp_path):
    called = False

    def compiler(arguments):
        nonlocal called
        called = True
        return 0

    invalid = GraphReference("tenant", "project", "https://example.test/graphs/contract", "sha256:" + "a" * 64)
    outputs, diagnostics = SurfaceCompilerExecutor(Materializer(), compiler, tmp_path)("generation", invalid, graph("profile"), [], None)

    assert outputs == []
    assert called is False
    assert diagnostics == ["materialized graph hash does not match revision: https://example.test/graphs/contract"]


def test_path_escape_prevents_compiler_execution(tmp_path):
    class EscapingMaterializer:
        def materialize(self, reference, destination):
            escaped = tmp_path / "escaped"
            escaped.write_bytes(GRAPH_BYTES)
            return escaped

    outputs, diagnostics = SurfaceCompilerExecutor(EscapingMaterializer(), lambda arguments: 0, tmp_path)("parity", graph("contract"), graph("profile"), [], None)

    assert outputs == []
    assert diagnostics == ["materialized graph escaped the worker directory"]


def test_generation_publishes_content_addressed_output_outside_worker_directory(tmp_path):
    def compiler(arguments):
        output_directory = Path(arguments[arguments.index("--out") + 1])
        output_directory.mkdir()
        (output_directory / "manifest.ttl").write_text("@prefix ex: <https://example.test/> .", encoding="utf-8")
        return 0

    outputs, diagnostics = SurfaceCompilerExecutor(Materializer(), compiler, tmp_path, FilesystemSurfaceOutputPublisher(tmp_path / "published"))("generation", graph("contract"), graph("profile"), [], None)

    assert diagnostics == []
    assert outputs[0]["uri"].startswith("file:")
    published_file = tmp_path / "published" / "sha256" / f"{outputs[0]['digest'].removeprefix('sha256:')}.ttl"
    assert published_file.exists()
