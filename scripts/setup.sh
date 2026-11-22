#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p .local
if [[ ! -f .env ]]; then cp .env.example .env; fi
set -a
source .env
set +a
python3 -m venv .venv
.venv/bin/python -m pip --disable-pip-version-check --no-cache-dir install -r backend/requirements.txt
npm --prefix frontend --cache "$PWD/.local/npm-cache" ci --no-audit --no-fund
if [[ "${1:-}" != "--offline-demo-only" ]]; then
  source scripts/ollama.sh
  if ! relay_prepare_ollama; then
    if [[ "$(uname -s)" != Darwin ]]; then echo "Install Ollama for this platform first."; exit 1; fi
    mkdir -p .local/ollama-bin
    curl -fL https://github.com/ollama/ollama/releases/latest/download/ollama-darwin.tgz -o .local/ollama-darwin.tgz
    tar -xzf .local/ollama-darwin.tgz -C .local/ollama-bin
    relay_prepare_ollama
  fi
  model="${OLLAMA_MODEL:-qwen3:4b}"
  .venv/bin/python -c 'import sys; from backend.schema import Settings; Settings(mode="local_ai", model=sys.argv[1])' "$model"
  relay_start_ollama || { echo "Ollama failed to start. See .local/ollama.log."; exit 1; }
  "$relay_ollama" show "$model" >/dev/null 2>&1 || "$relay_ollama" pull "$model"
else
  export APP_MODE=offline_demo
fi
.venv/bin/python -m scripts.seed_demo
echo "Setup complete. Run ./scripts/start.sh"
