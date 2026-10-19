<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Local Test Bed: Comparing Lattice to Knwler, TrustGraph, and Semantica on Document Ingestion

**Status:** Draft manual test script — not yet an ADR. This is a testing procedure document, intended to sit alongside (not replace) the architectural decision that should be recorded before Lattice's roadmap is influenced by these results.

---

## 1. Purpose and Scope

Compare document ingestion quality across four tools using the same working document set, run entirely on a local machine:

| Tool | Ingestion Model | Backend Graph Type |
|---|---|---|
| **Lattice** (ours) | — | — (fill in from internal docs) |
| **Knwler** | Chunk → LLM extract (entities/relations/topics) → consolidate | JSON graph; exportable to GML/GraphML/JSON-LD/RDF, Neo4j, SurrealDB, Neptune, GraphDB |
| **TrustGraph** | PDF/DOCX/XLSX/PPTX/HTML/MD/CSV/image ingest → ontology-grounded extraction | RDF 1.2 named graphs (quads) in Cassandra + Qdrant vectors, deployed via Docker |
| **Semantica** | `FileIngestor` → NER/relation/event extraction → `GraphBuilder` | Polyglot: RDF (Oxigraph/Blazegraph/Jena/RDF4J) or LPG (Neo4j/FalkorDB/AGE/Neptune) |

Because backends differ (LPG vs RDF quads vs JSON graph), **raw outputs are not directly comparable**. Section 5 defines a harmonized intermediate schema all four tools' outputs will be converted into before scoring.

---

## 2. Test Bed Directory Layout

```
lattice-ingestion-bench/
├── documents/                      # the shared working set (read-only, checksummed)
│   ├── manifest.csv                # filename, sha256, page_count, language, domain
│   └── *.pdf / *.docx / *.html ...
├── ground-truth/
│   ├── entities.csv                # hand/curated gold entities per document
│   ├── relations.csv               # hand/curated gold relations per document
│   └── notes.md                    # known ambiguous cases, adjudication rules
├── runs/
│   ├── lattice/<doc-id>/raw/...
│   ├── knwler/<doc-id>/raw/graph.json
│   ├── trustgraph/<doc-id>/raw/export.ttl
│   ├── semantica/<doc-id>/raw/kg.json
│   └── */<doc-id>/harmonized.json   # output of Section 5 normalizer
├── scoring/
│   ├── harmonize.py                 # tool-specific adapters → common schema
│   ├── score.py                     # precision/recall/F1 vs ground truth
│   └── results/<date>-<tool>.json
└── run-log.md                       # manual log: command run, timestamp, wall-clock time, errors
```

Create `documents/manifest.csv` first and freeze the working set (checksum) before any tool run, so all four tools ingest byte-identical inputs.

---

## 3. Per-Tool Setup and Ingestion Procedure

### 3.1 Knwler (`Orbifold/knwler`)

**Install (local, air-gapped-capable):**
```bash
# Python 3.12 required
uv sync                       # or: pip install knwler / pipx install knwler
```

**Local LLM backend (keeps comparison "fully local"):**
```bash
ollama pull llama3.2:latest
OLLAMA_NUM_PARALLEL=8 ollama serve
```

**Run per document:**
```bash
uv run main.py extract -f documents/<doc>.pdf \
  --backend ollama \
  --output runs/knwler/<doc-id>/raw/
```
Or batch the whole set:
```bash
uv run main.py extract --directory documents/ --backend ollama
```

**Output artifact:** `graph.json` (entities, relations, topics/clusters). Convert with:
```bash
uv run main.py graph convert --format jsonld   # optional, for RDF-based comparison
```

**Notes for the log:**
- Record model used (`--extraction-model` override if changed from default).
- Note cache hits — reruns are near-instant and free; log first-run wall-clock time only.
- Knwler auto-discovers entity/relation schema per run; log the discovered schema (`schema.entity_types`/`relation_types`) since it varies by document and affects comparability.

### 3.2 TrustGraph (`trustgraph-ai/trustgraph`)

