"""Chọn nơi gọi model: Ollama (máy này / máy khác) hay API trên mạng theo chuẩn OpenAI (OpenAI, Gemini, OpenRouter,
Groq... cả /v1 của Ollama). ApiClient nhận lệnh giống hệt ollama.Client.chat, nên phần còn lại không cần biết đang dùng gì."""
import base64
from types import SimpleNamespace

import httpx
import ollama

from ..core.config import API_BASE, API_KEY, HOST, PROVIDER


def make_client(timeout):
    """Client gọi model theo cài đặt hiện tại. Cả hai loại đều có ._client là httpx.Client: đóng nó từ luồng khác là
    huỷ được lệnh đang chờ (dùng khi bỏ lượt bình luận vì người dùng vừa hỏi)."""
    if PROVIDER == "api":
        return ApiClient(API_BASE, API_KEY, timeout)
    return ollama.Client(host=HOST, timeout=timeout)


class ApiClient:
    def __init__(self, base, key, timeout):
        self.base = base.rstrip("/")
        self._client = httpx.Client(timeout=timeout, headers={"Authorization": f"Bearer {key}"} if key else {})

    def chat(self, model, messages, format=None, options=None, **_):
        """Như ollama.Client.chat: messages kiểu Ollama (ảnh là bytes trong "images"), format là JSON schema.
        Trả về đối tượng có .message.content. Bỏ qua keep_alive / think (chỉ Ollama hiểu)."""
        body = {"model": model, "messages": [self._message(m) for m in messages]}
        if options and "temperature" in options:
            body["temperature"] = options["temperature"]
        if format:
            body["response_format"] = {"type": "json_schema", "json_schema": {"name": "tra_loi", "schema": format}}
        # Model / nhà cung cấp không nhận tham số nào thì lùi dần: bỏ temperature (vài model suy luận chỉ nhận mặc định),
        # rồi đổi khuôn JSON chi tiết thành "trả JSON là được" (nhắc tên các trường trong lời dặn cho chắc).
        for fallback in (None, "temperature", "json_object"):
            if fallback == "temperature":
                body.pop("temperature", None)
            elif fallback == "json_object" and format:
                body["response_format"] = {"type": "json_object"}
                body["messages"].insert(0, {"role": "system", "content": "Chỉ trả lời bằng một object JSON có đúng các trường: "
                                            + ", ".join(format.get("properties", {}))})
            r = self._client.post(self.base + "/chat/completions", json=body)
            if r.status_code != 400:
                break
        if r.status_code >= 400:
            raise RuntimeError(f"API báo lỗi {r.status_code}: {r.text[:300]}")
        content = r.json()["choices"][0]["message"].get("content") or ""
        return SimpleNamespace(message=SimpleNamespace(content=content, thinking=None))

    def models(self):
        """Tên các model nhà cung cấp cho dùng (GET /models), để chọn trong cửa sổ Cài đặt."""
        r = self._client.get(self.base + "/models")
        r.raise_for_status()
        return sorted(m["id"] for m in r.json().get("data", []))

    @staticmethod
    def _message(m):
        if not m.get("images"):
            return {"role": m["role"], "content": m["content"]}
        parts = [{"type": "text", "text": m["content"]}]
        parts += [{"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(img).decode()}}
                  for img in m["images"]]
        return {"role": m["role"], "content": parts}
