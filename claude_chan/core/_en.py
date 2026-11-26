"""Bản tiếng Anh (LANGUAGE = "en"): câu nhân vật tự nói, tính cách gửi model, và chữ giao diện (tra theo câu tiếng Việt)."""

PERSONA = (
    "You are Claude-chan, a playful pink-haired girl sitting in the corner of the screen, watching the user work on their "
    "computer. Your name is Claude-chan: when asked your name, say exactly this name. "
    "ALWAYS speak English, at most 2 short sentences, friendly and casual. "
    "Comment specifically on what you see on the screen: cheer them on, tease lightly, remind them to rest, or give a "
    "small tip. The pink-haired character in the bottom-right corner of the screen is you, ignore it."
)

# {n} = " Name" (or empty), {h} = hours, {p} = battery %, {m}/{b} = focus/break minutes, {what} = thing to remind
LINES = {
    "morning": ["Good morning{n}! What are we doing today?", "Morning{n}! Had some water yet?",
                "Good morning{n}~ Let's do our best today!"],
    "noon": ["It's noon{n}, have you eaten?", "Midday already{n}, take a lunch break~", "Noon{n}! Hungry yet?"],
    "afternoon": ["Good afternoon{n}! Keep it up.", "Afternoon{n}~ Drink some water.", "Have a nice afternoon{n}!"],
    "evening": ["It's evening{n}, still working?", "Good evening{n}~ Had dinner yet?", "Evening{n}, finish up and rest soon."],
    "late": ["It's late{n}... don't stay up too long.", "Still awake{n}? Go to bed early~", "So late{n}... I'm sleepy."],
    "monday": ["It's Monday{n}! Let's start the week strong!", "New week{n}~ What's the plan?"],
    "friday": ["It's Friday{n}! Weekend's almost here~", "Friday{n}! Just one more day!"],
    "birthday": ["Happy birthday{n}!!! Have the best day ever!", "Happy birthday{n}! Wishing you all the best~"],
    "tet": ["Happy Lunar New Year{n}! Wishing you luck and joy~", "Happy Tết{n}! Lots of luck this year!"],
    "trung_thu": ["Happy Mid-Autumn Festival{n}! Had a mooncake yet?", "Full moon festival{n}~ The moon must be pretty tonight!"],
    "pause": ["Eyes covered! Click me again when you want me to look.", "Not looking, not looking! Click me when you need me.",
              "Okay, closing my eyes~"],
    "resume": ["Watching again!", "Eyes open!", "Let me see what you're doing~"],
    "private": ["This looks private, I won't look.", "Oh, private stuff, I'll look away~", "Covering my eyes here, don't worry!"],
    "offline": ["I lost connection to the model... try again later.", "The model isn't answering me... let's try again later."],
    "ask_fail": ["I couldn't reach the model... try again later.", "The model didn't answer, ask me again later..."],
    "no_model": ["AI is off, so I can't chat about that... turn it on in Settings~",
                 "Without AI I can't answer that... turn it back on in Settings if you want to talk!"],
    "no_model_ok": ["Okay, leave it to me!", "Got it, I'll handle it!", "Sure, I'll keep track of the time~"],
    "ask_hint": ["What do you want to ask? Enter to send, Esc to cancel.", "Ask me anything~ Enter to send, Esc to cancel."],
    "thinking": ["Let me see...", "Hmm, give me a sec...", "Let me think~"],
    "away": ["Zzz... where did you go? I'll nap a bit.", "You're gone... time for a little nap~", "Zzz..."],
    "back": ["Ah, you're back!", "Welcome back! I waited forever~", "Oh, back already? Let's keep going!"],
    "tired": ["You've been sitting for {h} hours... I'm so sleepy, take a break.",
              "{h} hours already! Stand up and stretch~", "{h} hours straight... tired eyes? Rest a bit."],
    "night": ["It's past midnight... I'm so sleepy, let's go to bed.", "Midnight already... continue tomorrow, go sleep~"],
    "dragged": ["Hey hey, where are we going!", "Aah, put me down~", "Don't grab me by the collar!", "Waah, I'm dizzy~"],
    "dropped": ["Safe landing~", "Phew, this spot is nice too.", "Warn me next time!", "Oh, are we there?"],
    "dizzy": ["Ugh... so dizzy~", "The world is spinning...", "Stars all around my head~", "Ugh... I see two screens..."],
    "dont_throw": ["Stop throwing me!", "Ah, gonna throw me again?!", "Gently, I'm still dizzy!"],
    "peek_found": ["You found me~", "Hehe, here I am!", "Oh, you saw me?"],
    "fell": ["Aaah! Where did my floor go?!", "Ouch, I fell!", "Hey, the window vanished!", "Phew... that hurt~"],
    "music": ["Listening to \"{what}\"? Nice~", "Ooh, \"{what}\"! I'll dance along~", "\"{what}\"? You've got great taste!"],
    "game_start": ["Ooh! Cake! It's mine, don't stop me~", "Food!! Here I come!", "Smells so good... stop me and I'll be mad!",
                   "That's mine! Keep me away for 20 seconds and you win~"],
    "game_lose": ["Nom nom! Got it, hehe~ You lose!", "Yummy! Block me better next time~", "Hehe, I was faster! Nom nom~"],
    "game_win": ["Waah... the food is gone. You're so mean!", "Didn't make it... I'll win next time!",
                 "You're good at this... my tummy is rumbling"],
    "eating": ["Nom nom", "Munch munch", "Let me taste it", "Gulp, chewing"],
    "eat_file": ["Nom! \"{name}\" tastes like crunchy {kind}~", "Gulp... swallowed \"{name}\", a bit hard to digest~",
                 "Munch munch... this {kind} is so chewy!", "Yummy! Give me more {kind} next time~"],
    "eat_fail": ["Uh oh, can't swallow this... I couldn't taste it", "Cough cough... it got stuck, I can't eat this!"],
    "snap": ["Take a cute picture of me~", "Wait, let me pose!", "Get my best angle~", "Cheese~! Make this your wallpaper~"],
    "snap_skip": ["Huh... I posed and you didn't take the picture?", "Hmph, I posed for nothing!",
                  "No picture? Next time you'd better take one of me!"],
    "snap_missed": ["Huh, you took a picture somewhere else without me?", "Hmph, I posed and you shot something else!",
                    "That picture is missing me... take one with me in it~"],
    "typing_cheer": ["Typing like crazy! Go go~", "Your fingers are so fast!", "You're in the zone, keep going!",
                     "On fire! I'm cheering for you~"],
    "battery": ["Only {p}% battery left, plug in before it dies!", "Hey, battery's at {p}%! Charge it!"],
    "net_lost": ["Uh oh... the internet is gone.", "Where did the internet go..."],
    "net_back": ["Internet's back!", "We're online again!"],
    "focus_start": ["Starting {m} minutes of focus! You got this!", "{m} minutes of focus, I'll keep time!"],
    "focus_stop": ["Focus stopped.", "Okay, no more focus mode~"],
    "focus_nag": ["It's focus time! Close that and get back to work.", "Hey hey, scrolling during focus time?",
                  "Hmph, watch that after the timer!"],
    "focus_done": ["{m} minutes done, great job! Take a {b} minute break, stand up and stretch.",
                   "Focus time's over! Rest your eyes for {b} minutes~"],
    "break_done": ["Break's over, back to work!", "That's enough rest~ Let's continue!"],
    "reminder": ["It's time: {what}!", "Hey, remember to {what}!", "Time to {what}!"],
    "clip_empty": ["You haven't copied any text. Select it and press Ctrl+C first.", "Clipboard is empty~ Copy some text first."],
    "clip_read": ["Let me read what you copied...", "Let me look at this..."],
    "code": ["Coding time!", "Code's open, go go!", "Coding again? I'll watch~"],
    "game": ["Playing a game? Let me watch!", "What game is that? Win it!", "Yay, game time~"],
    "chat": ["Chatting with someone~", "Who's texting? Hehe~", "Gossip time?"],
}

