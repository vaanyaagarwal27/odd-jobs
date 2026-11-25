import os
import sys
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

load_dotenv()

token = os.environ.get("TELEGRAM_BOT_TOKEN")
if not token:
    print("Error: TELEGRAM_BOT_TOKEN is missing from .env")
    sys.exit(1)

chat_id = os.environ.get("MY_CHAT_ID")
if not chat_id:
    print("Error: MY_CHAT_ID is missing from .env")
    sys.exit(1)

async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("hi. it's peter.")

app = ApplicationBuilder().token(token).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.Chat(int(chat_id)), reply))

print("peter is running")
app.run_polling()
