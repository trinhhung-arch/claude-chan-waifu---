"""Đọc câu trả lời JSON của model: lời nói + emote, điều cần nhớ, lời nhờ nhắc, số phút tập trung."""
import json
import re

from ..core.config import CHAT_EMOTES, EMOTES, tr

# tên emote lọt vào lời nói (":co_vu:", "(co_vu)", "[emote: soc]", "co_vu" đứng trơ...) và mã kiểu ":abc_xyz:": model
# thỉnh thoảng viết cả tên emote vào câu, bong bóng hiện nguyên chữ đó. Tên một chữ không gạch dưới (buon, soc) chỉ bỏ
# khi có dấu hiệu là tên emote (bọc ":" / ngoặc / sau "emote:"), kẻo xoá nhầm chữ trong code như hàm buon()
_NAMES = "|".join(sorted(map(re.escape, EMOTES), key=len, reverse=True))
_UNDERSCORED = "|".join(re.escape(e) for e in EMOTES if "_" in e)
_EMOTE_TAG = re.compile(
    rf"[\[(]\s*(?:emote\s*[:=]\s*)?:?(?:{_NAMES}):?\s*[\])]"  # (co_vu)  [emote: soc]  (:buon:)
    rf"|(?:emote\s*[:=]\s*)(?:{_NAMES})\b"  # emote: soc
    rf"|:(?:{_NAMES}):"  # :soc:
    rf"|\b(?:{_UNDERSCORED})\b"  # co_vu đứng trơ (tên có gạch dưới, câu tiếng Việt không viết vậy)
    r"|:[a-z]+(?:_[a-z]+)+:",  # mã emoji :thumbs_up:
    re.IGNORECASE)


def clean(line):
    """Bỏ tên emote / mã emoji khỏi lời nói, gộp khoảng trắng thừa, bỏ dấu cách đứng trước dấu câu."""
    line = " ".join(_EMOTE_TAG.sub(" ", line).split())
    return re.sub(r"\s+([.,!?~])", r"\1", line)


UNIT = r"(phút|ph|p|tiếng|giờ|h|minutes?|mins?|hours?|hrs?)\b"
HOUR_UNITS = ("tiếng", "giờ", "h", "hour", "hours", "hr", "hrs")


def quick_intent(text):
    """Hiểu câu nhờ không cần model (tiếng Việt lẫn tiếng Anh): "15 phút nữa nhắc mình uống nước" / "remind me to drink
    water in 15 minutes" -> nhắc (15, việc); "mình code 40 phút" / "học 1 tiếng" / "study for half an hour" -> tập trung
    40 / 60 / 30 phút. -> (nhắc hoặc None, phút hoặc None)."""
    low = " ".join(text.lower().split())
    m = re.search(r"(\d+)\s*" + UNIT, low)
    if m:
        minutes = int(m.group(1)) * (60 if m.group(2) in HOUR_UNITS else 1)
    elif re.search(r"nửa (tiếng|giờ)|half an? hour|half hour", low):
        minutes = 30
    else:
        minutes = 60 if re.search(r"\b(an|one) hour\b", low) else None
    if not minutes or not 1 <= minutes <= 24 * 60:
        return None, None
    key = "nhắc" if "nhắc" in low else "remind" if re.search(r"\bremind", low) else None
    if key:
        what = low.split(key, 1)[1].strip()
        what = re.sub(r"^(mình|tôi|tớ|em|anh|chị|bạn|tui|t|me|us)\s+", "", what)
        # bỏ cụm thời gian: "sau 2 tiếng nữa", "in 15 minutes", "after half an hour"
        what = re.sub(r"\s*(sau|trong|in|after|for)?\s*(\d+|nửa|half an?|an|one)\s*" + UNIT + r"(\s*nữa)?", " ", what)
        what = re.sub(r"^to\s+", "", " ".join(what.split()))
        what = re.sub(r"\s*(nhé|nha|nhá|với|giúp|giùm|đi|nhe|please|pls)?[.!~ ]*$", "", what).strip()
        return (minutes, what[:100] or tr("việc bạn nhờ")), None
    if (any(w in low for w in ("tập trung", "làm", "học", "code", "viết", "ôn"))
            or re.search(r"\b(focus|work|working|study|studying|coding|write|writing|learn|learning)\b", low)) \
            and minutes <= 240:
        return None, minutes
    return None, None


def parse(content):
    """Câu trả lời của model -> (lời nói, emote); emote lạ thì về mim_cuoi."""
    try:
        data = json.loads(content)
        line, emote = str(data.get("loi_noi", "")).strip(), data.get("emote")
    except (json.JSONDecodeError, AttributeError):
        line, emote = str(content).strip(), None
    return clean(line) or "...", emote if emote in CHAT_EMOTES else "mim_cuoi"


def parse_explaining(content):
    """"giai_thich" = true: câu trả lời đang giải thích / dạy / chỉ cách làm gì đó (lúc đó luôn đeo kính mọt sách)."""
    try:
        return json.loads(content).get("giai_thich") is True
    except (json.JSONDecodeError, AttributeError):
        return False


def parse_facts(content):
    """Lấy danh sách "ghi_nho" trong câu trả lời của model; hỏng thì coi như không có gì mới."""
    try:
        facts = json.loads(content).get("ghi_nho", [])
    except (json.JSONDecodeError, AttributeError):
        return []
    if not isinstance(facts, list):
        return []
    return [" ".join(str(f).split())[:200] for f in facts if str(f).strip()][:5]


def parse_reminder(content):
    """"nhac_phut"/"nhac_viec" trong câu trả lời -> (phút, việc), hoặc None nếu không nhờ nhắc / số phút vô lý."""
    try:
        data = json.loads(content)
        minutes, what = int(data.get("nhac_phut") or 0), " ".join(str(data.get("nhac_viec") or "").split())
    except (json.JSONDecodeError, AttributeError, TypeError, ValueError):
        return None
    return (minutes, what[:100] or tr("việc bạn nhờ")) if 1 <= minutes <= 24 * 60 else None


def parse_focus(content):
    """"tap_trung_phut" -> số phút người dùng nói sẽ làm việc/học tập trung (1-240), không có thì None."""
    try:
        minutes = int(json.loads(content).get("tap_trung_phut") or 0)
    except (json.JSONDecodeError, AttributeError, TypeError, ValueError):
        return None
    return minutes if 1 <= minutes <= 240 else None
