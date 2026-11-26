"""Cửa sổ Claude-chan (có icon ở taskbar): chỉnh cài đặt rồi lưu vào cai_dat.json, bật / tắt tự chạy khi bật máy.
open_window(root, on_saved): mở (hoặc đưa lên trước) cửa sổ; on_saved() được gọi sau khi lưu để app chạy lại."""
import json
import os
import subprocess
import sys
import threading
import tkinter as tk
import urllib.request
from pathlib import Path
from tkinter import messagebox, ttk

from PIL import Image, ImageDraw, ImageTk

from ..core import config
from ..brain import ApiClient
from ..core.config import (API_PRESETS, CHOICES, EMOTE_DIR, ICON_FILE, ROOT, SETTINGS, SETTINGS_FILE, TITLE,
                           coerce_setting, protect, tr)

STARTUP = Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs/Startup/Tro ly man hinh.lnk"
_window = [None]  # chỉ mở một cửa sổ


def autostart_on():
    return STARTUP.exists()


def set_autostart(on):
    """Tạo / xoá shortcut trong thư mục Startup của Windows (pythonw: chạy không hiện cửa sổ đen)."""
    if not on:
        return STARTUP.unlink(missing_ok=True)
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    script = ("$s = (New-Object -ComObject WScript.Shell).CreateShortcut($args[0]); $s.TargetPath = $args[1]; "
              "$s.Arguments = '\"' + $args[2] + '\"'; $s.WorkingDirectory = $args[3]; $s.IconLocation = $args[4]; $s.Save()")
    subprocess.run(["powershell", "-NoProfile", "-Command", script, str(STARTUP), str(pythonw), str(ROOT / "assistant.py"),
                    str(ROOT), str(ICON_FILE)], check=True, creationflags=0x08000000)  # CREATE_NO_WINDOW


def _models(provider, host, base, key, done):
    """Danh sách model dùng được: Ollama thì các model đã tải, API thì model nhà cung cấp cho dùng. Hỏi ở luồng riêng để
    cửa sổ không đứng hình nếu máy / mạng chậm. done((tên các model, lý do nếu không lấy được))."""
    def run():
        try:
            if provider == "api":
                names = ApiClient(base, key, 6).models()
            else:
                with urllib.request.urlopen(host.rstrip("/") + "/api/tags", timeout=3) as r:
                    names = sorted(m["name"] for m in json.load(r).get("models", []))
            done((names, "" if names else tr("chưa có model nào")))
        except Exception as e:  # không lấy được: chỉ là không có gợi ý, vẫn gõ tay tên model được
            done(([], _why(e, provider, key)))
    threading.Thread(target=run, daemon=True).start()


def _why(error, provider, key):
    """Lý do dễ hiểu vì sao không lấy được danh sách model."""
    code = getattr(getattr(error, "response", None), "status_code", None) or getattr(error, "code", None)
    if provider == "api" and not key and code in (401, 403):
        return tr("cần dán API key trước")
    if code in (401, 403):
        return tr("API key sai hoặc hết hạn")
    if code == 404:
        return tr("sai địa chỉ API")
    if code:
        return tr("nhà cung cấp báo lỗi {code}").format(code=code)
    return tr("không kết nối được, xem lại địa chỉ / mạng")


# tông hồng như bong bóng lời nói của nhân vật
BG, CARD, PINK, PINK_DARK, PINK_SOFT, TEXT, MUTED = "#fff0f5", "#ffffff", "#f08aa0", "#e0607e", "#ffe1eb", "#5b3442", "#b08391"
ICONS = {"Chung": "♪", "Model": "✿", "Bình luận": "♡", "Hành vi": "★", "Tập trung & nghỉ": "☕", "Khởi động": "♥"}


