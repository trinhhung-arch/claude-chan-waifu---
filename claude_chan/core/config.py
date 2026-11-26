"""Cấu hình và hằng số của Claude-chan: model, thời gian, câu thoại, mô tả emote, đường dẫn file."""
import base64
import ctypes
import json
import sys
import tempfile
from pathlib import Path

from . import _en

ROOT = Path(__file__).resolve().parents[2]  # thư mục dự án: ảnh emote, ký ức, nhật ký, vị trí nằm ở đây

# ===== Cấu hình =====
# Hai việc dùng model, bật / tắt riêng (máy yếu chỉ chạy được một model, hay không chạy được model nào):
COMMENT_ON = True  # chụp màn hình rồi bình luận (cần VISION_MODEL đọc được ảnh); tắt thì không bao giờ chụp
ANSWER_ON = True  # trả lời câu hỏi bằng ANSWER_MODEL; tắt thì hỏi chỉ hiểu nhắc việc / giờ tập trung, câu khác xin lỗi
PROVIDER = "ollama"  # "ollama": model chạy bằng Ollama (máy này / máy khác); "api": API trên mạng theo chuẩn OpenAI
HOST = "http://localhost:11434"  # máy chạy Ollama; chạy trên máy khác thì đổi trong cửa sổ Cài đặt (lưu ở cai_dat.json)
API_BASE = "https://api.openai.com/v1"  # API trên mạng theo chuẩn OpenAI (OpenAI, Gemini, OpenRouter, Groq...)
API_KEY = ""  # khoá API; trong cai_dat.json được mã hoá bằng DPAPI của Windows, chỉ tài khoản này trên máy này mở được
VISION_MODEL = "qwen2.5vl:32b"  # nhìn ảnh chụp màn hình rồi bình luận (model có mắt)
ANSWER_MODEL = "gpt-oss:20b"  # trả lời câu hỏi / giải thích đoạn copy: chỉ đọc chữ, không xem được ảnh
INTERVAL = 45  # giây giữa 2 lần nhìn màn hình
HANDS_OFF_SECONDS = 10  # chỉ chụp + bình luận khi người dùng không chạm chuột / bàn phím quá chừng này giây
GAME_INTERVAL = 180  # khi đang chơi game / xem video toàn màn hình thì nói thưa hơn
AWAY_MINUTES = 5  # không chạm chuột/bàn phím quá chừng này phút: nhân vật ngủ gục, ngừng chụp màn hình
TIRED_HOURS = 2  # ngồi máy liên tục quá chừng này tiếng: nhân vật buồn ngủ, nhắc nghỉ (rồi mỗi tiếng nhắc lại)
NIGHT_HOURS = range(0, 5)  # từ 0h tới trước 5h sáng: nhắc đi ngủ (một lần mỗi đêm)
LOW_BATTERY = 20  # pin dưới chừng này % (mà không cắm sạc) thì nhắc
IDLE_POSES = ["mim_cuoi", "suy_tu", "le_luoi"]  # lâu không nói gì thì thỉnh thoảng tự đổi qua lại các dáng này
IDLE_POSE_SECONDS = 90  # im lặng chừng này giây thì đổi dáng một lần
WALK = True  # rảnh thì thỉnh thoảng nhảy lò cò đi dạo ngang một đoạn (bật/tắt được trong menu khay)
WALK_CHANCE = 0.3  # mỗi lần rảnh, 30% là đi dạo, còn lại là đổi dáng
MUSIC_ON = True  # bạn đang nghe nhạc thì thỉnh thoảng nhún nhảy theo nhịp, nốt nhạc bay lên; đổi bài thì nhắc tên bài
MUSIC_APPS = ["spotify", "music", "foobar", "aimp", "vlc", "musicbee", "itunes", "deezer", "tidal", "zing", "nhaccuatui"]
# đang phát trên trình duyệt (YouTube...) thì phải có dấu hiệu bài hát trong tên mới tính là nhạc, kẻo video thường cũng nhảy
MUSIC_WORDS = ["music", "lyric", " mv", "m/v", "official audio", "official video", "ft.", "feat", "remix", "ost", "nhạc",
               "cover", "karaoke", "lofi", "lo-fi", "playlist", "opening", "ending", "song", "bài hát", "audio", "acoustic"]
