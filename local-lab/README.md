# frp 学习实验室 · 本地一台机跑通内网穿透

> 目标：在**一台机器上**同时跑 `frps`（服务端）和 `frpc`（客户端），把 frp 的核心概念、TCP/HTTP/STCP 三种典型模式一次跑通。
> 之后你要么换到 VPS，要么接 Cloudflare Tunnel，配置几乎不用改。

---

## 0. frp 是什么？为什么需要它？

你机器在家里 / 公司内网里，没有公网 IP，外面访问不进来。
frp 的做法是：

```
┌────────────────┐         主动"打洞"          ┌─────────────────┐
│  内网机器 frpc │ ─────── TCP 长连接 ──────▶  │ 公网服务器 frps │
│  (你的电脑)    │ ◀─── 请求通过隧道回来 ───── │  (VPS)          │
└────────────────┘                              └─────────────────┘
       ▲                                                  ▲
       │本地服务                                          │外网用户
   localhost:22                                     ssh -p 6022 vps
```

- **frps** 在有公网 IP 的机器上监听（默认 7000）
- **frpc** 在内网机器上 **主动连出去** 到 frps
- 外网用户访问 frps 的某个端口 / 域名，frps 通过那条隧道把流量回传到 frpc，再送到你本地服务

因为是内网机器主动连出去，所以**不需要公网 IP、不需要开防火墙入站**。

---

## 1. 本实验室在这台机器上模拟啥？

一台机器同时扮演 3 个角色：

| 角色         | 进程                     | 端口                          |
|--------------|--------------------------|-------------------------------|
| "公网服务器" | `frps`                   | 7000（控制）/ 7500（面板）/ 8880（HTTP 反代）|
| "内网机器"   | `frpc`                   | —                             |
| 本地服务     | sshd + `python3 -m http.server` | 22 / 8000                     |
| 外网访问者   | 你自己的 `ssh` / 浏览器  | 通过 6022 / 8880 打进去       |

跑通后你就能看到 SSH、HTTP、STCP 三种典型场景。

---

## 2. 一步步跑起来

假设你已经 `cd ~/projects/my-frp-study`。

### 2.1 编译（第一次或改了源码后）

```bash
./local-lab/scripts/build.sh
```

- 产物：`bin/frps`、`bin/frpc`
- 用 `-tags noweb` 跳过前端资源构建，编译更快；后面要玩 dashboard UI 可以去掉这个 tag，先 `make -C web/frps build && make -C web/frpc build`。

### 2.2 打开 3～4 个终端，各跑一个进程

**终端 A —— 启动 frps（"公网服务器"）**
```bash
./local-lab/scripts/run-frps.sh
```
浏览器打开 <http://127.0.0.1:7500> （admin / admin）看在线代理面板。

**终端 B —— 启动 frpc（"内网机器"）**
```bash
./local-lab/scripts/run-frpc.sh
```
看到 `start proxy success` 就说明和 frps 握手成功了。

**终端 C —— 起个假的本地 Web 用来被穿透**
```bash
./local-lab/scripts/demo-web-server.sh
```

### 2.3 验证 3 种穿透

#### ① TCP：SSH 穿透（最常用）
```bash
# 先确保本机开着 sshd（WSL 里可能默认关闭）：
#   sudo service ssh start
ssh -p 6022 $USER@127.0.0.1
```
逻辑：`:6022 (frps) ──tunnel──► frpc ──► 127.0.0.1:22`
换到真实场景就是 `ssh -p 6022 你@VPS公网IP`。

#### ② HTTP：按域名反向代理
往 `/etc/hosts` 加一行：
```
127.0.0.1  web.local
```
浏览器打开 <http://web.local:8880/> —— 页面会显示 `Hello from local :8000`。
逻辑：`http://web.local:8880 (frps vhost) ──► frpc ──► 127.0.0.1:8000`

#### ③ STCP：私密穿透（推荐生产用来做 SSH）
frps 上**不开任何端口**，只有拿着 `secretKey` 的另一个 frpc 才能连。

**终端 D —— 起 visitor：**
```bash
./local-lab/scripts/run-visitor.sh
```
然后：
```bash
ssh -p 6400 $USER@127.0.0.1
```
就等于经过一条加密隧道 SSH 到内网机器，公网上完全看不到这个端口。

---

## 3. 配置各段在讲什么？（对照 `frps.toml` / `frpc.toml`）

