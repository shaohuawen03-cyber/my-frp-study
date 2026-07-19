#!/usr/bin/env bash
# 起一个最简单的本地 Web 用来被穿透测试
# 之后浏览器访问 http://web.local:8880/ 验证 HTTP 穿透
set -euo pipefail
cd "$(dirname "$0")/../.."
mkdir -p local-lab/www
cat > local-lab/www/index.html <<'HTML'
<!doctype html><meta charset="utf-8">
<title>frp study</title>
<h1>Hello from local :8000</h1>
<p>如果你在浏览器地址栏看到 <code>web.local:8880</code>，说明 HTTP 穿透生效了 🎉</p>
HTML
cd local-lab/www
exec python3 -m http.server 8000 --bind 127.0.0.1
