"""
Telegram бот — минимальный, только открывает Mini App.
Запускается отдельно от Flask (или через Procfile worker).
"""

import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
# URL вашего задеплоенного Flask-приложения
WEBAPP_URL = os.environ.get("WEBAPP_URL")  # https://your-app.railway.app


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start — показываем кнопку для открытия Mini App."""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            text="🎵 Открыть SoundCloud",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )]
    ])

    await update.message.reply_text(
        "Привет! Нажми кнопку ниже, чтобы открыть SoundCloud плеер.",
        reply_markup=keyboard
    )


def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не задан в переменных окружения!")
        return
    if not WEBAPP_URL:
        logger.error("WEBAPP_URL не задан в переменных окружения!")
        return

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))

    logger.info("Бот запущен")
    app.run_polling()


if __name__ == "__main__":
    main()
