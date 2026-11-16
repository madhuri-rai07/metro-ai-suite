#!/bin/sh

# Copyright (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

set -eu

NGINX_TEMPLATE="/etc/nginx/templates/default.conf.template"
NGINX_CONF="/etc/nginx/conf.d/default.conf"

require_env() {
    var_name="$1"
    eval "var_value=\${$var_name:-}"

    if [ -z "$var_value" ]; then
        echo "Missing required environment variable: $var_name" >&2
        exit 1
    fi
}

require_env UI_PORT
require_env SERVER_HOST
require_env METRICS_API_PORT
require_env LIBRARY_API_PORT
require_env APP_API_PORT
require_env WORKSPACE_API_PORT
require_env VITE_CHATBOT_WS_PORT

mkdir -p "$(dirname "$NGINX_CONF")"
envsubst '${UI_PORT} ${SERVER_HOST} ${METRICS_API_PORT} ${LIBRARY_API_PORT} ${APP_API_PORT} ${WORKSPACE_API_PORT} ${VITE_CHATBOT_WS_PORT}' \
    < "$NGINX_TEMPLATE" \
    > "$NGINX_CONF"

if grep -n '\${[A-Za-z_][A-Za-z0-9_]*}' "$NGINX_CONF"; then
    echo "[replace-env] Unresolved nginx template variables remain in $NGINX_CONF" >&2
    exit 1
fi