def _style(win):
    """Giao diện hồng: dùng giao diện "clam" của ttk (cho đổi màu được hết) với tên kiểu riêng "Cute.*"."""
    st = ttk.Style(win)
    st.theme_use("clam")
    font, bold = ("Segoe UI", 10), ("Segoe UI", 10, "bold")
    st.configure("Cute.TFrame", background=CARD)
    st.configure("Bg.TFrame", background=BG)
    st.configure("Cute.TLabel", background=CARD, foreground=TEXT, font=font)
    st.configure("Note.TLabel", background=CARD, foreground=MUTED, font=("Segoe UI", 9))
    st.configure("Cute.TNotebook", background=BG, borderwidth=0, tabmargins=(4, 4, 4, 0))
    st.configure("Cute.TNotebook.Tab", background=PINK_SOFT, foreground=TEXT, font=bold, padding=(12, 6), borderwidth=0,
                 lightcolor=PINK_SOFT, bordercolor=BG, focuscolor=PINK_SOFT)
    st.map("Cute.TNotebook.Tab", background=[("selected", CARD), ("active", "#ffd0de")],
           foreground=[("selected", PINK_DARK)], lightcolor=[("selected", CARD)], expand=[("selected", (0, 2, 0, 0))])
    for field in ("Cute.TEntry", "Cute.TCombobox", "Cute.TSpinbox"):
        st.configure(field, fieldbackground="#fff8fb", foreground=TEXT, bordercolor=PINK, lightcolor="#ffd0de",
                     darkcolor="#ffd0de", insertcolor=PINK_DARK, padding=4, arrowcolor=PINK_DARK, background=PINK_SOFT,
                     selectbackground=PINK, selectforeground="#ffffff")
        st.map(field, bordercolor=[("disabled", "#f0d6de"), ("focus", PINK_DARK)], lightcolor=[("focus", PINK)],
               darkcolor=[("focus", PINK)], background=[("active", "#ffd0de")], arrowcolor=[("disabled", "#e6c3cd")],
               fieldbackground=[("disabled", "#f7eef1"), ("readonly", "#fff8fb")], foreground=[("disabled", "#c4a7b1")])
    st.configure("Pink.TButton", background=PINK, foreground="#ffffff", font=bold, borderwidth=0, padding=(16, 7),
                 lightcolor=PINK, darkcolor=PINK, focuscolor=PINK)
    st.map("Pink.TButton", background=[("active", PINK_DARK), ("pressed", PINK_DARK)],
           lightcolor=[("active", PINK_DARK)], darkcolor=[("active", PINK_DARK)])
    st.configure("Soft.TButton", background=PINK_SOFT, foreground=TEXT, font=font, borderwidth=0, padding=(14, 7),
                 lightcolor=PINK_SOFT, darkcolor=PINK_SOFT, focuscolor=PINK_SOFT)
    st.map("Soft.TButton", background=[("active", "#ffd0de")], lightcolor=[("active", "#ffd0de")],
           darkcolor=[("active", "#ffd0de")])
    win.option_add("*TCombobox*Listbox.background", "#fff8fb")  # danh sách thả xuống của ô chọn model
    win.option_add("*TCombobox*Listbox.foreground", TEXT)
    win.option_add("*TCombobox*Listbox.selectBackground", PINK)
    win.option_add("*TCombobox*Listbox.font", font)


