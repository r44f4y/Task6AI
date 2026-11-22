#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
for service in frontend backend ollama; do
  file=".local/$service.pid"
  if [[ ! -f "$file" ]]; then continue; fi
  read -r pid < "$file" || continue
  if [[ ! "$pid" =~ ^[0-9]+$ ]] || [[ "$pid" -le 1 ]]; then continue; fi
  command="$(ps -p "$pid" -o command= || true)"
  case "$service:$command" in
    frontend:*vite/bin/vite.js*|backend:*uvicorn*backend.main:create_app*|ollama:*ollama*serve*) kill "$pid" 2>/dev/null || true ;;
  esac
  : > "$file"
done
