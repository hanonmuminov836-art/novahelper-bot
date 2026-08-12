# -*- coding: utf-8 -*-
import os
import logging
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

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8961244766:AAE26-C5Bo4ngiY-8jtq6BquqF3nJYdWrus")
ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", "123456789"))

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
    "ва фармоиш додан кӯмак мекунад."
)

CONTACT_TEXT = (
    "📞 Барои тамос:\n\n"
    "Telegram: @ваш_username\n"
    "Телефон: +992 XX XXX XXXX"
)

GREETING_WORDS = [
    "салом", "ассалом", "ассалому", "салм", "хай", "hi", "hello",
    "нағз", "чихел", "чӣ хел", "субҳ", "шаб бахайр", "рӯз хуш",
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
    ],
    resize_keyboard=True,
)

waiting_for_order = set()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"Салом, {user.first_name}! 👋\n\n"
        "Хуш омадед ба NovaHelper. Аз менюи поён интихоб кунед "
        "ё танҳо бо ман сӯҳбат кунед:",
        reply_markup=MAIN_MENU,
    )


def is_greeting(text: str) -> bool:
    text_lower = text.lower().strip()
    return any(word in text_lower for word in GREETING_WORDS)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.effective_user
    chat_id = update.effective_chat.id

    if chat_id in waiting_for_order:
        waiting_for_order.discard(chat_id)
        order_msg = (
            f"🆕 Фармоиши нав!\n\n"
            f"Аз: {user.first_name} (@{user.username or 'бе username'})\n"
            f"ID: {user.id}\n\n"
            f"Матн: {text}"
        )
        try:
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=order_msg)
        except Exception as e:
            logger.error(f"Хатогӣ ҳангоми фиристодан ба админ: {e}")

        await update.message.reply_text(
            "✅ Фармоиши шумо қабул шуд! Мо ба зудӣ бо шумо тамос мегирем.",
            reply_markup=MAIN_MENU,
        )
        return

    if text == "ℹ️ Дар бораи мо":
        await update.message.reply_text(ABOUT_TEXT, reply_markup=MAIN_MENU)

    elif text == "📋 Хизматрасониҳо":
        await update.message.reply_text(SERVICES_TEXT, reply_markup=MAIN_MENU)

    elif text == "🛒 Фармоиш додан":
        waiting_for_order.add(chat_id)
        await update.message.reply_text(
            "✍️ Лутфан фармоиши худро дар як хат нависед "
            "(масалан: чӣ мехоҳед, миқдор, ва ғайра):"
        )

    elif text == "📞 Тамос":
        await update.message.reply_text(CONTACT_TEXT, reply_markup=MAIN_MENU)

    elif is_greeting(text):
        await update.message.reply_text(
            f"Салом, {user.first_name}! 😊 Хушҳолам, ки шумо ҳастед. "
            "Чӣ гуна метавонам кӯмак кунам? Аз менюи поён интихоб кунед.",
            reply_markup=MAIN_MENU,
        )

    else:
        await update.message.reply_text(
            "Мутаассифона, ман ин паёмро нафаҳмидам 🤔\n"
            "Лутфан аз менюи поён интихоб кунед ё «салом» гӯед!",
            reply_markup=MAIN_MENU,
        )


flask_app = Flask(__name__)


@flask_app.route("/")
def home():
    return "NovaHelper бот кор карда истодааст! ✅"


def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port)


def main():
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Бот оғоз шуд...")
    app.run_polling()


if __name__ == "__main__":
    main()
