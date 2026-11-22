# Zero-cost verification

Relay AI uses Python, Node.js, React, FastAPI, SQLite, report generation libraries, local package storage and a standalone Ollama server. Qwen3 4B was downloaded once from the Ollama registry. The weights use Apache 2.0. [Ollama model details](https://ollama.com/library/qwen3%3A4b) The project requires no account, billing information, hosted database, email provider, external asset provider, API key or paid inference service.

Ollama was observed running with cloud disabled, listening at `127.0.0.1:11434` and using Apple Metal on the M5 Pro. Relay sends schema-constrained inference to loopback through an HTTP client with proxies disabled. Settings reject cloud model identifiers. The project startup script installs and runs the standalone server from ignored workspace data if needed. If an existing service is reused, run it with cloud disabled and verify the model is installed locally.

The frontend imports fonts and icons from system fonts and installed dependencies. Runtime data and exports are written to local paths. Customer communication is stored as a local simulated conversation event. Setup downloads free packages and model weights. Startup and demo flows require no package downloads.

See [test results](TEST_RESULTS.md) for the local-model and browser evidence and the conditions of offline verification.

The app, Ollama and browser tests ran with a macOS sandbox profile that denied non-loopback outbound connections. A reserved-address connection returned an OS permission error. The Ontario Bulk workflow still completed local inference, human-control endpoints and export. The other workflow inputs produced local model-backed outputs under the same profile. The network check preserved the Mac’s Wi-Fi settings.
