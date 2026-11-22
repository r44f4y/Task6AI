#!/usr/bin/env bash
# Source from setup/start to manage a workspace-local server.
relay_prepare_ollama() {
  if [[ -x .local/ollama-bin/ollama ]]; then
    relay_ollama="$PWD/.local/ollama-bin/ollama"
  elif command -v ollama >/dev/null 2>&1; then
    relay_ollama="$(command -v ollama)"
  else
    return 1
  fi
  export OLLAMA_HOST=127.0.0.1:11434 OLLAMA_NO_CLOUD=1
  export OLLAMA_MODELS="${OLLAMA_MODELS:-$PWD/.local/models}"
}
relay_start_ollama() {
  if curl --noproxy '*' -fsS --max-time 1 http://127.0.0.1:11434/api/version >/dev/null 2>&1; then
    return 0
  fi
  relay_prepare_ollama || return 1
  mkdir -p "$OLLAMA_MODELS"
  nohup "$relay_ollama" serve >.local/ollama.log 2>&1 </dev/null &
  echo "$!" >.local/ollama.pid
  for ((relay_poll=0;relay_poll<40;relay_poll++)); do
    if curl --noproxy '*' -fsS --max-time 1 http://127.0.0.1:11434/api/version >/dev/null 2>&1; then return 0; fi
    sleep .25
  done
  return 1
}
