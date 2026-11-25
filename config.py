"""Cấu hình và hằng số của Claude-chan: model, thời gian, câu thoại, mô tả emote, đường dẫn file."""
import sys
from pathlib import Path

# ===== Cấu hình =====
HOST = "http://100.105.62.59:11434"  # IP Tailscale của máy Mac (macbook-pro-ca-trnh)
MODEL = "qwen2.5vl:32b"
INTERVAL = 45  # giây giữa 2 lần nhìn màn hình
GAME_INTERVAL = 180  # khi đang chơi game / xem video toàn màn hình thì nói thưa hơn
AWAY_MINUTES = 5  # không chạm chuột/bàn phím quá chừng này phút: nhân vật ngủ gục, ngừng chụp màn hình
TIRED_HOURS = 2  # ngồi máy liên tục quá chừng này tiếng: nhân vật buồn ngủ, nhắc nghỉ (rồi mỗi tiếng nhắc lại)
NIGHT_HOURS = range(0, 5)  # từ 0h tới trước 5h sáng: nhắc đi ngủ (một lần mỗi đêm)
LOW_BATTERY = 20  # pin dưới chừng này % (mà không cắm sạc) thì nhắc
IDLE_POSES = ["mim_cuoi", "suy_tu", "le_luoi"]  # lâu không nói gì thì thỉnh thoảng tự đổi qua lại các dáng này
IDLE_POSE_SECONDS = 90  # im lặng chừng này giây thì đổi dáng một lần
WALK = True  # rảnh thì thỉnh thoảng nhảy lò cò đi dạo ngang một đoạn (bật/tắt được trong menu khay)
WALK_CHANCE = 0.3  # mỗi lần rảnh, 30% là đi dạo, còn lại là đổi dáng
FOCUS_MINUTES, BREAK_MINUTES = 25, 5  # hẹn giờ tập trung (Pomodoro) trong menu khay
FOCUS_BLOCK = ["facebook", "tiktok", "youtube", "instagram", "reddit", "twitter"]  # mở mấy trang này lúc tập trung: bị nhắc
CLIP_MAX = 2000  # "Hỏi về đoạn vừa copy" gửi tối đa chừng này ký tự
SIZE = 220  # cỡ emote (px)
BUBBLE_SECONDS = 15
PERSONA = (
    "Bạn là một cô bé tóc hồng tinh nghịch ngồi ở góc màn hình, đang xem người dùng làm việc trên máy tính. "
    "Nói tiếng Việt, xưng 'mình', gọi người dùng là 'bạn' (đừng đoán là anh hay chị), tối đa 2 câu ngắn. "
    "Bình luận cụ thể về thứ đang thấy trên màn hình: "
    "cổ vũ, trêu nhẹ, nhắc nghỉ ngơi hoặc góp ý nhỏ. Nhân vật tóc hồng ở góc phải dưới màn hình là chính bạn, bỏ qua nó."
)
# Ý nghĩa từng emote, gửi kèm cho model để nó chọn đúng (tên phải khớp file trong V3_trong_suot)
EMOTE_GUIDE = {
    "mim_cuoi": "cười hiền. Mặc định khi bình thường, cổ vũ nhẹ nhàng",
    "nhay_mat_ok": "nháy mắt làm dấu OK. Khi việc ổn rồi, làm tốt lắm, đồng ý",
    "lap_lanh": "mắt lấp lánh há miệng. Khi có tin vui, thành công, thấy thứ hay ho",
    "phan_khich": "áp sát màn hình cười toe. Khi cực kỳ hào hứng, game gay cấn, vừa thắng",
    "le_luoi": "lè lưỡi vẫy tay. Khi trêu đùa vui vẻ, chào hỏi tinh nghịch",
    "tinh_quai": "mọc sừng quỷ cười gian. Khi bày trò, trêu chọc, xúi làm chuyện nghịch",
    "de_thuong": "ôm má phụng phịu. Khi làm nũng, được khen, thấy thứ dễ thương",
    "chay_mau_mui": "mặt đơ chảy máu mũi giơ ngón cái. Khi thấy nhân vật/ảnh đẹp hoặc dễ thương quá mức",
    "mot_sach": "đeo kính răng thỏ giơ ngón cái. CHỈ khi đang giải thích một điều gì đó: chỉ ra nguyên nhân, cách làm, "
                "nghĩa của từ/đoạn code. Chỉ khen người dùng đang code/học thì dùng co_vu",
    "suy_tu": "tay chống cằm. Khi đang nghĩ, câu hỏi khó, xem người dùng đọc hay phân tích gì đó",
    "cau_nguyen": "chắp tay cầu nguyện. Khi chờ build, chạy test, tải file, nộp bài, mong kết quả tốt",
    "co_vu": "nằm trên gối vẫy hai cây lightstick. Khi cổ vũ người dùng đang chăm chỉ làm bài, học, code, viết",
    "soc": "mắt tròn há hốc. Khi thấy lỗi đỏ, chuyện bất ngờ, máu thấp, sắp thua",
    "xau_ho": "lấy tay che mặt. Khi ngại ngùng, bị khen, thấy nội dung riêng tư hoặc khó xử",
    "gian_doi": "khoanh tay phụng phịu. Khi người dùng lướt mạng xã hội thay vì làm việc, hoặc lơ mình",
    "buon": "ôm gối mắt rưng rưng. Khi làm hỏng việc, thất bại, tin buồn",
    "buon_ngu": "nằm gục lên gối. Khi đã khuya, làm việc quá lâu, nên nghỉ ngơi",
}
# Tiêu đề cửa sổ đang mở chứa một trong các từ này (không phân biệt hoa thường) thì không chụp màn hình
PRIVATE_WORDS = ["bank", "ngân hàng", "password", "mật khẩu", "inprivate", "incognito", "ẩn danh",
                 "đăng nhập", "sign in", "login", "log in", "1password", "bitwarden", "keepass",
                 "momo", "zalopay", "vnpay", "paypal"]
