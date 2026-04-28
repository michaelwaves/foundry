#!/usr/bin/env bash
# Thin wrapper around the unified collector. Override any field on the CLI:
#   ./collect_train.sh subsample=50 partial_t=10
set -euo pipefail
cd "$(dirname "$0")/../.."
exec python -m tutorials.sae_collect.run_collect \
    --config-name=rfd3_safeprotein "$@"
