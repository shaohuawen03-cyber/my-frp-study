#!/usr/bin/env bash
# 前台启动 frps（Ctrl+C 停）
set -euo pipefail
cd "$(dirname "$0")/../.."
mkdir -p local-lab/logs
exec ./bin/frps -c ./local-lab/frps.toml