# chữ giao diện: câu tiếng Việt -> tiếng Anh (câu có {..} được .format() sau khi dịch)
UI = {
    # nhóm / tab cài đặt
    "Chung": "General", "Model": "Model", "Bình luận": "Comments", "Hành vi": "Behavior",
    "Tập trung & nghỉ": "Focus & breaks", "Khởi động": "Startup",
    # nhãn cài đặt
    "Ngôn ngữ / Language": "Ngôn ngữ / Language",
    "Bình luận màn hình (cần model đọc được ảnh)": "Comment on the screen (needs a model that reads images)",
    "Trả lời câu hỏi": "Answer questions",
    "Dùng model ở đâu": "Where the model runs",
    "Địa chỉ Ollama": "Ollama address",
    "Địa chỉ API": "API address",
    "API key": "API key",
    "Model nhìn màn hình, bình luận": "Model for screen comments",
    "Model trả lời câu hỏi": "Model for answering questions",
    "Bao lâu nhìn màn hình một lần (giây)": "Look at the screen every (seconds)",
    "Chỉ bình luận khi rảnh tay quá (giây)": "Only comment after hands-off for (seconds)",
    "Lúc chơi game / xem video toàn màn hình (giây)": "While gaming / fullscreen video (seconds)",
    "Bong bóng lời nói giữ bao lâu (giây)": "Speech bubble stays for (seconds)",
    "Rảnh thì đi dạo, nấp, nhảy lên cửa sổ": "Walk around, hide, hop on windows when idle",
    "Im lặng bao lâu thì tự làm gì đó (giây)": "Do something on her own after silence of (seconds)",
    "Khả năng đi dạo (%)": "Chance to walk (%)",
    "Khả năng nấp ở rìa màn hình (%)": "Chance to hide at the screen edge (%)",
    "Khả năng nhảy lên cửa sổ (%)": "Chance to hop on a window (%)",
    "Gõ phím liên tục bao lâu thì cổ vũ (phút)": "Cheer after typing nonstop for (minutes)",
    "Một phiên tập trung (phút)": "One focus session (minutes)",
    "Nghỉ sau mỗi phiên (phút)": "Break after each session (minutes)",
    "Ngồi máy bao lâu thì nhắc nghỉ (giờ)": "Remind to rest after sitting for (hours)",
    "Rời máy bao lâu thì ngủ gục (phút)": "Fall asleep when you're away for (minutes)",
    "Nhắc khi pin dưới (%)": "Warn when battery is below (%)",
    "Ollama (máy này hoặc máy khác)": "Ollama (this computer or another one)",
    "API trên mạng (OpenAI, Gemini, OpenRouter...)": "Online API (OpenAI, Gemini, OpenRouter...)",
    # lỗi nhập cài đặt
    "phải là bật / tắt": "must be on / off", "không có trong danh sách": "not in the list",
    "không được để trống": "cannot be empty", "phải là số nguyên": "must be a whole number",
    "phải trong khoảng {lo} - {hi}": "must be between {lo} and {hi}", "không hợp lệ": "invalid",
    # cửa sổ cài đặt
    "Chỉnh mình theo ý bạn nè~ ✿": "Make me just the way you like~ ✿",
    "↻ Lấy danh sách model": "↻ Get model list",
    "↻ Đang lấy danh sách...": "↻ Getting the list...",
    "↻ Lấy danh sách model ({n} model)": "↻ Get model list ({n} models)",
    "↻ Chưa lấy được: {why}": "↻ Couldn't get it: {why}",
    "chưa có model nào": "no models yet",
    "cần dán API key trước": "paste the API key first",
    "API key sai hoặc hết hạn": "API key is wrong or expired",
    "sai địa chỉ API": "wrong API address",
    "nhà cung cấp báo lỗi {code}": "the provider returned error {code}",
    "không kết nối được, xem lại địa chỉ / mạng": "can't connect, check the address / network",
    "  Tự chạy Claude-chan khi bật máy": "  Start Claude-chan when the computer starts",
    "Cài đặt được lưu ở {file}, trong thư mục {folder}": "Settings are saved in {file}, in the {folder} folder",
    "Chưa lưu được nè:\n": "Couldn't save:\n",
    "Lưu cài đặt rồi, nhưng chưa đổi được chế độ tự chạy khi bật máy.":
        "Settings saved, but starting with the computer couldn't be changed.",
    "Đưa mọi cài đặt về mặc định rồi chạy lại Claude-chan?": "Reset all settings to default and restart Claude-chan?",
    "↺ Về mặc định": "↺ Reset to default", "Đóng": "Close", "♥ Lưu và chạy lại": "♥ Save and restart",
    "Cần cài Ollama (ollama.com) và tải model về trước, vd: ollama pull qwen2.5vl:7b\n"
    "Ollama chạy ngay trên máy này: để http://localhost:11434\n"
    "Chạy trên máy khác (máy bàn, Mac, server...): điền địa chỉ máy đó, vd: http://192.168.1.10:11434\n"
    "Model nhìn màn hình phải là loại đọc được ảnh (vd: qwen2.5vl, qwen3-vl, gemma3).":
        "Install Ollama (ollama.com) and download a model first, e.g.: ollama pull qwen2.5vl:7b\n"
        "Ollama on this computer: keep http://localhost:11434\n"
        "On another computer (desktop, Mac, server...): enter its address, e.g.: http://192.168.1.10:11434\n"
        "The screen model must be able to read images (e.g.: qwen2.5vl, qwen3-vl, gemma3).",
    "Chọn địa chỉ API của nhà cung cấp (OpenAI, Gemini, OpenRouter, Groq) hoặc dán địa chỉ khác theo chuẩn\n"
    "OpenAI, rồi dán API key lấy trên trang của họ. Key được mã hoá theo tài khoản Windows trước khi lưu.\n"
    "Model nhìn màn hình phải đọc được ảnh (vd: gpt-4o-mini, gemini-2.5-flash). Dùng API sẽ tốn phí theo\n"
    "mỗi lần gọi (mỗi lần bình luận màn hình là một lần gửi ảnh), xem bảng giá của nhà cung cấp.":
        "Pick a provider's API address (OpenAI, Gemini, OpenRouter, Groq) or paste another OpenAI-compatible\n"
        "address, then paste the API key from their site. The key is encrypted with your Windows account.\n"
        "The screen model must read images (e.g.: gpt-4o-mini, gemini-2.5-flash). APIs charge per call\n"
        "(every screen comment sends one image), check the provider's pricing.",
    "Đang tắt AI (hợp với máy yếu, không có máy chạy Ollama hay API): Claude-chan không chụp màn hình,\n"
    "không bình luận; vẫn đi dạo, nấp, chơi đùa, nhắc nghỉ, nhắc khuya, tập trung như thường.\n"
    "Hỏi thì vẫn hiểu nhờ nhắc việc (\"15 phút nữa nhắc mình uống nước\") và giờ tập trung\n"
    "(\"mình code 40 phút\"); câu hỏi khác cần bật \"Trả lời câu hỏi\".":
        "AI is off (good for weak computers, no Ollama or API): Claude-chan won't capture or comment on\n"
        "the screen; she still walks, hides, plays, reminds you to rest, and runs focus sessions.\n"
        "Asking still works for reminders (\"remind me to drink water in 15 minutes\") and focus sessions\n"
        "(\"I'll code for 40 minutes\"); other questions need \"Answer questions\" turned on.",
    "\nChỉ chạy được một model? Model đọc được ảnh trả lời câu hỏi được luôn: chọn cùng model cho hai ô.\n"
    "Model chỉ đọc chữ (vd gpt-oss) thì tắt \"Bình luận màn hình\", chỉ để trả lời câu hỏi.":
        "\nCan only run one model? A model that reads images can answer questions too: pick it for both.\n"
        "A text-only model (e.g. gpt-oss): turn off \"Comment on the screen\" and use it for answers only.",
    # menu khay, tập trung, câu nối thêm
    "Cài đặt...": "Settings...", "Hiện / ẩn nhân vật": "Show / hide character", "Hỏi nhân vật...": "Ask Claude-chan...",
    "Hỏi về đoạn vừa copy": "Ask about copied text", "Chơi: giành đồ ăn": "Play: food fight",
    "Tạm dừng nhìn màn hình": "Pause screen watching", "Cho đi dạo khi rảnh": "Walk around when idle",
    "Mở file ký ức": "Open memory file", "Về góc mặc định": "Back to default corner", "Thoát": "Quit",
    "Tập trung {m} phút": "Focus {m} minutes", "Dừng tập trung (còn {m} phút)": "Stop focus ({m} min left)",
    " (Bắt đầu tập trung {m} phút, xong lúc {t})": " (Focus {m} minutes, until {t})",
    " (Mình sẽ nhắc lúc {t})": " (I'll remind you at {t})",
    "việc bạn nhờ": "the thing you asked", "thư mục": "folder", "không đuôi": "no extension",
}
