#!/usr/bin/env bash
# Pull required Ollama models for JobAI.
# Idempotent: skips models already present.
# Usage:
#   ./scripts/ollama-pull-models.sh                    # uses http://localhost:11434
#   OLLAMA_BASE_URL=http://ollama:11434 ./scripts/ollama-pull-models.sh

set -euo pipefail

OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"

MODELS=(
  "nomic-embed-text"   # embeddings — 274 MB
  "mistral:7b"         # LLM FAST tier — 4.1 GB
)

echo "→ Ollama base URL: ${OLLAMA_BASE_URL}"

wait_for_ollama() {
  echo "→ Waiting for Ollama to be ready..."
  for i in $(seq 1 30); do
    if curl -sf "${OLLAMA_BASE_URL}/api/tags" > /dev/null 2>&1; then
      echo "✓ Ollama is ready."
      return 0
    fi
    echo "  attempt ${i}/30 — retrying in 5s"
    sleep 5
  done
  echo "✗ Ollama did not become ready in time." >&2
  exit 1
}

is_model_present() {
  local model="$1"
  curl -sf "${OLLAMA_BASE_URL}/api/tags" \
    | grep -q "\"name\":\"${model}" 2>/dev/null
}

pull_model() {
  local model="$1"
  if is_model_present "${model}"; then
    echo "✓ Model '${model}' already present — skipping."
  else
    echo "→ Pulling model '${model}'..."
    curl -sf "${OLLAMA_BASE_URL}/api/pull" \
      -d "{\"name\":\"${model}\"}" \
      | grep -E '"status"' || true
    echo "✓ Model '${model}' pulled."
  fi
}

wait_for_ollama

for model in "${MODELS[@]}"; do
  pull_model "${model}"
done

echo ""
echo "✓ All models ready."