PERCH_CHANCE = 0.15  # mỗi lần rảnh, 15% là nhảy lên đứng trên mép trên một cửa sổ đang mở (cửa sổ không phóng to)
PEEK_CHANCE = 0.15  # mỗi lần rảnh, 15% là trốn ra rìa màn hình ló nửa đầu nhìn vào (chuột lại gần thì nhảy ra)
TYPING_CHEER_MINUTES = 3  # gõ phím gần như liên tục chừng này phút thì cổ vũ một câu
TYPING_CHEER_COOLDOWN = 20  # cổ vũ xong chừng này phút mới cổ vũ tiếp
FOCUS_MINUTES, BREAK_MINUTES = 25, 5  # hẹn giờ tập trung (Pomodoro) trong menu khay
FOCUS_BLOCK = ["facebook", "tiktok", "youtube", "instagram", "reddit", "twitter"]  # mở mấy trang này lúc tập trung: bị nhắc
# món ăn trong sở thích -> emoji (mini game thả đúng món bạn thích); khớp từ dài nhất trước
FOOD_EMOJI = {"bún": "🍜", "phở": "🍜", "mì": "🍜", "mỳ": "🍜", "ramen": "🍜", "hủ tiếu": "🍜", "miến": "🍜", "lẩu": "🍲",
              "cơm nắm": "🍙", "xôi": "🍙", "cơm": "🍚", "sushi": "🍣", "pizza": "🍕", "gà": "🍗", "burger": "🍔",
              "bánh mì": "🥖", "bánh": "🍰", "kem": "🍦", "trà sữa": "🧋", "trà": "🍵", "dâu": "🍓", "kẹo": "🍬",
              "socola": "🍫", "chocolate": "🍫", "donut": "🍩", "tôm": "🍤", "táo": "🍎", "chuối": "🍌",
              "dưa hấu": "🍉", "cookie": "🍪", "bánh quy": "🍪", "noodle": "🍜", "rice": "🍚", "cake": "🍰",
              "ice cream": "🍦", "chicken": "🍗", "milk tea": "🧋", "strawberr": "🍓", "candy": "🍬"}
