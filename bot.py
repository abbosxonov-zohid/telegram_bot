import telebot
from telebot import types
import yt_dlp
import os
import time
import threading

# Bot tokenini shu yerga yoz
TOKEN = "8256870616:AAF4O9gV_zMpIiiDgovnx0ijU0k97upokz8"
bot = telebot.TeleBot(TOKEN)

# Kesh (url -> file_path)
cache = {}
CACHE_DIR = "cache"
CACHE_TTL = 60 * 60 * 24 * 30   # 30 kun

os.makedirs(CACHE_DIR, exist_ok=True)

# 🔹 Keshni tozalash funksiyasi
def clear_cache():
    while True:
        now = time.time()
        for file in os.listdir(CACHE_DIR):
            path = os.path.join(CACHE_DIR, file)
            if os.path.isfile(path):
                if now - os.path.getmtime(path) > CACHE_TTL:
                    try:
                        os.remove(path)
                        print(f"🧹 Kesh tozalandi: {path}")
                    except Exception:
                        pass
        time.sleep(3600)  # har soatda tekshiradi

# Fon jarayonda kesh tozalashni ishga tushiramiz
threading.Thread(target=clear_cache, daemon=True).start()


# Start buyrug'i
@bot.message_handler(commands=['start'])
def start_handler(message):
    bot.reply_to(
        message,
        "👋 Salom!\n"
        "Menga YouTube, TikTok yoki Instagram link yuboring.\n"
        "Men sizga videoni 720p sifatida yuklab beraman.\n"
        "🎵 Agar xohlasangiz, audiosini ham olishingiz mumkin."
    )


def download_media(url, audio=False):
    if audio:
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": f"{CACHE_DIR}/%(id)s.%(ext)s",
            "quiet": True,
            "noplaylist": True,
            "postprocessors": [
                {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}
            ],
            "concurrent_fragment_downloads": 4,
            "http_chunk_size": 1048576
        }
    else:
        ydl_opts = {
            "format": "best[height<=720]",
            "outtmpl": f"{CACHE_DIR}/%(id)s.%(ext)s",
            "quiet": True,
            "noplaylist": True,
            "concurrent_fragment_downloads": 4,
            "http_chunk_size": 1048576
        }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file_path = ydl.prepare_filename(info)
        if audio:
            file_path = os.path.splitext(file_path)[0] + ".mp3"
        return file_path, info.get("title", "media")


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    url = message.text.strip()

    if any(x in url for x in ["youtube.com", "youtu.be", "tiktok.com", "instagram.com"]):
        try:
            if url in cache and os.path.exists(cache[url]["video"]):
                with open(cache[url]["video"], "rb") as f:
                    bot.send_video(message.chat.id, f, caption=cache[url]["title"])
            else:
                status_msg = bot.reply_to(message, "⏳ Yuklab olyapman, biroz kuting...")

                file_path, title = download_media(url, audio=False)

                file_size = os.path.getsize(file_path)
                if file_size > 50 * 1024 * 1024:
                    bot.send_message(message.chat.id, "⚠️ Fayl hajmi 50MB dan katta, yuborib bo‘lmaydi.")
                else:
                    with open(file_path, "rb") as f:
                        bot.send_video(message.chat.id, f, caption=title)

                cache[url] = {"video": file_path, "title": title}

                bot.delete_message(message.chat.id, status_msg.message_id)

            markup = types.InlineKeyboardMarkup()
            btn = types.InlineKeyboardButton("🎵 Audioni yuklab ber", callback_data=f"audio|{url}")
            markup.add(btn)
            bot.send_message(message.chat.id, "👉 Audioni ham xohlaysizmi?", reply_markup=markup)

        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Xato yuz berdi: {str(e)}")
    else:
        bot.reply_to(message, "⚠️ Faqat YouTube, TikTok yoki Instagram link yuboring.")


@bot.callback_query_handler(func=lambda call: call.data.startswith("audio|"))
def handle_audio(call):
    url = call.data.split("|")[1]
    try:
        if url in cache and "audio" in cache[url] and os.path.exists(cache[url]["audio"]):
            with open(cache[url]["audio"], "rb") as f:
                bot.send_audio(call.message.chat.id, f, caption=cache[url]["title"])
        else:
            status_msg = bot.send_message(call.message.chat.id, "🎵 Audioni yuklab olyapman...")

            file_path, title = download_media(url, audio=True)

            file_size = os.path.getsize(file_path)
            if file_size > 50 * 1024 * 1024:
                bot.send_message(call.message.chat.id, "⚠️ Audio hajmi 50MB dan katta, yuborib bo‘lmaydi.")
            else:
                with open(file_path, "rb") as f:
                    bot.send_audio(call.message.chat.id, f, caption=title)

            cache.setdefault(url, {"title": title})
            cache[url]["audio"] = file_path

            bot.delete_message(call.message.chat.id, status_msg.message_id)

    except Exception as e:
        bot.send_message(call.message.chat.id, f"❌ Audio yuklashda xato: {str(e)}")


if __name__ == "__main__":
    print("✅ Bot ishga tushdi...")
    bot.infinity_polling()
