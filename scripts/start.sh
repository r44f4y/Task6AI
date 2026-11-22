#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
[[ -x .venv/bin/python && -d frontend/node_modules ]] || { echo "Run ./scripts/setup.sh first."; exit 1; }
mkdir -p .local
if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi
source scripts/ollama.sh
if [[ "${1:-}" == "--offline-demo" ]]; then
  export APP_MODE=offline_demo
else
  relay_start_ollama || echo "Ollama unavailable. See .local/ollama.log or select Offline demo in Settings."
fi
for port in 8000 5173; do
  if curl --noproxy '*' -sS --max-time 1 "http://127.0.0.1:$port/" >/dev/null 2>&1; then
    echo "Port $port is already occupied. Stop the existing server before starting Relay AI."
    exit 1
  fi
done
nohup .venv/bin/python -m uvicorn backend.main:create_app --factory --host 127.0.0.1 --port 8000 >.local/backend.log 2>&1 </dev/null &
echo "$!" >.local/backend.pid
nohup node frontend/node_modules/vite/bin/vite.js frontend --config frontend/vite.config.ts >.local/frontend.log 2>&1 </dev/null &
echo "$!" >.local/frontend.pid
for ((relay_poll=0;relay_poll<50;relay_poll++)); do
  if curl --noproxy '*' -fsS --max-time 2 http://127.0.0.1:5173/api/workflows >/dev/null 2>&1; then
    if [[ "${1:-}" == "--offline-demo" ]]; then
      curl --noproxy '*' -fsS -X PUT -H 'Content-Type: application/json' \
        -d '{"mode":"offline_demo","model":"qwen3:4b"}' http://127.0.0.1:5173/api/settings >/dev/null
    fi
    echo "Relay AI is running at http://127.0.0.1:5173"
    exit 0
  fi
  sleep .2
done
echo "Startup failed. See .local/backend.log and .local/frontend.log."
exit 1