**Install (Docker-based, heavier footprint):**
```bash
npx @trustgraph/config
# interactive config wizard produces deploy.zip
unzip deploy.zip -d trustgraph-deploy
cd trustgraph-deploy
docker compose up -d
```
This provisions Cassandra (graph store), Qdrant (vectors), Pulsar/RabbitMQ (messaging), and the inference stack (vLLM/TGI/Ollama depending on config choice — choose a **local** LLM option in the wizard to keep this comparable to Knwler's local run).

UI available at `http://localhost:8888` once containers are healthy.

**Ingestion:**
- Use the **Document Ingestion** UI panel (upload workflow with chunk/page inspection), or the CLI/API (`docs.trustgraph.ai/reference`) to submit each file in `documents/`.
- TrustGraph requires selecting a **Flow** and **Collection** before ingest — create one collection per test run so results don't bleed across documents.

**Export for comparison:**
- TrustGraph natively stores RDF 1.2 named graphs. Export via the Ontology Workbench or API as Turtle (`.ttl`) per collection.
- Record provenance separately if available (PROV-O) — useful bonus signal but not required for the harmonized schema.

**Notes for the log:**
- This is the heaviest deployment (multiple containers) — log container startup time separately from ingestion time so setup cost doesn't pollute the per-document ingestion metric.
- Log which LLM/OCR backend was configured (affects extraction quality independent of the graph engine itself).

### 3.3 Semantica (`semantica-agi/semantica`)

**Install:**
```bash
pip install semantica
semantica doctor      # verify install
```

**Ingest + extract + build KG (scriptable, no UI required):**
```python
from semantica.ingest import FileIngestor
from semantica.semantic_extract import NamedEntityRecognizer, RelationExtractor
from semantica.kg import GraphBuilder
from semantica.export import RDFExporter

docs = FileIngestor().ingest_directory("documents/", recursive=True)

ner = NamedEntityRecognizer(confidence_threshold=0.7)
rel = RelationExtractor(confidence_threshold=0.6, bidirectional=True)

kg = GraphBuilder(merge_entities=True).build(docs)   # or wire ner/rel explicitly per module docs

RDFExporter().export(kg.to_kg_dict(), "runs/semantica/<doc-id>/raw/kg.ttl", format="turtle")
```
Save a script per document (or looped over `manifest.csv`) under `runs/semantica/scripts/` so the exact extraction call is reproducible.

**Notes for the log:**
- Semantica's extraction is not purely LLM-driven by default (NER/relation extractors can be classical or LLM-backed depending on config) — record which extractor backend was used, since this materially affects the "apples to apples" claim vs Knwler/TrustGraph's LLM-first approach.
- Optionally launch the Knowledge Explorer (`semantica-explorer --graph kg.json`) for visual spot-checking during the qualitative review pass (Section 6).

### 3.4 Lattice

Fill in from Lattice's own CLI/API docs — keep the same structure: install command, local LLM/backend config, per-document ingestion command, and the raw output location. Since Lattice is 82.8% Python/7.8% Erlang, confirm whether ingestion is invoked via the Python tooling in `tools/` per the repo topology rule, and log that path here.

---

## 4. Manual Run Log Template

For every `(tool, document)` pair, record in `run-log.md`:

| Field | Example |
|---|---|
| Tool + version | knwler 1.1.0 |
| Document ID | doc-003 |
| LLM/backend used | ollama / llama3.2:latest |
| Command run | `uv run main.py extract -f ...` |
| Start / end timestamp | |
| Wall-clock duration | |
| Exit status / errors | |
| Output path | `runs/knwler/doc-003/raw/graph.json` |
| Anomalies observed | e.g. truncated output, schema drift, OOM |

This is manual, not automated — one row per run, filled in as you go.

---

## 5. Harmonizing Outputs for Comparison

Since Knwler emits a JSON property graph, TrustGraph emits RDF quads, and Semantica emits either RDF or LPG depending on config, define one **common intermediate schema** and write a small adapter per tool (`scoring/harmonize.py`):

```json
{
  "document_id": "doc-003",
  "entities": [
    {"id": "...", "name": "...", "type": "...", "source_span": "...", "confidence": 0.0}
  ],
  "relations": [
    {"source": "...", "predicate": "...", "target": "...", "confidence": 0.0}
  ]
}
```

Adapter responsibilities:
- **Knwler → harmonized:** direct mapping from `graph.json` entities/relations; types come from the auto-discovered schema.
- **TrustGraph → harmonized:** parse Turtle, map RDF classes/predicates to `type`/`predicate`, resolve blank nodes to stable IDs.
- **Semantica → harmonized:** `kg.to_kg_dict()` already close to this shape; map directly.
- **Lattice → harmonized:** define once Lattice's native output format is confirmed.

Normalize entity names (casing, whitespace) before comparison but keep an `original_name` field for audit.

---

## 6. Quality Evaluation Procedure

### 6.1 Quantitative (against ground truth)
1. Build `ground-truth/entities.csv` and `relations.csv` once, manually, per document (small working set — accept the manual cost).
2. Run `scoring/score.py` per tool's harmonized output:
   - **Entity precision/recall/F1** — fuzzy-match on normalized name + type.
   - **Relation precision/recall/F1** — match on (source, predicate, target) triple after entity alignment.
3. Record per-document and aggregate scores in `scoring/results/<date>-<tool>.json`.

### 6.2 Qualitative (spot-check, since automated matching won't catch everything)
For a sample of 3–5 documents per tool, manually review:
- **Entity disambiguation** — does the tool separate "Apple the company" from "apple the fruit" correctly? (Knwler explicitly claims this; check if TrustGraph/Semantica/Lattice do too.)
- **Relation plausibility** — spot-check relations for hallucination vs. text grounding.
- **Coverage** — does the tool miss whole sections (e.g. tables, footnotes)?
- **Provenance** — can you trace an extracted fact back to a source span/page? (TrustGraph and Semantica both advertise provenance; Knwler ties chunks to entities but check granularity.)

### 6.3 Cost / Performance Metrics (from the run log)
- Wall-clock time per document (excluding one-time setup like Docker startup or model download).
- Peak memory (if easily observable, e.g. `docker stats` for TrustGraph, `Activity Monitor`/`htop` for the others).
- Whether re-runs are cached/free (Knwler explicitly caches; check others).

---

## 7. Comparison Summary Table (fill in after runs)

| Metric | Lattice | Knwler | TrustGraph | Semantica |
|---|---|---|---|---|
| Setup time / complexity | | pip/uv, single process | Docker multi-container | pip, single process |
| Local LLM support | | Ollama / LM Studio | vLLM/TGI/Ollama (self-hosted) | configurable extractor backends |
| Entity F1 | | | | |
| Relation F1 | | | | |
| Entity disambiguation quality (qual.) | | | | |
| Provenance granularity | | chunk-level | PROV-O (fact-level) | PROV-O (fact-level) |
| Native graph model | | JSON property graph | RDF 1.2 quads | RDF or LPG (config) |
| Wall-clock (20-page PDF, local LLM) | | ~20–40 min (Ollama, per project's own benchmark) | | |

---

## 8. Open Questions to Raise Before Running This

Per the Agentic Development Contract, these are architectural questions, not implementation details — flag for discussion before treating results as decision-grade:
1. Should this comparison itself be the subject of an ADR (proposing it as a formal input to Lattice's ingestion design), or is it exploratory only?
2. Where should `lattice-ingestion-bench/` live — a new top-level dir, under `tools/`, or a separate repo entirely (given it's not a semantic asset per the `ontology/` vs `tools/` split)?
3. Is TrustGraph's Docker Compose footprint acceptable for "runs locally," or does its multi-container weight disqualify it from a fair head-to-head against the lightweight Knwler/Semantica installs?
4. What counts as "ground truth" authority — do we need a second reviewer to adjudicate the gold entity/relation set to avoid single-annotator bias?

---

**Next step suggestion:** I have not created any files or ADRs — this is presented for your review per the Design First rule. If you'd like, I can draft the accompanying ADR stub and commit this document (and the directory skeleton) to the Lattice repo once you confirm the target path and that an ADR should precede it.