#!/usr/bin/env bash
# scripts/pipeline.sh
# Full SPC design-time pipeline runner.

set -euo pipefail

SOURCE="${1:?Usage: pipeline.sh <source.ple> [output_dir]}"
OUTPUT_DIR="${2:-build}"
DOMAIN_ONTOLOGY="${DOMAIN_ONTOLOGY:-ontologies/insurance.ttl}"
TBOX="${TBOX:-ontologies/spc_core.ttl}"
FUSEKI_URL="${FUSEKI_URL:-http://localhost:3030}"
DATASET="${DATASET:-spc}"

echo "=== SPC Design-Time Pipeline ==="
echo "Source: ${SOURCE}"
echo "Output: ${OUTPUT_DIR}"
echo "Fuseki: ${FUSEKI_URL}/${DATASET}"

# Ensure Fuseki is running
if ! curl -sf "${FUSEKI_URL}/$/ping" > /dev/null 2>&1; then
    echo "ERROR: Fuseki not reachable at ${FUSEKI_URL}"
    echo "Start Fuseki with: fuseki-server --update --mem /${DATASET}"
    exit 1
fi

# Run the Python pipeline
spc pipeline "${SOURCE}" \
    --output-dir "${OUTPUT_DIR}" \
    --domain "${DOMAIN_ONTOLOGY}" \
    --tbox "${TBOX}" \
    --fuseki-url "${FUSEKI_URL}" \
    --dataset "${DATASET}"

echo ""
echo "=== Copying artifacts to runtime ==="

# Copy to the Elixir runtime's priv directory
RUNTIME_CONFIG="apps/spc_boundary/priv/config"
mkdir -p "${RUNTIME_CONFIG}"

cp "${OUTPUT_DIR}/protocol_tables.json" "${RUNTIME_CONFIG}/"
cp "${OUTPUT_DIR}/extensions.json" "${RUNTIME_CONFIG}/"
cp "${OUTPUT_DIR}/ingress_registry.json" "${RUNTIME_CONFIG}/"
cp "${OUTPUT_DIR}/egress/query_registry.json" "${RUNTIME_CONFIG}/"

# Copy shapes
RUNTIME_SHAPES="apps/spc_boundary/priv/shapes"
mkdir -p "${RUNTIME_SHAPES}"
cp "${OUTPUT_DIR}/shapes/"*.ttl "${RUNTIME_SHAPES}/" 2>/dev/null || true

# Copy egress templates and frames
RUNTIME_QUERIES="apps/spc_boundary/priv/queries"
RUNTIME_FRAMES="apps/spc_boundary/priv/frames"
mkdir -p "${RUNTIME_QUERIES}" "${RUNTIME_FRAMES}"
cp "${OUTPUT_DIR}/egress/queries/"*.rq "${RUNTIME_QUERIES}/" 2>/dev/null || true
cp "${OUTPUT_DIR}/egress/frames/"*.jsonld "${RUNTIME_FRAMES}/" 2>/dev/null || true

echo "Artifacts deployed to apps/spc_boundary/priv/"
echo "=== Done ==="