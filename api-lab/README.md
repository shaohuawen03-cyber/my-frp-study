# AI API 学习实验室

目标：**10 分钟跑通一个 OpenAI 兼容 API，再回头读 upstream 的 lmarena2api 就秒懂。**

---

## 第 1 站：跑 mock（假的复读机）

这个服务没有任何真实模型，就是把你输入原样返回，但**协议格式跟 OpenAI 完全一样**。
目的：先摸清"OpenAI 兼容 API"到底长啥样。

### 安装依赖

```bash
# 用 pip
pip install fastapi uvicorn

# 或用 conda（你是 base 环境）
conda install -c conda-forge fastapi uvicorn -y
```

### 启动服务

```bash
cd ~/projects/my-frp-study
python api-lab/mock_openai.py
```

看到 `Uvicorn running on http://127.0.0.1:8080` 就成功了。**保持前台**。

### 测试（另开一个终端）

```bash
# ① 列出可用模型
curl http://127.0.0.1:8080/v1/models \
  -H "Authorization: Bearer sk-test"

# ② 发一次对话（非流式）
curl http://127.0.0.1:8080/v1/chat/completions \
  -H "Authorization: Bearer sk-test" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "fake-gpt-4",
    "messages": [{"role":"user","content":"你好"}]
  }'

# ③ 发一次对话（流式，看它一个字一个字吐）
curl -N http://127.0.0.1:8080/v1/chat/completions \
  -H "Authorization: Bearer sk-test" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "fake-gpt-4",
    "messages": [{"role":"user","content":"讲个笑话"}],
    "stream": true
  }'
```

### 用真实客户端连它（可选，很爽的一步）

装个 [Chatbox](https://chatboxai.app/) 或 Cherry Studio，配置：

- **API 类型**：OpenAI
- **API Base URL**：`http://127.0.0.1:8080/v1`
- **API Key**：`sk-anything`（我们没做真实校验）
- **模型**：`fake-gpt-4`

然后你就能在图形界面里跟这个复读机对话 —— **这就证明你的服务"OpenAI 兼容"是真的**。

---

## 第 2 站：读代码，理解每个字段

请把 `mock_openai.py` 从上往下读一遍，重点看：

| 代码位置 | 学到什么 |
|---|---|
| `GET /v1/models` | 客户端启动时怎么发现"你有哪些模型" |
| `POST /v1/chat/completions` | 主接口的入参：`model` / `messages` / `stream` |
| `_completion_response` | 非流式响应的完整结构 |
| `_sse_stream` | 流式响应的 SSE 协议：`data: {...}\n\n` + 最后 `[DONE]` |
| `_check_auth` | `Authorization: Bearer xxx` 头的用法 |

---

## 第 3 站：回头看 upstream/lmarena2api

现在你已经知道"OpenAI 兼容 API"要返回什么了。lmarena2api 做的事就是：

1. **提供**一个 `/v1/chat/completions` 接口（跟你 mock 一样）
2. **收到请求**后，不是复读，而是拿你的 `messages` 去请求 `lmarena.ai` 的网页版聊天
3. **拿到网页版的流式返回**后，包装成 OpenAI 的 SSE 格式返回给客户端

对应源码路径（Go 项目）：

```bash
cd ~/projects/my-frp-study     # 你的 fork
git remote -v                  # upstream = deanxv/lmarena2api
git fetch upstream
git log upstream/main --oneline | head    # 看看 upstream 的历史
```

关键目录（不同 fork 结构可能略有差异，去 upstream 分支看）：
- `router/` 或 `controller/` — 定义 `/v1/chat/completions` 路由
- `service/` 或 `internal/lmarena/` — 调用 lmarena.ai 网页的核心逻辑
- `common/` — 请求/响应的结构体定义（对照 OpenAI 官方文档 https://platform.openai.com/docs/api-reference/chat）

---

## 第 4 站：把 mock 换成真中转（进阶）

自己写一个**真能用**的中转，思路：

1. `/v1/chat/completions` 收到请求
2. 用 `httpx` 去调你想代理的后端（比如 free-gpt / 你自己的 LLM）
3. 把后端响应转成 OpenAI 格式返回

不建议现在就做，等 upstream 源码看完再尝试。

---

## 常见坑

| 现象 | 原因 |
|---|---|
| `ModuleNotFoundError: fastapi` | 忘了 `pip install fastapi uvicorn` |
| `Address already in use: 8080` | 换个端口 `--port 8081` 或 `lsof -i :8080` 杀掉占用进程 |
| 客户端连不上 | 客户端和服务在同一台机才用 127.0.0.1；跨机要用 `--host 0.0.0.0` |
| 走了系统代理导致 curl 连不上 127.0.0.1 | `curl` 加 `--noproxy '*'`，或确保 `no_proxy` 包含 127.0.0.1（你 bashrc 已经配好）|