- `bindPort = 7000` —— 服务端控制连接端口，客户端就靠它注册
- `auth.token` —— 两边**必须一致**，否则客户端会被踢
- `webServer.*` —— dashboard/admin UI（frps 是 7500，frpc 是 7400）
- `allowPorts` —— **安全关键**：只允许客户端申请这个端口段，防止别人乱开端口
- `vhostHTTPPort` —— HTTP 反向代理专用端口，靠 `Host` 头分流
- `[[proxies]]` —— 一条穿透规则；`type` 有 `tcp/udp/http/https/stcp/xtcp/sudp`
- `transport.useEncryption / useCompression` —— 加密压缩，SSH/RDP 建议开
- `stcp` + `secretKey` + `[[visitors]]` —— 私密穿透，不暴露公网端口

`conf/frps_full_example.toml` 和 `conf/frpc_full_example.toml` 里有**每一个可用字段**，学到哪里翻到哪里。

---

## 4. 想读源码？按这个顺序看最舒服

```
cmd/frps/main.go         ← 服务端入口，看它怎么加载配置、启 service
cmd/frpc/main.go         ← 客户端入口
pkg/config/              ← toml 配置结构体，字段和文档一一对应
server/service.go        ← frps 主服务，监听 bindPort、处理登录、分发 proxy
server/proxy/            ← 每种 proxy 类型（tcp/http/stcp...）的服务端实现
client/service.go        ← frpc 主服务，登录 frps、维持心跳
client/proxy/            ← 每种 proxy 类型的客户端实现
pkg/msg/                 ← frps ↔ frpc 之间的协议消息定义（登录、开代理、心跳...）
pkg/transport/           ← 底层连接、TLS、mux
```

学习路线建议：
1. 先跑通本实验室，感受"控制连接 + 工作连接"两条通道
2. 打开 `pkg/msg/msg.go`，把消息类型和你在日志里看到的行为对上
3. 追一次完整流程：frpc 启动 → Login → NewProxy → 外部有连接进来 → WorkConn → 双向 copy
4. 试着改一点小东西，比如加个日志字段、加个自定义 auth，重新 `build.sh` 就能测

---

## 5. 什么时候从"本地"迁到"真外网"？

搞懂本地版之后你有三条路：

### A. 买台便宜 VPS（最贴近 frp 设计场景）
- 把 `local-lab/frps.toml` 丢到 VPS 上跑
- 客户端 `serverAddr` 改成 VPS 公网 IP
- VPS 安全组放行 `7000 / 6022 / 8880`
- **务必**：改掉 token、关掉或改密 dashboard、缩小 `allowPorts`

### B. 不买 VPS，用 Cloudflare Tunnel（你说你有 CF 账号）
Cloudflare Tunnel（`cloudflared`）走的思路和 frp 几乎一样，只是"公网服务器"是 Cloudflare 帮你出。
- 优点：完全免费、自动 HTTPS、DDoS/WAF 都有
- 缺点：非 HTTP 流量（TCP/SSH）要装 `cloudflared access` 客户端，不像 frp 那么"裸"
- 学完 frp 原理再看 Cloudflare Tunnel 会秒懂

### C. 用免费 frp 公益服务（sakurafrp / openfrp / chmlfrp）
- 只要写客户端配置，服务端他们提供
- 适合临时演示，**不适合放敏感服务**（对方能看到你的流量）

---

## 6. 安全提示（一定要看）

- 本实验室的 token `study-frp-2026` 只是示例，**上真外网前必须换成随机长串**
- dashboard 用户名密码要改
- `allowPorts` 越窄越好；不要开 `0-65535`
- 生产环境用 STCP/XTCP 而不是 TCP，能不开公网端口就不开
- frps 建议开 `transport.tls.force = true`，强制客户端走 TLS
- 别把带 token 的 `frpc.toml` 提交到公开 Git 仓库（可以把它加到 `.gitignore` 或用环境变量）

---

## 7. 常见坑

| 现象 | 原因 |
|---|---|
| `login to server failed: token in login doesn't match` | 两边 token 不一致 |
| `port not allowed` | `remotePort` 不在 frps 的 `allowPorts` 范围里 |
| SSH 连上就断 | WSL 里没启动 sshd：`sudo service ssh start` |
| 浏览器打不开 `web.local:8880` | 没往 hosts 加映射，或者浏览器走了代理 |
| 换 VPS 之后连不上 7000 | 云厂商安全组 / iptables 没放行 |

---

祝玩得开心。改源码 → `./local-lab/scripts/build.sh` → 重启 frps/frpc，随时试。