MAX_MEMORY = 30  # nhớ tối đa chừng này điều về bạn, quá thì quên điều cũ nhất
HISTORY_TURNS = 3  # gửi kèm chừng này cặp hỏi-đáp gần nhất để hỏi tiếp được ("còn cái kia thì sao?")
# Câu nhân vật tự nói (không qua model). Mỗi lần chọn ngẫu nhiên một câu cho đỡ nhàm; thêm bớt thoải mái.
# {n} = " Tên" (hoặc trống), {h} = số tiếng, {p} = % pin, {m}/{b} = phút tập trung/nghỉ, {what} = việc cần nhắc
LINES = {
    "morning": ["Chào buổi sáng{n}! Hôm nay mình làm gì nè?", "Sáng rồi{n}! Uống nước chưa đó?",
                "Chào buổi sáng{n}~ Hôm nay cố lên nha!"],
    "noon": ["Trưa rồi{n}, ăn cơm chưa đó?", "Giữa trưa rồi{n}, nghỉ ăn chút đi nha~", "Trưa rồi nè{n}, đói chưa?"],
    "afternoon": ["Chào buổi chiều{n}! Cố lên nha.", "Chiều rồi{n}~ Uống miếng nước đi.", "Buổi chiều vui vẻ nha{n}!"],
    "evening": ["Tối rồi{n}, vẫn còn làm à?", "Chào buổi tối{n}~ Ăn tối chưa?", "Tối rồi nè{n}, làm xong sớm rồi nghỉ nha."],
    "late": ["Khuya rồi đó{n}... đừng thức muộn quá nha.", "Giờ này còn thức hả{n}? Ngủ sớm đi mà~",
             "Khuya lắm rồi{n}... mình buồn ngủ ghê."],
    "monday": ["Thứ Hai rồi{n}! Đầu tuần cố lên nha!", "Đầu tuần rồi{n}~ Tuần này mình làm gì nè?"],
    "friday": ["Thứ Sáu rồi{n}! Sắp cuối tuần rồi~", "Thứ Sáu nè{n}! Ráng nốt hôm nay thôi!"],
    "birthday": ["Chúc mừng sinh nhật{n}!!! Hôm nay phải vui thật nhiều nha!", "Sinh nhật vui vẻ{n}! Mình chúc bạn mọi điều tốt nhất~"],
    "tet": ["Chúc mừng năm mới{n}! An khang thịnh vượng nha~", "Tết vui vẻ{n}! Năm mới nhiều may mắn nè!"],
    "trung_thu": ["Trung thu vui vẻ{n}! Ăn bánh trung thu chưa?", "Rằm tháng Tám rồi{n}~ Trăng hôm nay chắc đẹp lắm!"],
    "pause": ["Mình che mắt rồi nha, bấm lại để mình xem tiếp.", "Không nhìn, không nhìn! Bấm lại khi nào cần mình nha.",
              "Ok, mình nhắm mắt đây~"],
    "resume": ["Mình xem tiếp đây!", "Mở mắt rồi nè!", "Cho mình xem tiếp với~"],
    "private": ["Chỗ này riêng tư, mình không nhìn đâu nha.", "Ơ, chỗ này riêng tư, mình quay đi đây~",
                "Mình che mắt chỗ này nha, yên tâm!"],
    "offline": ["Mình mất kết nối với máy Mac rồi... thử lại sau nha.", "Ơ, máy Mac không trả lời mình... lát thử lại nha."],
    "ask_fail": ["Mình không hỏi được máy Mac... thử lại sau nha.", "Máy Mac không trả lời rồi, hỏi lại sau nha..."],
    "ask_hint": ["Bạn muốn hỏi gì nè? Enter để gửi, Esc để thôi.", "Hỏi mình đi~ Enter để gửi, Esc để thôi."],
    "thinking": ["Để mình xem nào...", "Hmm, đợi mình chút...", "Để mình nghĩ đã~"],
    "away": ["Zzz... bạn đi đâu rồi, mình ngủ chút nha.", "Bạn đi đâu rồi... mình chợp mắt tí~", "Zzz..."],
    "back": ["A, bạn về rồi!", "Bạn về rồi nè! Mình đợi mãi~", "Ủa, về rồi hả? Làm tiếp thôi!"],
    "tired": ["Bạn ngồi {h} tiếng rồi đó... mình buồn ngủ quá, nghỉ chút đi.",
              "{h} tiếng rồi đó! Đứng dậy vươn vai chút đi mà~", "Ngồi {h} tiếng liền rồi... mắt mỏi chưa? Nghỉ tí nha."],
    "night": ["Quá 12 giờ đêm rồi... mình buồn ngủ quá, đi ngủ thôi.", "Nửa đêm rồi đó... mai làm tiếp nha, đi ngủ đi~"],
    "pat": ["Hehe, nhột quá~", "Xoa nữa đi~", "Ư ư... nhột mà!", "Hihi, thích ghê~"],
    "dragged": ["Ơ ơ, đi đâu vậy!", "Á á, thả mình xuống~", "Đừng xách cổ áo mình mà!", "Huhu, chóng mặt quá~"],
    "dropped": ["Hạ cánh an toàn~", "Phù, chỗ mới cũng được nè.", "Lần sau báo trước nha!", "Ui, tới nơi rồi hả?"],
    "battery": ["Pin còn {p}% thôi, cắm sạc đi kẻo sập máy!", "Ơ, pin còn có {p}%! Sạc đi sạc đi!"],
    "net_lost": ["Ơ... mất mạng rồi.", "Mạng đi đâu mất rồi..."],
    "net_back": ["Có mạng lại rồi!", "Mạng về rồi nè!"],
    "focus_start": ["Bắt đầu {m} phút tập trung! Cố lên nha!", "{m} phút tập trung nè, mình canh cho!"],
    "focus_stop": ["Dừng tập trung rồi nha.", "Ok, nghỉ tập trung nha~"],
    "focus_nag": ["Đang giờ tập trung mà! Tắt đi rồi làm tiếp nào.", "Ê ê, đang tập trung mà lướt gì đó?", "Hứ, hết giờ rồi hẵng xem!"],
    "focus_done": ["Xong {m} phút rồi, giỏi ghê! Nghỉ {b} phút đi, đứng dậy vươn vai nè.",
                   "Hết giờ tập trung! Nghỉ {b} phút cho mắt đỡ mỏi nha~"],
    "break_done": ["Hết giờ nghỉ rồi, quay lại làm tiếp nha!", "Nghỉ đủ rồi đó~ Làm tiếp thôi!"],
    "reminder": ["Đến giờ rồi nè: {what}!", "Ê, nhớ {what} nha!", "Tới giờ {what} rồi đó!"],
    "clip_empty": ["Bạn chưa copy chữ nào hết á. Bôi đen rồi Ctrl+C trước nha.", "Clipboard trống trơn à~ Copy chữ trước đã nha."],
    "clip_read": ["Để mình đọc đoạn bạn copy nào...", "Để mình xem đoạn này..."],
    "code": ["Code thôi nào!", "Mở code rồi kìa, cố lên!", "Lại code hả? Mình ngồi xem nha~"],
    "game": ["Chơi game hả? Cho mình xem với!", "Game gì đó? Thắng nha!", "Yay, giờ chơi game~"],
    "chat": ["Nhắn tin với ai đó~", "Ai nhắn đó? Hihi~", "Tám chuyện hả?"],
}
# Emote có con ngươi liếc hẳn sang một bên (ảnh gốc chưa lật): lật ảnh cho mắt nhìn về phía con trỏ chuột.
# Chỉ tính theo con ngươi, không theo độ nghiêng đầu: emote mắt nhìn thẳng mà lật theo nghiêng đầu thì trông như nhìn ngược.
FACING = {"soc": "right", "suy_tu": "right"}
# Âm lịch tra bảng (Tết = mùng 1 tháng Giêng, Trung thu = rằm tháng Tám), tới 2030
LUNAR = {"tet": ["2026-02-17", "2027-02-06", "2028-01-26", "2029-02-13", "2030-02-03"],
         "trung_thu": ["2026-09-25", "2027-09-15", "2028-10-03", "2029-09-22", "2030-09-12"]}
