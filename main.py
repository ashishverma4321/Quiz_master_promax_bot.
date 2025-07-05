import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")

async def start(update: Update, context):
    await update.message.reply_text("MCQ बॉट चल रहा है! 🚀")

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app.run_polling()