def _tick_images(size=22):
    """Ô tích tự vẽ (ô của ttk hiện dấu x nhỏ, trông như đang tắt): tắt = ô viền hồng, bật = ô hồng đậm có dấu ✓ trắng."""
    big, out = size * 4, []
    for on in (False, True):
        im = Image.new("RGBA", (big, big), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((4, 4, big - 5, big - 5), radius=big // 4, fill=PINK_DARK if on else "#fff8fb",
                            outline=PINK_DARK if on else PINK, width=8)
        if on:
            d.line([(big * 0.27, big * 0.52), (big * 0.44, big * 0.69), (big * 0.74, big * 0.33)], fill="#ffffff",
                   width=11, joint="curve")
        flat = Image.new("RGBA", im.size, CARD)
        flat.alpha_composite(im)
        out.append(ImageTk.PhotoImage(flat.resize((size, size), Image.LANCZOS)))
    return out


def _tick(parent, var, text="", ticks=None):
    return tk.Checkbutton(parent, variable=var, text=text, image=ticks[0], selectimage=ticks[1], indicatoron=False,
                          compound="left", padx=0, bd=0, relief="flat", offrelief="flat", overrelief="flat",
                          highlightthickness=0, bg=CARD, activebackground=CARD, selectcolor=CARD, fg=TEXT,
                          activeforeground=TEXT, font=("Segoe UI", 10), cursor="hand2")


def open_window(root, on_saved):
    if _window[0] is not None and _window[0].winfo_exists():
        _window[0].deiconify()
        _window[0].lift()
        return _window[0].focus_force()
    win = _window[0] = tk.Toplevel(root, bg=BG)
    win.title(TITLE)
    win.resizable(False, False)
    try:
        win.iconbitmap(str(ICON_FILE))  # icon ở góc cửa sổ và ở taskbar
    except tk.TclError:
        pass
    _style(win)
    ticks = win.ticks = _tick_images()  # giữ tham chiếu ảnh theo cửa sổ

    head = tk.Frame(win, bg=BG, padx=20, pady=14)
    head.pack(fill="x")
    face = ImageTk.PhotoImage(_badge(EMOTE_DIR / "mim_cuoi.png"))
    pic = tk.Label(head, image=face, bg=BG, bd=0)
    pic.image = face  # giữ tham chiếu, kẻo Tk mất ảnh
    pic.pack(side="left")
    words = tk.Frame(head, bg=BG, padx=14)
    words.pack(side="left")
    tk.Label(words, text=f"{TITLE} ♥", bg=BG, fg=PINK_DARK, font=("Segoe UI", 20, "bold")).pack(anchor="w")
    tk.Label(words, text=tr("Chỉnh mình theo ý bạn nè~ ✿"), bg=BG, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w")

    tabs = ttk.Notebook(win, style="Cute.TNotebook")
    tabs.pack(fill="both", expand=True, padx=16)
    fields, pages, widgets = {}, {}, {}
    opts = {k: {code: tr(name) for code, name in m.items()} for k, m in CHOICES.items()}  # mã -> tên hiện ra
    for key, label, group, kind, lo, hi in SETTINGS:
        if group not in pages:
            pages[group] = ttk.Frame(tabs, style="Cute.TFrame", padding=(20, 16))
            pages[group].columnconfigure(1, weight=1)
            tabs.add(pages[group], text=f"{ICONS.get(group, '♡')} {tr(group)}")
        page, row = pages[group], len(pages[group].grid_slaves(column=0))
        value = getattr(config, key)
        ttk.Label(page, text=tr(label), style="Cute.TLabel").grid(row=row, column=0, sticky="w", pady=6, padx=(0, 16))
        if kind == "bool":
            var = tk.BooleanVar(value=value)
            _tick(page, var, ticks=ticks).grid(row=row, column=1, sticky="w")
        else:
            var = tk.StringVar(value=round(value * 100) if kind == "pct" else opts[key].get(value, value)
                               if kind == "choice" else value)
            if kind == "choice":  # hiện tên dễ hiểu, lưu thì đổi lại thành mã ("ollama" / "api", "vi" / "en")
                widget = ttk.Combobox(page, textvariable=var, values=list(opts[key].values()), state="readonly",
                                      width=40, style="Cute.TCombobox", font=("Segoe UI", 10))
            elif kind == "text" and (key.endswith("MODEL") or key == "API_BASE"):  # gõ tay được, hoặc chọn từ danh sách
                widget = ttk.Combobox(page, textvariable=var, width=40, style="Cute.TCombobox", font=("Segoe UI", 10),
                                      values=list(API_PRESETS.values()) if key == "API_BASE" else [])
            elif kind == "secret":
                widget = ttk.Entry(page, textvariable=var, width=42, show="•", style="Cute.TEntry", font=("Segoe UI", 10))
            elif kind == "text":
                widget = ttk.Entry(page, textvariable=var, width=32, style="Cute.TEntry", font=("Segoe UI", 10))
            else:
                widget = ttk.Spinbox(page, textvariable=var, from_=lo, to=hi, width=8, style="Cute.TSpinbox",
                                     font=("Segoe UI", 10))
            widget.grid(row=row, column=1, sticky="w")
            widgets[key] = widget
        fields[key] = var

    model_page = pages["Model"]
    note = ttk.Label(model_page, style="Note.TLabel", justify="left")
    note.grid(row=len(model_page.grid_slaves(column=0)), column=0, columnspan=2, sticky="w", pady=(12, 0))
    refresh = ttk.Button(model_page, text=tr("↻ Lấy danh sách model"), style="Soft.TButton")
    refresh.grid(row=len(model_page.grid_slaves(column=0)), column=0, sticky="w", pady=(10, 0))
    notes = {
        "ollama": tr("Cần cài Ollama (ollama.com) và tải model về trước, vd: ollama pull qwen2.5vl:7b\n"
                   "Ollama chạy ngay trên máy này: để http://localhost:11434\n"
                   "Chạy trên máy khác (máy bàn, Mac, server...): điền địa chỉ máy đó, vd: http://192.168.1.10:11434\n"
                   "Model nhìn màn hình phải là loại đọc được ảnh (vd: qwen2.5vl, qwen3-vl, gemma3)."),
        "api": tr("Chọn địa chỉ API của nhà cung cấp (OpenAI, Gemini, OpenRouter, Groq) hoặc dán địa chỉ khác theo chuẩn\n"
                "OpenAI, rồi dán API key lấy trên trang của họ. Key được mã hoá theo tài khoản Windows trước khi lưu.\n"
                "Model nhìn màn hình phải đọc được ảnh (vd: gpt-4o-mini, gemini-2.5-flash). Dùng API sẽ tốn phí theo\n"
                "mỗi lần gọi (mỗi lần bình luận màn hình là một lần gửi ảnh), xem bảng giá của nhà cung cấp."),
    }
    to_code = {name: code for code, name in opts["PROVIDER"].items()}

    def load_models():
        """Luồng phụ chỉ cất kết quả vào got; luồng giao diện tự xem mỗi 0.1s rồi mới đụng Tk (Tk không an toàn đa luồng)."""
        got = []
        refresh.config(text=tr("↻ Đang lấy danh sách..."))
        _models(to_code.get(fields["PROVIDER"].get(), "ollama"), fields["HOST"].get(), fields["API_BASE"].get(),
                fields["API_KEY"].get(), got.append)

        def check():
            if not win.winfo_exists():
                return
            if not got:
                return win.after(100, check)
            names, why = got[0]
            for key in ("VISION_MODEL", "ANSWER_MODEL"):
                widgets[key].config(values=names)
            refresh.config(text=tr("↻ Lấy danh sách model ({n} model)").format(n=len(names)) if names
                           else tr("↻ Chưa lấy được: {why}").format(why=why))
        check()

    notes["off"] = tr("Đang tắt AI (hợp với máy yếu, không có máy chạy Ollama hay API): Claude-chan không chụp màn hình,\n"
                    "không bình luận; vẫn đi dạo, nấp, chơi đùa, nhắc nghỉ, nhắc khuya, tập trung như thường.\n"
                    "Hỏi thì vẫn hiểu nhờ nhắc việc (\"15 phút nữa nhắc mình uống nước\") và giờ tập trung\n"
                    "(\"mình code 40 phút\"); câu hỏi khác cần bật \"Trả lời câu hỏi\".")
    one_model = tr("\nChỉ chạy được một model? Model đọc được ảnh trả lời câu hỏi được luôn: chọn cùng model cho hai ô.\n"
                 "Model chỉ đọc chữ (vd gpt-oss) thì tắt \"Bình luận màn hình\", chỉ để trả lời câu hỏi.")

    def sync(_=None):  # mờ phần không dùng: tắt cả hai thì mờ hết; chỉ bật một việc thì mờ ô model của việc kia;
        comment, answer = fields["COMMENT_ON"].get(), fields["ANSWER_ON"].get()  # Ollama thì mờ API và ngược lại
        on, api = comment or answer, to_code.get(fields["PROVIDER"].get()) == "api"
        widgets["PROVIDER"].state(["!disabled"] if on else ["disabled"])
        widgets["VISION_MODEL"].state(["!disabled"] if comment else ["disabled"])
        widgets["ANSWER_MODEL"].state(["!disabled"] if answer else ["disabled"])
        widgets["HOST"].state(["!disabled"] if on and not api else ["disabled"])
        for key in ("API_BASE", "API_KEY"):
            widgets[key].state(["!disabled"] if on and api else ["disabled"])
        refresh.state(["!disabled"] if on else ["disabled"])
        note.config(text=notes["off"] if not on else notes["api" if api else "ollama"] + one_model)

    refresh.config(command=load_models)
    widgets["PROVIDER"].bind("<<ComboboxSelected>>", lambda e: (sync(), load_models()))
    # dán key / đổi địa chỉ xong (rời khỏi ô, chọn từ danh sách, bấm Enter) thì tự lấy lại danh sách model
    for key, events in (("API_KEY", ("<FocusOut>", "<Return>")), ("API_BASE", ("<<ComboboxSelected>>", "<FocusOut>", "<Return>")),
                        ("HOST", ("<FocusOut>", "<Return>"))):
        for event in events:
            widgets[key].bind(event, lambda e: load_models() if str(e.widget.cget("state")) != "disabled" else None, add="+")
    for key in ("COMMENT_ON", "ANSWER_ON"):  # bật / tắt từng việc: mờ hoặc sáng các ô model ngay
        fields[key].trace_add("write", lambda *_: sync())
    sync()

    start = ttk.Frame(tabs, style="Cute.TFrame", padding=(20, 16))
    tabs.add(start, text=f"{ICONS['Khởi động']} {tr('Khởi động')}")
    auto = tk.BooleanVar(value=autostart_on())
    _tick(start, auto, tr("  Tự chạy Claude-chan khi bật máy"), ticks).pack(anchor="w", pady=6)
    ttk.Label(start, text=tr("Cài đặt được lưu ở {file}, trong thư mục {folder}").format(file=SETTINGS_FILE.name,
                                                                                         folder=SETTINGS_FILE.parent.name),
              style="Note.TLabel").pack(anchor="w", pady=(10, 0))

    load_models()

    def save():
        values, errors = {}, []
        for key, label, _, kind, lo, hi in SETTINGS:
            try:
                raw = fields[key].get()
                codes = {name: code for code, name in opts.get(key, {}).items()}
                values[key] = coerce_setting(kind, lo, hi, codes.get(raw, raw) if kind == "choice" else raw)
            except (ValueError, tk.TclError) as e:
                errors.append(f"• {tr(label)}: {e if str(e) and 'could not' not in str(e) else tr('không hợp lệ')}")
        if errors:
            return messagebox.showerror(TITLE, tr("Chưa lưu được nè:\n") + "\n".join(errors), parent=win)
        for key, _, _, kind, _, _ in SETTINGS:  # API key: mã hoá theo tài khoản Windows, file không chứa key trần
            if kind == "secret":
                values[key] = protect(values[key])
        SETTINGS_FILE.write_text(json.dumps(values, ensure_ascii=False, indent=2), encoding="utf-8")
        try:
            if auto.get() != autostart_on():
                set_autostart(auto.get())
        except (OSError, subprocess.CalledProcessError):
            messagebox.showwarning(TITLE, tr("Lưu cài đặt rồi, nhưng chưa đổi được chế độ tự chạy khi bật máy."), parent=win)
        win.destroy()
        on_saved()

    def reset():
        if messagebox.askyesno(TITLE, tr("Đưa mọi cài đặt về mặc định rồi chạy lại Claude-chan?"), parent=win):
            SETTINGS_FILE.unlink(missing_ok=True)
            win.destroy()
            on_saved()

    bar = tk.Frame(win, bg=BG, padx=16, pady=14)
    bar.pack(fill="x")
    ttk.Button(bar, text=tr("↺ Về mặc định"), command=reset, style="Soft.TButton").pack(side="left")
    ttk.Button(bar, text=tr("Đóng"), command=win.destroy, style="Soft.TButton").pack(side="right")
    ttk.Button(bar, text=tr("♥ Lưu và chạy lại"), command=save, style="Pink.TButton").pack(side="right", padx=8)
    win.update_idletasks()
    x, y = (win.winfo_screenwidth() - win.winfo_width()) // 2, (win.winfo_screenheight() - win.winfo_height()) // 3
    win.geometry(f"+{x}+{y}")
    win.lift()
    win.focus_force()
    return win


def _badge(path, size=76):
    """Ảnh nhân vật trong khung tròn hồng viền đậm (vẽ lớn rồi thu nhỏ cho mép tròn mịn)."""
    big = size * 4
    disc = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(disc)
    d.ellipse((0, 0, big - 1, big - 1), fill=PINK)
    d.ellipse((12, 12, big - 13, big - 13), fill=PINK_SOFT)
    face = Image.open(path).convert("RGBA").resize((big - 40, big - 40), Image.LANCZOS)
    mask = Image.new("L", disc.size, 0)
    ImageDraw.Draw(mask).ellipse((12, 12, big - 13, big - 13), fill=255)
    layer = Image.new("RGBA", disc.size, (0, 0, 0, 0))
    layer.paste(face, (20, 28), face)
    disc.paste(layer, (0, 0), Image.composite(layer, Image.new("RGBA", disc.size, (0, 0, 0, 0)), mask))
    flat = Image.new("RGBA", disc.size, BG)
    flat.alpha_composite(disc)
    return flat.resize((size, size), Image.LANCZOS)
