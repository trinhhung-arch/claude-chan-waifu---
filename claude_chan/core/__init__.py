"""Phần dùng chung cho mọi module: cấu hình (config) và trạng thái chung (State). Không import module nào khác."""
from .state import State

__all__ = ["State"]
