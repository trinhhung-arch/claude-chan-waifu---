"""Hành vi tự phát: phản ứng khi chuyển sang code / game / chat, rảnh lâu thì tự đổi dáng / đi dạo / trốn ra rìa
ló đầu, cổ vũ khi thấy gõ phím hăng say. start(char, state) rồi để nó tự chạy."""
import random
import re
import threading
import time
from collections import deque

from ..core.config import (APP_COOLDOWN_MINUTES, APP_EMOTES, APP_QUIET_SECONDS, IDLE_POSE_SECONDS, IDLE_POSES, NIGHT_HOURS,
                           PEEK_CHANCE, PERCH_CHANCE, TITLE, TYPING_CHEER_COOLDOWN, TYPING_CHEER_MINUTES, WALK_CHANCE,
                           YAWN_EMOTE, MUSIC_APPS, MUSIC_ON, MUSIC_WORDS, SIZE)
from ..desktop import active_title, clipboard_image, clipboard_image_seq, fullscreen, idle_seconds, now_playing, screenshot_keys
from ..dialogue import pick
from ..memory import likes, load_memory
from ..vision import grab_screen, is_private, locate
from ._apps import app_category

__all__ = ["app_category", "is_favorite", "is_music", "on_youtube", "song_name", "start"]


SNAP_WAIT = 15  # bấm chụp màn hình mà chừng này giây chưa có ảnh nào (hủy) thì dỗi "không chụp mình à"


def is_music(playing):
    """(tên, ca sĩ / kênh, app) đang phát có phải nhạc không: app nghe nhạc thì luôn là nhạc; trình duyệt (YouTube...)
    thì tên phải có dấu hiệu bài hát, kẻo video thường / podcast cũng nhún."""
    if not playing:
        return False
    title, _, app = (str(x).lower() for x in playing)
    return any(a in app for a in MUSIC_APPS) or any(w in f" {title}" for w in MUSIC_WORDS)


def on_youtube(title):
    """Cửa sổ đang mở là tab YouTube (tiêu đề trình duyệt kết thúc bằng "- YouTube", hoặc YouTube Music)."""
    return "youtube" in title.lower()


def is_favorite(title, liked):
    """Bài đang phát có phải bài người dùng thích (trong ký ức) không: "Thích bài hát Letter From Ajax" khớp tiêu đề
    "Letter From Ajax (Official MV)". Bỏ chữ "bài hát / nghe" đầu, tên quá ngắn (< 4 ký tự) thì bỏ qua cho khỏi khớp bừa."""
    low = title.lower()
    for thing in liked:
        song = re.sub(r"^(nghe\s+)?(bài hát|bài|ca khúc|song|the song)\s+", "", thing, flags=re.IGNORECASE).strip(" '\"")
        if len(song) >= 4 and song.lower() in low:
            return True
    return False


def song_name(title):
    """Tên bài gọn để nói: bỏ phần thêm kiểu "| Lyrics...", "(Official MV)", "【...】", tối đa ~40 ký tự."""
    for cut in ("|", "(", "[", "【", "『", " - Official", " ft.", " feat"):
        head = title.split(cut)[0].strip()
        title = head or title
    return title[:40].rstrip() + ("…" if len(title) > 40 else "")


