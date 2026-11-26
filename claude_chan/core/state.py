"""Trạng thái nhiều module cùng cần (cả luồng nói chuyện với model đọc): tạm dừng, đang ngủ, đang ẩn, cửa sổ đang mở."""
import threading
from dataclasses import dataclass, field


@dataclass
class State:
    paused: threading.Event = field(default_factory=threading.Event)  # người dùng bấm tạm dừng: không nhìn màn hình
    sleeping: threading.Event = field(default_factory=threading.Event)  # người dùng rời máy: nhân vật ngủ, không chụp
    hidden: threading.Event = field(default_factory=threading.Event)  # nhân vật ẩn xuống khay: không hiện, không chụp
    dragging: threading.Event = field(default_factory=threading.Event)  # người dùng đang kéo nhân vật: không chụp, không bình luận
    # tiêu đề cửa sổ khác gần nhất: lúc người dùng bấm vào nhân vật thì cửa sổ nhân vật đứng trước, xét cửa sổ trước đó
    seen_title: str = ""
