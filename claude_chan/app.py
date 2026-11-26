"""Nối mọi module thành chương trình: nhân vật, luồng nói chuyện với model, chăm sóc, tập trung, hành vi tự phát, khay."""
import ctypes
import os
import subprocess
import sys
import time
import tkinter as tk
from pathlib import Path

from . import behaviors, brain, settings, tray
from .character import Character
from .core import State
from .core.config import APP_ID, CLIP_MAX, ERROR_LOG, MEMORY_FILE, MEMORY_HEADER, MOCK, OPEN_FLAG, ROOT, tr
from .desktop import accept_drops
from .dialogue import pick
from .focus import Focus
from .game import FoodGame
from .memory import log_line
from .wellbeing import Wellbeing


def main():
    # Màn hình scale 125%: không bật cái này thì Tk báo sai kích thước màn hình, nhân vật lệch khỏi góc
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
    # hẹn giờ Windows mặc định chỉ chính xác ~15.6ms: after(16) hay thành 31ms, chuyển động còn ~30 khung/giây, trông giật
    ctypes.windll.winmm.timeBeginPeriod(1)
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)  # cửa sổ Claude-chan ở taskbar mang icon riêng
    if sys.stderr is None:  # chạy bằng pythonw (tự khởi động) không có console: ghi lỗi ra file, mỗi lần chạy ghi đè
        sys.stderr = open(ERROR_LOG, "w", encoding="utf-8")
    state = State()  # trạng thái chung, luồng nói chuyện với model cũng đọc
    char = Character(state)
    root = char.root
    focus = Focus(char, state, on_change=lambda: icon.update_menu())
    game = FoodGame(char)

    def toggle_pause():
        if state.paused.is_set():
            state.paused.clear()
            char.say(pick("resume"), "lap_lanh")
        else:
            state.paused.set()
            char.say(pick("pause"), "xau_ho")
        icon.update_menu()  # pystray dựng menu Windows một lần rồi giữ nguyên: phải dựng lại thì dấu tích mới đổi

    def ask(question):
        asks.put(question)
        char.start_thinking("thinking")

    def ask_clipboard():
        """Gửi đoạn chữ đang có trong clipboard (người dùng vừa Ctrl+C) cho model giải thích / dịch."""
        if char.answering:  # đang nghĩ / đang giải thích câu trước thì chưa nhận câu mới
            return
        try:
            clip = root.clipboard_get().strip()
        except tk.TclError:  # clipboard trống hoặc đang chứa ảnh, file...
            clip = ""
        char.show()
        char.close_ask()
        if not clip:
            return char.say(pick("clip_empty"), "suy_tu")
        asks.put(("clip", clip[:CLIP_MAX]))
        char.start_thinking("clip_read")

    def feed(paths):
        """Kéo thả file / ảnh vào người: nhai nhóp nhép trong lúc model nếm, xong nói một câu (như trả lời câu hỏi)."""
        if not paths or char.answering or char.asking or state.dragging.is_set():
            return
        char.show()
        asks.put(("feed", paths))
        char.start_thinking("eating", "de_thuong")  # mặt phồng má, tay ôm má: đang nhai
        char.chew()

    def fire_reminder(what):
        if char.asking:  # đang gõ câu hỏi thì đợi chút, kẻo che ô nhập
            return root.after(5000, fire_reminder, what)
        char.show()  # nhắc việc thì hiện lên dù đang ẩn
        char.say(pick("reminder", what=what), "lap_lanh")

    def open_memory():
        if not MEMORY_FILE.exists():
            MEMORY_FILE.write_text(MEMORY_HEADER, encoding="utf-8")
        os.startfile(MEMORY_FILE)  # mở bằng Notepad (chương trình mặc định cho .txt)

    def toggle_walk():
        char.toggle_walk()
        icon.update_menu()

    def restart():
        """Lưu cài đặt xong: mở bản mới (đợi bản này thoát hẳn mới chạy) rồi thoát, cài đặt mới có hiệu lực từ đầu."""
        pythonw = Path(sys.executable).with_name("pythonw.exe")
        args = [str(pythonw if pythonw.exists() else sys.executable), str(ROOT / "assistant.py"), "--restart"]
        subprocess.Popen(args + (["--mock"] if MOCK else []), cwd=ROOT)
        root.destroy()

    def open_settings():
        settings.open_window(root, restart)

    icon, todo = tray.build([
        (tr("Cài đặt..."), open_settings, {"default": True}),  # bấm trái vào icon ở khay = mở cửa sổ Claude-chan
        (tr("Hiện / ẩn nhân vật"), char.show_hide),
        (tr("Hỏi nhân vật..."), char.open_ask),
        (tr("Hỏi về đoạn vừa copy"), ask_clipboard),
        (tr("Chơi: giành đồ ăn"), game.start),
        (focus.label, focus.toggle),
        (tr("Tạm dừng nhìn màn hình"), toggle_pause, {"checked": lambda _: state.paused.is_set()}),
        (tr("Cho đi dạo khi rảnh"), toggle_walk, {"checked": lambda _: char.walk["on"]}),
        (tr("Mở file ký ức"), open_memory),
        (tr("Về góc mặc định"), char.reset_position),
        tray.SEPARATOR,
        (tr("Thoát"), root.destroy),
    ])
    char.on_click, char.on_ask = toggle_pause, ask

    held = []  # câu bình luận đang chờ nhân vật nói xong câu trước: [(lời, emote, lúc về)], chỉ giữ câu mới nhất

    def speak(line, emote, answer=False):
        char.say(line, emote, answer=answer)
        if not MOCK:  # mock chọn emote ngẫu nhiên, ghi vào chỉ làm rối nhật ký
            log_line("trả lời" if answer else "bình luận", emote, line)

    def poll():
        tray.run_pending(todo)
        while dropped:  # file vừa kéo thả vào người
            feed(dropped.pop(0))
        if OPEN_FLAG.exists():  # vừa bấm shortcut Claude-chan lúc app đang chạy: mở cửa sổ
            OPEN_FLAG.unlink(missing_ok=True)
            open_settings()
        # bỏ câu bình luận lúc đang tạm dừng, đang gõ câu hỏi (kẻo che ô nhập) hay đang chờ trả lời (bình luận
        # gửi đi trước câu hỏi mới về, đè mất bong bóng "đang nghĩ"); câu trả lời thì luôn hiện ngay
        mute = state.paused.is_set() or state.dragging.is_set() or char.asking or char.thinking
        while not out.empty():
            line, emote, *answer = out.get()  # answer = [True, nhắc, tập trung] nếu là câu trả lời
            if answer:
                char.answered()
                held.clear()  # bình luận cũ hơn câu trả lời: thôi khỏi nói
                speak(line, emote, answer=True)
            elif not mute:  # đang nói dở câu khác thì giữ lại, nói xong mới nói, khỏi bị cắt ngang giữa chừng
                held[:] = [(line, emote, time.time())]
            if answer and answer[1]:  # hẹn giờ ở luồng giao diện; tắt chương trình thì mất lời nhắc
                minutes, what = answer[1]
                root.after(minutes * 60000, fire_reminder, what)
            if answer and answer[2]:  # "mình code 40 phút nha" -> bật chế độ tập trung đúng 40 phút
                focus.begin(answer[2], announce=False)
        if held and (mute or time.time() - held[0][2] > 60):  # chờ lâu quá thì màn hình đã khác, bỏ
            held.clear()
        if held and not char.talking:
            speak(*held.pop()[:2])
        root.after(200, poll)

    char.start()
    # cửa sổ trong + hình + bong bóng (cửa sổ ngoài wm_frame bị Tk dựng lại lúc hiện lần đầu nên không dùng)
    dropped = accept_drops(root.winfo_id(), char.face.winfo_id(), char.bubble.winfo_id())
    behaviors.start(char, state)
    asks, out = brain.start(state)
    Wellbeing(char, state).start()
    focus.start()
    poll()
    icon.run_detached()
    try:
        root.mainloop()
    finally:
        icon.stop()  # thoát bằng chuột phải hay menu khay đều gỡ icon, không để icon ma lại trên taskbar
        ctypes.windll.winmm.timeEndPeriod(1)
