#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset

# Graceful shutdown: when Docker sends SIGTERM, Celery finishes the
# current task before stopping. This prevents mid-tick interruptions
# that could leave the simulation in an inconsistent state.
# --without-mingle: skip synchronization on startup (faster boot)
# --without-gossip: skip gossip protocol (not needed for single-node)
celery -A config.celery worker \
    -l INFO \
    --concurrency=2 \
    --without-mingle \
    --without-gossip