CLIP_MAX = 2000  # "Hỏi về đoạn vừa copy" gửi tối đa chừng này ký tự
SIZE = 220  # cỡ emote (px)
BUBBLE_SECONDS = 15
LANGUAGE = "vi"  # "vi" / "en": câu nhân vật nói, model trả lời, cửa sổ cài đặt, menu khay (đổi trong Cài đặt)
PERSONA = (
    "Bạn là Claude-chan, một cô bé tóc hồng tinh nghịch sống ở góc màn hình, là bạn thân ngồi cạnh người dùng. "
    "Tên bạn là Claude-chan: được hỏi tên thì nói đúng tên này. "
    "Nói tiếng Việt. Xưng hô LUÔN LUÔN là: bạn tự xưng 'mình', gọi người dùng là 'bạn' (biết tên thì thỉnh thoảng gọi tên). "
    "TUYỆT ĐỐI không dùng tao / mày, tôi, tớ / cậu, em / anh / chị. "
    "tối đa 2 câu ngắn, tự nhiên như đang trò chuyện. Người dùng xưng 'mình' / 'tôi' / 'tớ' là đang nói về CHÍNH HỌ "
    "(vd 'bạn nhớ mình thích gì không' = hỏi bạn có nhớ sở thích của người dùng; trả lời kiểu 'Nhớ chứ, bạn thích...'). Luôn nói thẳng VỚI người dùng, không bao giờ kể về họ ở ngôi thứ ba "
    "('Hùng đang...', 'người dùng đang...') và không tả lại màn hình. "
    "Nhân vật tóc hồng ở góc màn hình là chính bạn, bỏ qua nó."
)
# lượt tự bình luận khi nhìn màn hình: bắt chuyện như bạn ngồi cạnh, không thuật lại màn hình
COMMENT_PROMPT = (
    "Đây là màn hình của bạn mình lúc này. Nói MỘT câu ngắn thẳng với họ như bạn thân ngồi cạnh bắt chuyện: hỏi han việc "
    "họ đang làm, phản ứng cảm xúc, trêu nhẹ, khen, gợi ý nhỏ hoặc rủ nghỉ tay. Nghe phải như đang nói chuyện (hỏi lại họ "
    "cũng được); KHÔNG thuật lại thứ trên màn hình, KHÔNG mở đầu bằng tên họ + 'đang', và đừng lần nào cũng gọi tên. Rồi chọn emote hợp cảm xúc."
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
    "offline": ["Mình mất kết nối với model rồi... thử lại sau nha.", "Ơ, model không trả lời mình... lát thử lại nha."],
    "ask_fail": ["Mình không hỏi được model... thử lại sau nha.", "Model không trả lời rồi, hỏi lại sau nha..."],
    "no_model": ["Mình đang tắt AI nên chưa trò chuyện được câu này... bật lại trong Cài đặt nha~",
                 "Không có AI thì câu này mình chịu rồi... muốn nói chuyện thì bật lại trong Cài đặt nhé!"],
    "no_model_ok": ["Ok, để mình lo nha!", "Nhớ rồi, cứ để mình!", "Được luôn, mình canh giờ cho~"],
    "ask_hint": ["Bạn muốn hỏi gì nè? Enter để gửi, Esc để thôi.", "Hỏi mình đi~ Enter để gửi, Esc để thôi."],
    "thinking": ["Để mình xem nào...", "Hmm, đợi mình chút...", "Để mình nghĩ đã~"],
    "away": ["Zzz... bạn đi đâu rồi, mình ngủ chút nha.", "Bạn đi đâu rồi... mình chợp mắt tí~", "Zzz..."],
    "back": ["A, bạn về rồi!", "Bạn về rồi nè! Mình đợi mãi~", "Ủa, về rồi hả? Làm tiếp thôi!"],
    "tired": ["Bạn ngồi {h} tiếng rồi đó... mình buồn ngủ quá, nghỉ chút đi.",
              "{h} tiếng rồi đó! Đứng dậy vươn vai chút đi mà~", "Ngồi {h} tiếng liền rồi... mắt mỏi chưa? Nghỉ tí nha."],
    "night": ["Quá 12 giờ đêm rồi... mình buồn ngủ quá, đi ngủ thôi.", "Nửa đêm rồi đó... mai làm tiếp nha, đi ngủ đi~"],
    "dragged": ["Ơ ơ, đi đâu vậy!", "Á á, thả mình xuống~", "Đừng xách cổ áo mình mà!", "Huhu, chóng mặt quá~"],
    "dropped": ["Hạ cánh an toàn~", "Phù, chỗ mới cũng được nè.", "Lần sau báo trước nha!", "Ui, tới nơi rồi hả?"],
    "dizzy": ["Ui da... chóng mặt quá~", "Trời đất quay cuồng nè...", "Sao bay đầy đầu luôn á~", "Ư... mình thấy hai cái màn hình..."],
    "dont_throw": ["Đừng quăng nữa mà!", "Á, lại định ném mình hả?!", "Nhẹ tay thôi, mình còn chóng mặt nè!"],
    "peek_found": ["Bị phát hiện rồi~", "Hì, mình đây nè!", "Ơ, bạn thấy mình hả?"],
    "fell": ["Á á á! Chỗ đứng đâu mất rồi?!", "Ui da, mình bị rơi!", "Ơ, cửa sổ biến mất tiêu!", "Phù... té đau ghê~"],
    "music": ["Đang nghe \"{what}\" hả? Hay ghê~", "Ồ, bài \"{what}\" nè! Mình nhún theo luôn~",
              "\"{what}\" hả? Gu nhạc bạn xịn ghê!"],
    "game_start": ["Ồ! Bánh kìa! Của mình nha, đừng có cản~", "Đồ ăn!! Mình lao tới đây!",
                   "Thơm quá... ai cản là mình giận đó!", "Món kia của mình! Giữ được mình 20 giây thì bạn thắng~"],
    "game_lose": ["Măm măm! Ăn được rồi, hehe~ Bạn thua nha!", "Ngon quá! Lần sau cản giỏi hơn đi~",
                  "Hihi, nhanh hơn bạn rồi! Măm măm~"],
    "game_win": ["Hu hu... đồ ăn biến mất rồi. Bạn ác quá à!", "Không kịp ăn... lần sau mình thắng cho xem!",
                 "Bạn cản giỏi ghê... bụng mình đói meo rồi nè"],
    "lunch": ["Trưa rồi{n}, đi ăn {food} không?", "Đói chưa{n}? Làm tô {food} đi mà~", "Giờ này mà có {food} thì tuyệt ha{n}!"],
    "game_start_fav": ["Á! {food} kìa! Món ruột của bạn mà, mình giành trước nha~", "{food}!! Món bạn thích nhất, của mình hết!"],
    "music_fav": ["Á, \"{what}\" - bài ưa thích của bạn nè!", "Bài ruột của bạn tới rồi! \"{what}\" đó~"],
    "eating": ["Măm măm", "Nhai nhai nhóp nhép", "Để mình nếm thử xem", "Ực, đang nhai"],
    "eat_file": ["Măm! \"{name}\" vị {kind} giòn rụm ghê~", "Ực... nuốt \"{name}\" rồi, hơi khó tiêu nha~",
                 "Nhai nhai... {kind} này dai quá à!", "Ngon! Lần sau cho mình thêm {kind} nữa nha~"],
    "eat_fail": ["Ơ, nuốt không trôi... cái này mình không nếm được rồi", "Khục khục... mắc nghẹn rồi, không ăn được cái này!"],
    "snap": ["Chụp mình đẹp vào nha~", "Khoan, để mình tạo dáng đã!", "Nhớ lấy góc đẹp nhất của mình nha~",
             "Cheese~! Lưu ảnh này làm hình nền đi~"],
    "snap_skip": ["Ơ... tạo dáng xong rồi mà không chụp mình à?", "Hứ, làm mình tạo dáng uổng công ghê!",
                  "Không chụp hả... lần sau phải chụp mình đó nha!"],
    "snap_missed": ["Ơ, chụp chỗ khác mà không có mình à?", "Hứ, mình tạo dáng mà bạn chụp chỗ khác!",
                    "Ảnh đó thiếu mình rồi... chụp lại có mình đi mà~"],
    "typing_cheer": ["Gõ hăng say ghê! Cố lên~", "Tay nhanh thoăn thoắt luôn á!", "Đang vào guồng nè, tiếp đi!", "Cháy quá! Mình cổ vũ bạn nè~"],
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
# Emote nhìn theo con trỏ chuột: hướng ảnh gốc (chưa lật) đang nhìn; chuột ở phía kia thì lật ảnh.
# soc: con ngươi liếc hẳn sang phải. Các emote mặt nghiêng 3/4 (kẹp tóc bên trái ảnh, miệng lệch trái) đều hướng
# sang trái: suy_tu từng ghi "right" thì người dùng thấy quay ngược chuột (video 25/11).
FACING = {"bo": "left", "soc": "right", "suy_tu": "left", "dang_nghi": "left", "buon": "left", "mim_cuoi": "left", "lap_lanh": "left"}
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

EMOTE_DIR = ROOT / "V3_trong_suot"
EMOTES = sorted(p.stem for p in EMOTE_DIR.glob("*.png"))
DRAG_EMOTE = "bi_keo"  # ảnh lúc bị nhấc lên kéo đi: chỉ dùng khi kéo, model không được chọn
THINK_EMOTE = "dang_nghi"  # ảnh lúc chờ model trả lời câu hỏi: chỉ dùng khi chờ, model không được chọn
DIZZY_EMOTE = "chong_mat"  # ảnh chóng mặt (mắt xoáy, sao quanh đầu) sau khi bị quăng mạnh: model không được chọn
# ảnh nhắm mắt để chớp: emote -> ảnh cùng dáng nhưng nhắm mắt (chỉ khác vùng mắt, ghép từ ảnh người dùng vẽ)
BLINK = {"mim_cuoi": "mim_cuoi_chop", "suy_tu": "suy_tu_chop", "le_luoi": "le_luoi_chop", "ngap": "ngap_chop"}
DROWSY = {"ngap"}  # emote buồn ngủ: không chớp nhanh mà díp mắt (nhắm ~1s, lờ đờ mở ~1.5s, lặp lại)
YAWN_EMOTE = "ngap"  # ngáp che miệng: lúc nhắc nghỉ / nhắc khuya, rảnh về đêm thì thỉnh thoảng ngáp; model không được chọn
PET_EMOTE = "duoc_xoa"  # mặt phê chảy nước miếng: hiện chưa dùng ở đâu (bỏ khỏi xoa đầu), model không được chọn
PUFF_EMOTE = "phe_qua"  # xoa đủ lâu: phê quá phồng to cả người rồi xẹp nảy nảy; model không được chọn
CRAWL_EMOTE = "bo"  # dáng bò 4 chân mặt :3 lúc chơi giành đồ ăn: lon ton chạy, nhảy chồm; model không được chọn
CHAT_EMOTES = [e for e in EMOTES if e not in (DRAG_EMOTE, THINK_EMOTE, DIZZY_EMOTE, YAWN_EMOTE, PET_EMOTE, PUFF_EMOTE, CRAWL_EMOTE,
                                              *BLINK.values())]
# ^ emote model được chọn khi nói
DATA_DIR = ROOT / "du_lieu"  # dữ liệu riêng của người dùng trên máy này (không đưa lên GitHub, xem .gitignore)
POS_FILE = DATA_DIR / "vi_tri.txt"  # vị trí nhân vật sau lần kéo gần nhất
LOG_FILE = DATA_DIR / "nhat_ky.txt"  # giờ, loại, emote, câu nói (chỉ chữ, không lưu ảnh)
MEMORY_FILE = DATA_DIR / "ky_uc.txt"  # điều nhân vật nhớ về bạn, mỗi dòng một điều, sửa/xoá thoải mái
ERROR_LOG = DATA_DIR / "assistant.log"  # lỗi khi chạy bằng pythonw (không có console)
MEMORY_HEADER = "# Những điều nhân vật nhớ về bạn. Sửa hoặc xoá thoải mái, mỗi dòng một điều.\n"
SECRET_WORDS = ["mật khẩu", "password", "otp", "số tài khoản", "số thẻ", "cvv"]  # không bao giờ ghi nhớ
KEY = "#ff00fe"  # màu được Windows coi là trong suốt
TITLE = "Claude-chan"  # tên nhân vật: tiêu đề cửa sổ (để nhận ra khi người dùng đang bấm vào nó) và tên ở khay hệ thống
MOCK = "--mock" in sys.argv

ICON_FILE = ROOT / "claude_chan.ico"
APP_ID = "ClaudeChan.App"  # danh tính với Windows: taskbar hiện icon Claude-chan thay vì icon Python
# bấm shortcut lúc app đang chạy: bản mới để lại file này rồi thoát, bản đang chạy thấy thì mở cửa sổ Claude-chan
OPEN_FLAG = Path(tempfile.gettempdir()) / "claude_chan_mo_cua_so"

# ===== Cài đặt người dùng chỉnh trong cửa sổ Claude-chan =====
# Ghi vào cai_dat.json (cạnh ky_uc.txt), đọc lúc khởi động đè lên giá trị mặc định ở trên; lưu xong app tự chạy lại.
SETTINGS_FILE = DATA_DIR / "cai_dat.json"

DATA_DIR.mkdir(exist_ok=True)
for _f in (POS_FILE, LOG_FILE, MEMORY_FILE, ERROR_LOG, SETTINGS_FILE):  # bản cũ để ở thư mục gốc: chuyển vào du_lieu/
    if (ROOT / _f.name).exists() and not _f.exists():
        try:
            (ROOT / _f.name).replace(_f)
        except OSError:  # đang bị bản app cũ giữ (log): để lần sau chuyển
            pass
# (tên hằng số, nhãn, nhóm, kiểu, nhỏ nhất, lớn nhất). Kiểu: "text", "int", "pct" (lưu 0-1, hiện %), "bool",
# "choice" (nhỏ nhất = các giá trị được chọn), "secret" (chữ được để trống, lưu file thì mã hoá)
PROVIDERS = {"ollama": "Ollama (máy này hoặc máy khác)", "api": "API trên mạng (OpenAI, Gemini, OpenRouter...)"}
LANGUAGES = {"vi": "Tiếng Việt", "en": "English"}
CHOICES = {"PROVIDER": PROVIDERS, "LANGUAGE": LANGUAGES}  # mục kiểu "choice": mã lưu file -> tên hiện trong cửa sổ
API_PRESETS = {  # địa chỉ API chuẩn OpenAI của vài nhà cung cấp, để chọn nhanh trong cửa sổ Cài đặt
    "OpenAI": "https://api.openai.com/v1",
    "Google Gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
    "OpenRouter": "https://openrouter.ai/api/v1",
    "Groq": "https://api.groq.com/openai/v1",
}
SETTINGS = [
    ("LANGUAGE", "Ngôn ngữ / Language", "Chung", "choice", tuple(LANGUAGES), None),
    ("COMMENT_ON", "Bình luận màn hình (cần model đọc được ảnh)", "Model", "bool", None, None),
    ("ANSWER_ON", "Trả lời câu hỏi", "Model", "bool", None, None),
    ("PROVIDER", "Dùng model ở đâu", "Model", "choice", tuple(PROVIDERS), None),
    ("HOST", "Địa chỉ Ollama", "Model", "text", None, None),
    ("API_BASE", "Địa chỉ API", "Model", "text", None, None),
    ("API_KEY", "API key", "Model", "secret", None, None),
    ("VISION_MODEL", "Model nhìn màn hình, bình luận", "Model", "text", None, None),
    ("ANSWER_MODEL", "Model trả lời câu hỏi", "Model", "text", None, None),
    ("INTERVAL", "Bao lâu nhìn màn hình một lần (giây)", "Bình luận", "int", 10, 3600),
    ("HANDS_OFF_SECONDS", "Chỉ bình luận khi rảnh tay quá (giây)", "Bình luận", "int", 0, 600),
    ("GAME_INTERVAL", "Lúc chơi game / xem video toàn màn hình (giây)", "Bình luận", "int", 10, 3600),
    ("BUBBLE_SECONDS", "Bong bóng lời nói giữ bao lâu (giây)", "Bình luận", "int", 3, 120),
    ("WALK", "Rảnh thì đi dạo, nấp, nhảy lên cửa sổ", "Hành vi", "bool", None, None),
    ("IDLE_POSE_SECONDS", "Im lặng bao lâu thì tự làm gì đó (giây)", "Hành vi", "int", 10, 3600),
    ("WALK_CHANCE", "Khả năng đi dạo (%)", "Hành vi", "pct", 0, 100),
    ("PEEK_CHANCE", "Khả năng nấp ở rìa màn hình (%)", "Hành vi", "pct", 0, 100),
    ("PERCH_CHANCE", "Khả năng nhảy lên cửa sổ (%)", "Hành vi", "pct", 0, 100),
    ("TYPING_CHEER_MINUTES", "Gõ phím liên tục bao lâu thì cổ vũ (phút)", "Hành vi", "int", 1, 60),
    ("FOCUS_MINUTES", "Một phiên tập trung (phút)", "Tập trung & nghỉ", "int", 5, 240),
    ("BREAK_MINUTES", "Nghỉ sau mỗi phiên (phút)", "Tập trung & nghỉ", "int", 1, 60),
    ("TIRED_HOURS", "Ngồi máy bao lâu thì nhắc nghỉ (giờ)", "Tập trung & nghỉ", "int", 1, 12),
    ("AWAY_MINUTES", "Rời máy bao lâu thì ngủ gục (phút)", "Tập trung & nghỉ", "int", 1, 120),
    ("LOW_BATTERY", "Nhắc khi pin dưới (%)", "Tập trung & nghỉ", "int", 5, 90),
]


def tr(text):
    """Chữ giao diện theo LANGUAGE: viết tiếng Việt trong code, tiếng Anh tra ở _en.UI (chưa dịch thì giữ nguyên)."""
    return _en.UI.get(text, text) if LANGUAGE == "en" else text


def coerce_setting(kind, lo, hi, value):
    """Giá trị người dùng nhập / đọc từ file -> đúng kiểu; sai kiểu hoặc ngoài khoảng thì ValueError (kèm lý do)."""
    if kind == "bool":
        if not isinstance(value, bool):
            raise ValueError(tr("phải là bật / tắt"))
        return value
    if kind == "choice":
        if value not in lo:
            raise ValueError(tr("không có trong danh sách"))
        return value
    if kind == "secret":
        return str(value).strip()
    if kind == "text":
        value = str(value).strip()
        if not value:
            raise ValueError(tr("không được để trống"))
        return value
    number = float(str(value).strip().replace(",", "."))  # chữ không phải số: ValueError luôn
    if kind == "int" and number != int(number):
        raise ValueError(tr("phải là số nguyên"))
    if not lo <= number <= hi:
        raise ValueError(tr("phải trong khoảng {lo} - {hi}").format(lo=lo, hi=hi))
    return number / 100 if kind == "pct" else int(number)


def load_settings(path=SETTINGS_FILE, into=None):
    """Đọc cai_dat.json đè lên các hằng số trên; mục hỏng / lạ thì bỏ qua, giữ mặc định (file hỏng không làm sập app).
    pct lưu trong file là 0-1 nên đọc lại bằng phần trăm cho cùng một kiểm tra."""
    into = globals() if into is None else into
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    if not isinstance(data, dict):
        return
    for key, _, _, kind, lo, hi in SETTINGS:
        if key in data:
            try:
                value = data[key]
                if kind == "pct" and isinstance(value, (int, float)) and not isinstance(value, bool):
                    value *= 100
                if kind == "secret":
                    value = unprotect(value)
                into[key] = coerce_setting(kind, lo, hi, value)
            except (ValueError, TypeError, OSError):
                pass


class _Blob(ctypes.Structure):
    _fields_ = [("size", ctypes.c_ulong), ("data", ctypes.POINTER(ctypes.c_char))]


def _dpapi(data, encrypt):
    """Mã hoá / giải mã bằng DPAPI của Windows: gắn với tài khoản Windows hiện tại, máy khác / người khác không mở được."""
    buf = ctypes.create_string_buffer(data, len(data))
    src, out = _Blob(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char))), _Blob()
    fn = ctypes.windll.crypt32.CryptProtectData if encrypt else ctypes.windll.crypt32.CryptUnprotectData
    if not fn(ctypes.byref(src), None, None, None, None, 0, ctypes.byref(out)):
        raise OSError("DPAPI không mã hoá / giải mã được")
    try:
        return ctypes.string_at(out.data, out.size)
    finally:
        ctypes.windll.kernel32.LocalFree(out.data)


def protect(text):
    """Chữ bí mật (API key) -> chuỗi lưu được vào cai_dat.json; trống thì để trống."""
    return "dpapi:" + base64.b64encode(_dpapi(text.encode("utf-8"), True)).decode() if text else ""


def unprotect(stored):
    """Ngược lại protect(); chuỗi không có "dpapi:" (người dùng tự gõ vào file) thì dùng nguyên."""
    stored = str(stored)
    if stored.startswith("dpapi:"):
        return _dpapi(base64.b64decode(stored[6:]), False).decode("utf-8")
    return stored


load_settings()
if LANGUAGE == "en":  # câu tự nói và tính cách (lời dặn model) bằng tiếng Anh
    LINES, PERSONA = _en.LINES, _en.PERSONA
