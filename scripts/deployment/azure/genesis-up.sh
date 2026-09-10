#!/usr/bin/env bash
# Noninteractive policy-aware entry point for Azure subscription onboarding.

set -euo pipefail
umask 077

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/genesis_orchestrator.py" "$@"
