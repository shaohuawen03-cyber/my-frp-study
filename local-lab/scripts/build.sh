#!/usr/bin/env bash
# 编译 frps / frpc（源码 => bin/frps, bin/frpc）
set -euo pipefail
cd "$(dirname "$0")/../.."

echo "==> go version:"
go version

# 不编 web dashboard 的静态资源（更快，用自带的 noweb tag）
export CGO_ENABLED=0
mkdir -p bin

echo "==> building frps ..."
go build -trimpath -ldflags "-s -w" -tags "frps,noweb" -o bin/frps ./cmd/frps

echo "==> building frpc ..."
go build -trimpath -ldflags "-s -w" -tags "frpc,noweb" -o bin/frpc ./cmd/frpc

echo "==> done:"
ls -lh bin/frps bin/frpc
