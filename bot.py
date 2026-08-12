# -*- coding: utf-8 -*-
import os
import logging
import asyncio
import threading
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from groq import Groq

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", "0"))
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

groq_client = Groq(api_key=GROQ_API_KEY)

SERVICES_TEXT = (
    "📋 Хизматрасониҳои мо:\n\n"
    "1. Хизмат якум — тавсиф\n"
    "2. Хизмат дуюм — тавсиф\n"
    "3. Хизмат сеюм — тавсиф\n\n"
    "Барои фармоиш додан тугмаи «🛒 Фармоиш додан»-ро пахш кунед."
)

ABOUT_TEXT = (
    "🤖 Ман NovaHelper ҳастам!\n\n"
    "Боти ёрдамчие, ки ба шумо дар гирифтани маълумот "
    "ва фармоиш додан кӯмак мекунад. Инчунин метавонед бо ман озод сӯҳбат кунед ё суруд пурсед!"
)

CONTACT_TEXT = (
    "📞 Барои тамос:\n\n"
    "Telegram: @ваш_username\n"
    "Телефон: +992 XX XXX XXXX"
)

GREETING_WORDS = [
    "салом", "ассалом", "ассалому алейкум",
    "наѓз", "чихел", "чй хел", "субх бахайр",
]

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

MAIN_MENU = ReplyKeyboardMarkup(
    [
        [KeyboardButton("ℹ️ Дар бораи мо"), KeyboardButton("📋 Хизматрасониҳо")],
        [KeyboardButton("🛒 Фармоиш додан"), KeyboardButton("📞 Тамос")],
        [KeyboardButton("🎵 Мусиқӣ")],
    ],
    resize_keyboard=True,
)

waiting_for_order = set()
waiting_for_music = set()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"Салом, {user.first_name}! 👋\n\n"
        "Хуш омадед ба NovaHelper. Аз менюи поён интихоб кунед, "
        "ё танҳо бо ман сӯҳбат кунед:",
        reply_markup=MAIN_MENU,
    )


def is_greeting(text: str) -> bool:
    text_lower = text.lower().strip()
    return any(word in text_lower for word in GREETING_WORDS)


async def get_ai_reply(text: str) -> str:
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "Ту ёрдамчии дӯстонаи NovaHelper ҳастӣ. "
                    "Бо забони тоҷикӣ ҷавоб деҳ, кӯтоҳ, самимӣ ва мушаххас.",
                },
                {"role": "user", "content": text},
            ],
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Хатогии Groq: {e}")
        return "❌ Мутаассифона, ҳозир натавонистам ҷавоб диҳам. Дертар кӯшиш кунед."


async def send_song(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str):
    import yt_dlp
    import imageio_ffmpeg

    msg = await update.message.reply_text(f"🔎 «{query}»-ро ҷустуҷӯ карда истодаам...")
    outfile_base = f"/tmp/{update.effective_user.id}_song"
    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": outfile_base,
        "ffmpeg_location": ffmpeg_path,
        "extractor_args": {"youtube": {"player_client": ["android"]}},
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "default_search": "ytsearch1",
        "noplaylist": True,
        "quiet": True,
    }
    outfile = outfile_base + ".mp3"
    try:
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: yt_dlp.YoutubeDL(ydl_opts).download([query]),
        )
        await msg.edit_text("📤 Фиристодан...")
        with open(outfile, "rb") as f:
            await update.message.reply_audio(audio=f, title=query)
        os.remove(outfile)
    except Exception as e:
        logger.error(f"Хатогии мусиқӣ: {e}")
        await msg.edit_text("❌ Хатогӣ рух дод. Суруди дигареро санҷед.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.effective_user
    chat_id = update.effective_chat.id

    if chat_id in waiting_for_order:
        waiting_for_order.discard(chat_id)
        order_msg = (
            f"🆕 Фармоиши нав!\n\n"
            f"Аз: {user.first_name} (@{user.username})\n"
            f"ID: {user.id}\n\n"
            f"Матн: {text}"
        )
        try:
            if ADMIN_CHAT_ID:
                await context.bot.send_message(ADMIN_CHAT_ID, order_msg)
        except Exception as e:
            logger.error(f"Хатогӣ ҳангоми фиристодан ба admin: {e}")

        await update.message.reply_text(
            "✅ Фармоиши шумо қабул шуд! Мо ба зудӣ бо шумо тамос мегирем.",
            reply_markup=MAIN_MENU,
        )
        return

    if chat_id in waiting_for_music:
        waiting_for_music.discard(chat_id)
        await send_song(update, context, text)
        return

    if text == "ℹ️ Дар бораи мо":
        await update.message.reply_text(ABOUT_TEXT)

    elif text == "📋 Хизматрасониҳо":
        await update.message.reply_text(SERVICES_TEXT)

    elif text == "🛒 Фармоиш додан":
        waiting_for_order.add(chat_id)
        await update.message.reply_text(
            "✍️ Лутфан фармоиши худро дар як хат нависед "
            "(масалан: чӣ мехоҳед, миқдор, ва ғайра):"
        )

    elif text == "📞 Тамос":
        await update.message.reply_text(CONTACT_TEXT)

    elif text == "🎵 Мусиқӣ":
        waiting_for_music.add(chat_id)
        await update.message.reply_text("🎵 Номи суруд ё хонандаро нависед:")

    elif is_greeting(text):
        await update.message.reply_text(
            f"Салом, {user.first_name}! 👋\n"
            "Чӣ гуна метавонам кӯмак кунам?",
            reply_markup=MAIN_MENU,
        )

    else:
        reply = await get_ai_reply(text)
        await update.message.reply_text(reply)


flask_app = Flask(__name__)


@flask_app.route("/")
def home():
    return "NovaHelper бот кор карда истодааст!"


def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port)


def main():
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Бот оғоз шуд...")
    app.run_polling()


if __name__ == "__main__":
    main()
