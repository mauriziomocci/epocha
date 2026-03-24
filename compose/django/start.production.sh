#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset

# Start Daphne ASGI server (HTTP + WebSocket)
# - Bind to all interfaces
# - 4 worker threads (adjust based on available CPU)
# - Access log disabled in production (use structured logging instead)
daphne \
    -b 0.0.0.0 \
    -p 8000 \
    --proxy-headers \
    config.asgi:application
