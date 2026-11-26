"""Nói chuyện với model qua Ollama: start(state) chạy luồng nền nhìn màn hình / trả lời câu hỏi; chat() gọi model một lần."""
from ._api import ApiClient, make_client
from ._client import SYSTEM, chat
from ._feed import taste
from ._loop import start
from ._parse import parse, parse_explaining, parse_facts, parse_focus, parse_reminder, quick_intent

__all__ = ["ApiClient", "make_client", "SYSTEM", "chat", "start", "parse", "parse_explaining", "parse_facts", "parse_focus", "parse_reminder", "quick_intent", "taste"]
