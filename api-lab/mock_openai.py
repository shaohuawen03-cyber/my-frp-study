"""
最小 OpenAI 兼容 API 服务（教学 mock）
=====================================

依赖：pip install fastapi uvicorn

跑起来：
    python api-lab/mock_openai.py
或：
    uvicorn api-lab.mock_openai:app --host 127.0.0.1 --port 8080 --reload

测试（另开一个终端）：
    curl http://127.0.0.1:8080/v1/models \
        -H "Authorization: Bearer sk-test"

    curl http://127.0.0.1:8080/v1/chat/completions \
        -H "Authorization: Bearer sk-test" \
        -H "Content-Type: application/json" \
        -d '{
          "model": "fake-gpt-4",
          "messages": [{"role":"user","content":"你好"}]
        }'

这个服务:
1. 完全没有后端 LLM，返回的是把你输入原样"复读"的假回复
2. 但请求/响应格式和 OpenAI 官方 100% 一致
3. 任何 OpenAI 客户端（ChatGPT Next Web / Cherry Studio 等）都能连它
   -> Base URL 填 http://127.0.0.1:8080/v1
   -> API Key 随便填一个 sk- 开头的

理解了这个 mock 的每一行，再回头看 upstream/lmarena2api 就秒懂：
它做的事情就是把这里的"复读"替换成"真的去调 LMArena 网页拿回复"。
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import StreamingResponse

app = FastAPI(title="mock-openai-api")


# ------------------------------------------------------------------
# 1) /v1/models —— 客户端会先调这个拉可用模型列表
# ------------------------------------------------------------------
@app.get("/v1/models")
def list_models(authorization: str | None = Header(default=None)):
    _check_auth(authorization)
    return {
        "object": "list",
        "data": [
            {"id": "fake-gpt-4",  "object": "model", "owned_by": "study"},
            {"id": "fake-claude", "object": "model", "owned_by": "study"},
        ],
    }


# ------------------------------------------------------------------
# 2) /v1/chat/completions —— 核心接口
# ------------------------------------------------------------------
@app.post("/v1/chat/completions")
async def chat_completions(request: Request,
                           authorization: str | None = Header(default=None)):
    _check_auth(authorization)
    payload = await request.json()

    model    = payload.get("model", "fake-gpt-4")
    messages = payload.get("messages", [])
    stream   = bool(payload.get("stream", False))

    # 生成"假"回复：把用户最后一句话复读一遍
    last_user = next(
        (m["content"] for m in reversed(messages) if m.get("role") == "user"),
        "(没收到用户输入)",
    )
    reply = f"[mock-{model}] 你说的是：{last_user}"

    if stream:
        # OpenAI 的 SSE 格式：每个 chunk 是 `data: {...}\n\n`，结尾是 `data: [DONE]\n\n`
        return StreamingResponse(
            _sse_stream(reply, model),
            media_type="text/event-stream",
        )

    # 非流式响应
    return _completion_response(reply, model)


# ------------------------------------------------------------------
# 辅助
# ------------------------------------------------------------------
def _check_auth(header: str | None) -> None:
    """OpenAI 要求 Authorization: Bearer sk-xxxx
    这里为了教学只做最松验证：有 Bearer 前缀就放行。生产环境要真验 key。"""
    if not header or not header.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")


def _completion_response(text: str, model: str) -> dict[str, Any]:
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": text},
            "finish_reason": "stop",
        }],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": len(text),
            "total_tokens": len(text),
        },
    }


def _sse_stream(text: str, model: str):
    """把 text 一个字一个字吐出去，模拟真实流式返回"""
    chat_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    created = int(time.time())

    def make_chunk(delta: dict, finish: str | None = None) -> bytes:
        obj = {
            "id": chat_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
        }
        return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n".encode()

    # 首个 chunk 通常带 role
    yield make_chunk({"role": "assistant"})
    for ch in text:
        time.sleep(0.02)              # 模拟真实网络延迟
        yield make_chunk({"content": ch})
    yield make_chunk({}, finish="stop")
    yield b"data: [DONE]\n\n"


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8080, log_level="info")