# Tiêu đề cửa sổ chứa từ này -> phản ứng ngay (không cần model). Game toàn màn hình nhận ra riêng.
APPS = {"code": ["visual studio code", "pycharm", "sublime text", "notepad++", "cursor"],
        "game": ["steam", "epic games", "riot client", "battle.net"],
        "chat": ["zalo", "messenger", "discord", "telegram"]}
APP_EMOTES = {"code": "co_vu", "game": "phan_khich", "chat": "tinh_quai"}  # mở code = bắt đầu làm bài: cổ vũ
APP_COOLDOWN_MINUTES = 10  # cùng một loại app thì 10 phút mới phản ứng lại một lần
APP_QUIET_SECONDS = 20  # vừa nói câu khác chưa tới chừng này giây thì không phản ứng app, khỏi chen ngang
# =====================

EMOTE_DIR =Path(__file__).parent / "V3_trong_suot"
EMOTES = sorted(p.stem for p in EMOTE_DIR.glob("*.png"))
DRAG_EMOTE = "bi_keo"  # ảnh lúc bị nhấc lên kéo đi: chỉ dùng khi kéo, model không được chọn
CHAT_EMOTES = [e for e in EMOTES if e != DRAG_EMOTE]  # emote model được chọn khi nói
POS_FILE = Path(__file__).parent / "vi_tri.txt"  # vị trí nhân vật sau lần kéo gần nhất
LOG_FILE = Path(__file__).parent / "nhat_ky.txt"  # giờ, loại, emote, câu nói (chỉ chữ, không lưu ảnh)
MEMORY_FILE = Path(__file__).parent / "ky_uc.txt"  # điều nhân vật nhớ về bạn, mỗi dòng một điều, sửa/xoá thoải mái
MEMORY_HEADER = "# Những điều nhân vật nhớ về bạn. Sửa hoặc xoá thoải mái, mỗi dòng một điều.\n"
SECRET_WORDS = ["mật khẩu", "password", "otp", "số tài khoản", "số thẻ", "cvv"]  # không bao giờ ghi nhớ
KEY = "#ff00fe"  # màu được Windows coi là trong suốt
TITLE = "Trợ lý màn hình"  # tiêu đề cửa sổ nhân vật, để nhận ra khi người dùng đang bấm vào nó
MOCK = "--mock" in sys.argv
