#!/usr/bin/env bash

# Copyright (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UI_DIR="${SCRIPT_DIR}"

get_local_ip() {
  if command -v ip >/dev/null 2>&1; then
    ip -4 addr show scope global | awk '/inet / {sub(/\/.*/, "", $2); if ($2 != "127.0.0.1") {print $2; exit}}'
    return
  fi

  if command -v hostname >/dev/null 2>&1; then
    hostname -I 2>/dev/null | awk '{print $1}'
    return
  fi
}

SERVER_HOST="${SERVER_HOST:-}"
if [ -z "${SERVER_HOST}" ]; then
  SERVER_HOST="$(get_local_ip)"
  echo "Detected local IP address: ${SERVER_HOST}"
else
  echo "Using SERVER_HOST from environment: ${SERVER_HOST}"
fi

if [ -z "${SERVER_HOST}" ]; then
  echo "Unable to detect SERVER_HOST automatically. Please export SERVER_HOST=<your-server-ip> first." >&2
  exit 1
fi

UI_PORT="${UI_PORT:-7000}"
METRICS_API_PORT="${METRICS_API_PORT:-8000}"
LIBRARY_API_PORT="${LIBRARY_API_PORT:-16010}"
MEDIA_API_PORT="${MEDIA_API_PORT:-3000}"
WORKSPACE_API_PORT="${WORKSPACE_API_PORT:-3001}"
VITE_CHATBOT_WS_PORT="${VITE_CHATBOT_WS_PORT:-18789}"
export SERVER_HOST
export VITE_CHATBOT_WS_PORT="${VITE_CHATBOT_WS_PORT}"
export VITE_DEV_STATS_API_TARGET="http://${SERVER_HOST}:${METRICS_API_PORT}"
export VITE_DEV_KB_API_TARGET="http://${SERVER_HOST}:${LIBRARY_API_PORT}"
export VITE_DEV_MEDIA_API_TARGET="http://${SERVER_HOST}:${MEDIA_API_PORT}"
export VITE_DEV_FILE_API_TARGET="http://${SERVER_HOST}:${WORKSPACE_API_PORT}"
echo "UI URL: http://${SERVER_HOST}:${UI_PORT}"

cd "${UI_DIR}"
exec npm run dev -- --host 0.0.0.0 --port "${UI_PORT}"
