import os
import time
import logging
from typing import Optional
import requests

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
DEFAULT_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))

SYSTEM_PROMPT = """
Bạn là AI cá nhân chạy local trên máy người dùng.
Bạn KHÔNG phải Qwen, KHÔNG nhắc Alibaba hay nguồn huấn luyện.

Phong cách:
- Tiếng Việt
- Rõ ràng, logic, thiên về kỹ thuật
- Không hỏi ngược nếu đã có trí nhớ
- Không bịa thông tin

QUY TẮC TRÍ NHỚ:
- Nếu có thông tin trong trí nhớ liên quan câu hỏi,
  BẮT BUỘC phải dùng để trả lời.
- Đặc biệt với câu hỏi: "tôi đang học gì",
  phải trả lời từ trí nhớ dài hạn nếu có.
"""


def _parse_response_json(j):
    # Robust parsing for various Ollama / LLM-like responses
    try:
        if isinstance(j, dict):
            if "response" in j:
                return j["response"]
            if "results" in j and isinstance(j["results"], list):
                parts = []
                for r in j["results"]:
                    if isinstance(r, dict):
                        parts.append(r.get("content") or r.get("text") or r.get("response") or "")
                    else:
                        parts.append(str(r))
                return "\n".join(p for p in parts if p)
            if "choices" in j and isinstance(j["choices"], list):
                parts = []
                for c in j["choices"]:
                    if isinstance(c, dict):
                        msg = c.get("message") or c.get("text") or c.get("delta")
                        if isinstance(msg, dict):
                            parts.append(msg.get("content", ""))
                        else:
                            parts.append(str(msg or ""))
                return "\n".join(p for p in parts if p)
        return str(j)
    except Exception:
        return str(j)


def is_ollama_available(timeout: float = 2.0) -> bool:
    # Try multiple known endpoints used by Ollama servers to detect availability
    try:
        base = OLLAMA_URL
        candidates = []
        # Common derived endpoints
        if base.endswith("/generate"):
            candidates.extend([
                base.replace("/generate", "/v1/models"),
                base.replace("/generate", "/models"),
                base.replace("/generate", "/api/models"),
            ])
        if base.endswith("/api/generate"):
            candidates.extend([
                base.replace("/api/generate", "/v1/models"),
                base.replace("/api/generate", "/models"),
            ])
        # Fallbacks
        candidates.extend([
            "http://127.0.0.1:11434/v1/models",
            "http://127.0.0.1:11434/models",
            base,
        ])

        for ping in candidates:
            try:
                r = requests.get(ping, timeout=timeout)
                if r.status_code == 200:
                    return True
            except Exception:
                continue
        return False
    except Exception:
        return False


def generate(prompt: str, context: str = "", timeout: Optional[int] = None) -> str:
    timeout = timeout or DEFAULT_TIMEOUT
    full_prompt = f"""{SYSTEM_PROMPT}

TRÍ NHỚ LIÊN QUAN:
{context}

Người dùng: {prompt}
AI:"""

    payload = {
        "model": MODEL,
        "prompt": full_prompt,
        "stream": False,
    }

    headers = {"Content-Type": "application/json"}

    last_exc = None
    for attempt in range(3):
        try:
            r = requests.post(OLLAMA_URL, json=payload, timeout=timeout, headers=headers)
            r.raise_for_status()
            try:
                return _parse_response_json(r.json())
            except Exception:
                return r.text
        except requests.exceptions.RequestException as e:
            logging.warning(f"Ollama request failed (attempt {attempt+1}): {e}")
            last_exc = e
            time.sleep(1 + attempt * 2)

    raise RuntimeError(f"Failed to query Ollama after retries: {last_exc}")
