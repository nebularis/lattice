# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Rank the knowledge index's entries by how close their meaning is to a question.

One model embeds both sides, so a question's vector can be compared with an entry's. It is
``BAAI/bge-small-en-v1.5`` (MIT licence), run from its ONNX export by onnxruntime, pinned by
revision and checked by SHA-256. It is fetched into ``.build/knowledge/model/`` on first use and
never committed (ADR-A134, addendum of 2026-10-26). A downstream index whose vectors are to be
compared with these must embed with the same revision, because vectors from two models do not share
a space.

An entry's text is its name, its claim and its problem shape. The vectors are written beside the
store, keyed by node and by a digest of that text, so a rebuild embeds only what changed.

Nothing here is a source. When the model cannot be fetched, the build records why and leaves no
vectors, and ``graph:ask -- find`` says so rather than ranking by something else.
"""

from __future__ import annotations

import hashlib
import shutil
import urllib.request
from pathlib import Path

import numpy as np
import pyoxigraph as ox

REPO = "BAAI/bge-small-en-v1.5"
REVISION = "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a"
FILES = {
    "onnx/model.onnx": "828e1496d7fabb79cfa4dcd84fa38625c0d3d21da474a00f08db0f559940cf35",
    "tokenizer.json": "d241a60d5e8f04cc1b2b3e9ef7a4921b27bf526d9f6050ab90f9267a1f9e5c66",
}
# The instruction the model was trained to read before a question, and never before a passage.
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
MODEL_DIR = Path(__file__).resolve().parents[2] / ".build" / "knowledge" / "model" / REVISION
VECTORS = "vectors.npz"

KI = "https://www.nebularis.org/neuro-semantic/lattice/dev/knowledge#"
TEXTS = f"""
PREFIX ki: <{KI}>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?n (SAMPLE(?l) AS ?label) (SAMPLE(?c) AS ?claim) (SAMPLE(?ps) AS ?shape) WHERE {{
  GRAPH ki:index {{
    ?n ki:identifier ?id ; ki:claim ?c .
    OPTIONAL {{ ?n rdfs:label ?l }}
    OPTIONAL {{ ?n ki:problemShape ?ps }}
  }}
}} GROUP BY ?n"""


class Unavailable(Exception):
    """The model cannot be fetched or run here, with the reason."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def fetch() -> Path:
    """The pinned model's directory, downloading any file that is missing.

    A file reaches its own name only after its SHA-256 matched, so one that is there is trusted
    without hashing 130 MB again on every question."""
    for name, digest in FILES.items():
        path = MODEL_DIR / name
        if path.exists():
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        url = f"https://huggingface.co/{REPO}/resolve/{REVISION}/{name}"
        part = path.with_name(path.name + ".part")
        try:
            with urllib.request.urlopen(url, timeout=120) as response, part.open("wb") as handle:
                shutil.copyfileobj(response, handle)
        except OSError as error:
            raise Unavailable(f"could not fetch {url}: {error}") from error
        if _sha256(part) != digest:
            part.unlink()
            # A proxy's block page arrives as a successful download, so this is its usual symptom.
            raise Unavailable(f"{url} does not match its pinned SHA-256, which a proxy block page also causes")
        part.replace(path)
    return MODEL_DIR


class Model:
    def __init__(self) -> None:
        try:
            import onnxruntime
            from tokenizers import Tokenizer
        except ImportError as error:
            raise Unavailable(f"{error.name} is not installed. Run mise run bootstrap") from error
        root = fetch()
        self.tokenizer = Tokenizer.from_file(str(root / "tokenizer.json"))
        self.tokenizer.enable_truncation(512)
        self.tokenizer.enable_padding()
        options = onnxruntime.SessionOptions()
        options.log_severity_level = 3
        self.session = onnxruntime.InferenceSession(
            str(root / "onnx" / "model.onnx"), options, providers=["CPUExecutionProvider"]
        )

    def embed(self, texts: list[str]) -> np.ndarray:
        """One unit vector per text: the model's first-token state, as bge is trained to give it."""
        out = []
        for start in range(0, len(texts), 32):
            encoded = self.tokenizer.encode_batch(texts[start : start + 32])
            feed = {
                name: np.array([getattr(e, field) for e in encoded], dtype=np.int64)
                for name, field in (
                    ("input_ids", "ids"),
                    ("attention_mask", "attention_mask"),
                    ("token_type_ids", "type_ids"),
                )
            }
            out.append(self.session.run(None, feed)[0][:, 0])
        vectors = np.vstack(out).astype(np.float32)
        return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)

    def question(self, text: str) -> np.ndarray:
        return self.embed([QUERY_PREFIX + text])[0]


def text_of(row) -> str:
    """Name, claim and problem shape, each once, in that order."""
    parts = [row[k].value.replace("**", "") for k in ("label", "claim", "shape") if row[k] is not None]
    return ". ".join(dict.fromkeys(p for p in parts if p))


def build(store: ox.Store, directory: Path) -> int:
    """Write the vectors of every entry with a claim beside the store, re-embedding only changed text.

    Returns how many texts were embedded this time. Raises Unavailable, having removed any vectors,
    so a stale set is never ranked against a changed index."""
    target = directory / VECTORS
    entries = {str(row["n"].value): text_of(row) for row in store.query(TEXTS)}
    digests = {node: hashlib.sha256(text.encode("utf-8")).hexdigest() for node, text in entries.items()}
    cached: dict[str, np.ndarray] = {}
    if target.exists():
        with np.load(target) as previous:
            if str(previous["revision"]) == REVISION:
                cached = dict(zip(previous["digests"].tolist(), previous["vectors"]))
    todo = sorted({d for d in digests.values() if d not in cached})
    if todo:
        try:
            model = Model()
        except Unavailable:
            target.unlink(missing_ok=True)
            raise
        by_digest = {digests[node]: text for node, text in entries.items()}
        for digest, vector in zip(todo, model.embed([by_digest[d] for d in todo])):
            cached[digest] = vector
    nodes = sorted(entries)
    np.savez(
        target,
        revision=np.array(REVISION),
        nodes=np.array(nodes),
        digests=np.array([digests[n] for n in nodes]),
        vectors=np.vstack([cached[digests[n]] for n in nodes]),
    )
    return len(todo)


def load(directory: Path) -> tuple[list[str], np.ndarray]:
    """The nodes and their vectors, or Unavailable if the build could not write them."""
    target = directory / VECTORS
    if not target.exists():
        raise Unavailable(f"no {VECTORS} beside the store. The build note says why")
    with np.load(target) as saved:
        if str(saved["revision"]) != REVISION:
            raise Unavailable("the vectors were made by another model revision. Rebuild the index")
        return saved["nodes"].tolist(), saved["vectors"]
