#!/usr/bin/env bash
# 前台启动 STCP visitor（第 2 个 frpc）
set -euo pipefail
cd "$(dirname "$0")/../.."
mkdir -p local-lab/logs
exec ./bin/frpc -c ./local-lab/frpc-visitor.toml