def start(char, state):
    seen = {"cat": None, "at": {}}  # loại app đang mở, lần cuối phản ứng với từng loại

    def track():
        """Nhớ tiêu đề cửa sổ khác gần nhất (lúc người dùng bấm vào nhân vật thì nó mới là cửa sổ cần xét riêng tư),
        và phản ứng ngay khi chuyển sang code / game / chat: mỗi loại 10 phút tối đa 1 lần, không chen ngang câu
        vừa nói (20 giây), không nói khi đang tạm dừng (đã hứa không nhìn), ngủ, ẩn, gõ câu hỏi hay ở cửa sổ riêng tư."""
        title = active_title()
        if title != TITLE:
            state.seen_title = title
            cat, now = app_category(title, fullscreen()), time.time()
            if cat != seen["cat"]:
                seen["cat"] = cat
                quiet = (state.paused.is_set() or state.sleeping.is_set() or state.hidden.is_set() or state.dragging.is_set()
                         or char.asking or char.thinking or is_private(title) or now - char.last_said < APP_QUIET_SECONDS)
                if cat and not quiet and now - seen["at"].get(cat, 0) > APP_COOLDOWN_MINUTES * 60:
                    seen["at"][cat] = now
                    char.say(pick(cat), APP_EMOTES[cat])
        char.root.after(500, track)

    def idle_pose():
        """Im lặng lâu thì tự đổi dáng hoặc đi dạo (không nói) cho đỡ đứng im như tượng; đang ngủ thì để yên."""
        if (time.time() - char.last_said > IDLE_POSE_SECONDS and not char.walk["job"] and not char.peek
                and not char.airborne and not char.petting and not char.playing and not (state.sleeping.is_set() or state.hidden.is_set() or char.asking or char.thinking)):
            roll, free = random.random(), char.walk["on"] and not char.pointer_on_me()  # tắt đi dạo là thôi mọi trò di chuyển
            if free and roll < WALK_CHANCE:
                char.start_walk()  # đang đứng trên cửa sổ thì đi dọc mép cửa sổ đó
            elif free and roll < WALK_CHANCE + PEEK_CHANCE:
                char.hop_down() if char.perch else char.start_peek()  # trên cửa sổ: nhảy xuống; dưới đất: trốn ra rìa ló đầu
            elif free and roll < WALK_CHANCE + PEEK_CHANCE + PERCH_CHANCE and char.hop_to_window():
                pass  # nhảy lên mép trên một cửa sổ đang mở
            else:
                late = time.localtime().tm_hour >= 22 or time.localtime().tm_hour in NIGHT_HOURS
                poses = IDLE_POSES + [YAWN_EMOTE] * 2 * late  # về khuya: hay ngáp
                char.pose(random.choice([e for e in poses if e != char.cur["emote"]]))
            char.last_said = time.time() - random.randint(0, IDLE_POSE_SECONDS // 2)  # lần sau lệch chút cho tự nhiên
        char.root.after(5000, idle_pose)

    def calm(gap):  # rảnh để nói chen một câu: không đang nói / nghĩ / hỏi / bị kéo / trốn / đi dạo / ngủ / ẩn / tạm dừng
        return not (char.talking or char.asking or char.thinking or char.peek or char.walk["job"] or char.airborne or char.petting or char.playing
                    or state.dragging.is_set() or state.sleeping.is_set() or state.hidden.is_set() or state.paused.is_set()
                    or time.time() - char.last_said < gap)

    typing = {"keys": deque(maxlen=round(TYPING_CHEER_MINUTES * 60)), "p": None, "last": time.time()}

    def typing_cheer():
        """Mỗi giây: có bấm gì mà chuột đứng yên = đang gõ phím (Windows không cho biết phím hay chuột nếu không móc
        bàn phím). Gõ gần như liên tục TYPING_CHEER_MINUTES phút thì cầm lightstick cổ vũ một câu."""
        p, keys = char.root.winfo_pointerxy(), typing["keys"]
        keys.append(idle_seconds() < 1.5 and p == typing["p"])
        typing["p"] = p
        if (len(keys) == keys.maxlen and sum(keys) > 0.7 * keys.maxlen and calm(30)
                and time.time() - typing["last"] > TYPING_CHEER_COOLDOWN * 60):
            typing["last"] = time.time()
            keys.clear()
            char.say(pick("typing_cheer"), "co_vu")
        char.root.after(1000, typing_cheer)

    snap = {"last": 0.0, "seq": None}  # seq: số đếm clipboard lúc vừa bấm chụp, chờ xem có ảnh mới không

    def snap_pose():
        """Bấm chụp màn hình (PrtSc / Win+Shift+S) thì quay ra nháy mắt làm dấu OK, tia lấp lánh bay quanh, kịp lọt vào
        ảnh. Hỏi phím mỗi 50ms; 8 giây tối đa một lần; đang ẩn / ngủ / tạm dừng / gõ câu hỏi / nghĩ / giải thích /
        bị kéo thì thôi."""
        pressed = screenshot_keys()  # hỏi đều mỗi lượt để xoá dấu "đã bấm" cũ
        busy = (state.hidden.is_set() or state.sleeping.is_set() or state.paused.is_set() or state.dragging.is_set()
                or char.asking or char.answering)
        if pressed and not busy and time.time() - snap["last"] > 8:
            snap["last"] = time.time()
            char.say(pick("snap"), "nhay_mat_ok")
            char.burst("sparkle", 5)
            snap["seq"] = clipboard_image_seq()[0]
            r = char.root  # màn hình lúc bấm + chỗ hình nhân vật: có ảnh chụp thì dò xem ảnh có lọt nhân vật không
            snap["shot"] = grab_screen()
            snap["her"] = (r.winfo_rootx() + (r.winfo_width() - SIZE) // 2, r.winfo_rooty() + r.winfo_height() - SIZE)
        if snap["seq"] is not None:  # đã tạo dáng: chụp xong thì ảnh vào clipboard; hủy (Esc) / 15 giây chưa có thì dỗi
            seq, image = clipboard_image_seq()
            if seq != snap["seq"] and image:
                snap["seq"] = None
                if not in_shot(clipboard_image()):
                    char.say(pick("snap_missed"), "gian_doi")
            elif time.time() - snap["last"] > SNAP_WAIT:
                snap["seq"] = None
                if not (state.hidden.is_set() or char.asking or char.answering):
                    char.say(pick("snap_skip"), "gian_doi")
        char.root.after(50, snap_pose)

    def in_shot(img):
        """Ảnh vừa chụp có lọt ít nhất 1/4 hình nhân vật không; không đọc được / không dò ra vị trí thì coi như có."""
        if img is None:
            return True
        full, left, top = snap["shot"]
        pos = locate(full, img)
        if pos is None:
            return True
        hx, hy = snap["her"][0] - left, snap["her"][1] - top
        ox = min(pos[0] + img.width, hx + SIZE) - max(pos[0], hx)
        oy = min(pos[1] + img.height, hy + SIZE) - max(pos[1], hy)
        return ox > 0 and oy > 0 and ox * oy >= 0.25 * SIZE * SIZE

    music = {"playing": None, "title": None, "danced": time.time() - 40, "gap": 60, "mentioned": 0.0}

    def watch_music():  # luồng phụ: hỏi Windows mỗi 5 giây (không đụng Tk, chỉ ghi vào music)
        while True:
            try:
                music["playing"] = now_playing()
            except Exception:  # dịch vụ nhạc của Windows lỗi lặt vặt: coi như không nghe gì, lượt sau hỏi lại
                music["playing"] = None
            time.sleep(5)

    def groove():
        """Đang nghe nhạc mà rảnh: đổi bài thì nhắc tên bài (15 phút tối đa một lần), còn lại cứ 1-2 phút nhún một đợt."""
        playing, now = music["playing"], time.time()
        if MUSIC_ON and is_music(playing) and not char.dancing and calm(10):
            fav = playing[0] != music["title"] and is_favorite(playing[0], likes(load_memory()))
            if fav:  # bài bạn thích: reo lên ngay, không cần chờ 15 phút
                music.update(title=playing[0], mentioned=now, danced=now)
                char.say(pick("music_fav", what=song_name(playing[0])), "phan_khich")
                char.burst("heart", 3)
            elif playing[0] != music["title"] and now - music["mentioned"] > 15 * 60:
                music.update(title=playing[0], mentioned=now, danced=now)
                char.say(pick("music", what=song_name(playing[0])), "lap_lanh")
            elif now - music["danced"] > music["gap"] and on_youtube(active_title()):  # chỉ nhảy khi đang xem YouTube
                music.update(danced=now, gap=random.randint(60, 120))
                char.dance(random.randint(6, 10))
            music["title"] = playing[0]
        char.root.after(1000, groove)

    track()
    char.root.after(5000, idle_pose)
    threading.Thread(target=watch_music, daemon=True).start()
    char.root.after(3000, groove)
    typing_cheer()
    snap_pose()
