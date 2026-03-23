#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset

# Start Daphne ASGI server (supports HTTP + WebSocket)
daphne -b 0.0.0.0 -p 8000 config.asgi:application
