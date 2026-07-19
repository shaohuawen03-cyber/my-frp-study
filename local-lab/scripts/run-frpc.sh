#!/usr/bin/env bash
# 前台启动 frpc（Ctrl+C 停）
set -euo pipefail
cd "$(dirname "$0")/../.."
mkdir -p local-lab/logs
exec ./bin/frpc -c ./local-lab/frpc.toml
