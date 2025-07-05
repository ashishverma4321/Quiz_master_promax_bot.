import os
import json
import random
import logging
import fitz  # PyMuPDF
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# === CONFIG ===
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
HF_TOKEN = os.environ.get("HF_TOKEN")
ADMIN_ID = 123456789  # Replace with your Telegram user ID

# === LOGGING ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === UTIL: Generate MCQs using Hugging Face ===
def generate_mcqs(text):
    API_URL = "https://api-inference.huggingface.co/models/google/flan-t5-base"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    prompt = f"Generate a multiple choice question with 4 options from this text:\n{text}"
    response = requests.post(API_URL, headers=headers, json={"inputs": prompt})
    try:
        return response.json()[0]['generated_text']
    except:
        return "Unable to generate MCQ."

# === UTIL: Extract text from PDF ===
def extract_text_from_pdf(file_path):
    text = ""
    doc = fitz.open(file_path)
    for page in doc:
        text += page.get_text()
    doc.close()
    return text

# === HANDLE: /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    files = [f.replace(".json", "") for f in os.listdir("data") if f.endswith(".json")]
    keyboard = [[InlineKeyboardButton(f"📘 {f}", callback_data=f"quiz_{f}")] for f in files]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("👋 Welcome!\nSelect a quiz:", reply_markup=reply_markup)

# === HANDLE: /upload ===
async def upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ You are not authorized to upload.")
        return
    await update.message.reply_text("📎 Please send the PDF now.")
    return

# === HANDLE: PDF Document ===
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    file = await update.message.document.get_file()
    file_path = f"temp_{update.message.document.file_name}"
    await file.download_to_drive(file_path)

    text = extract_text_from_pdf(file_path)
    mcq = generate_mcqs(text[:1000])  # only first 1000 chars

    quiz_name = update.message.document.file_name.replace(".pdf", "")
    with open(f"data/{quiz_name}.json", "w", encoding="utf-8") as f:
        json.dump([{"question": mcq, "options": ["A", "B", "C", "D"], "answer_index": 0}], f)

    await update.message.reply_text(f"✅ Quiz saved as '{quiz_name}'")
    os.remove(file_path)

# === SEND MCQ ===
async def send_quiz(chat_id, context, quiz_name):
    with open(f"data/{quiz_name}.json", "r", encoding="utf-8") as f:
        questions = json.load(f)
    q = random.choice(questions)
    await context.bot.send_poll(
        chat_id=chat_id,
        question=q["question"],
        options=q["options"],
        type="quiz",
        correct_option_id=q["answer_index"],
        is_anonymous=False
    )
    context.job_queue.run_once(lambda ctx: context.application.create_task(send_quiz(chat_id, ctx, quiz_name)), 15)

# === HANDLE BUTTON ===
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    quiz_name = query.data.replace("quiz_", "")
    await send_quiz(query.message.chat.id, context, quiz_name)

# === MAIN ===
if __name__ == '__main__':
    os.makedirs("data", exist_ok=True)
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("upload", upload))
    app.add_handler(CallbackQueryHandler(handle_button))
    app.add_handler(MessageHandler(filters.Document.PDF, handle_document))

    logger.info("🤖 Bot is running...")
    app.run_polling()
