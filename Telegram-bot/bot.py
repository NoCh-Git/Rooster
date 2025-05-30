import os
import json
import csv
from io import StringIO
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters,
    ConversationHandler, CallbackContext
)
import gspread
from oauth2client.service_account import ServiceAccountCredentials

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account

# Load token
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not found.")

# Set up Google Sheets API using JSON from env variable
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
service_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

if not service_json:
    raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON not found in environment variables.")

creds_dict = json.loads(service_json)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# Open the sheet (change name if needed)
sheet = client.open("Rooster_bot_responses").sheet1

# Load Drive credentials from same dict as Sheets
drive_creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=scope)
drive_service = build("drive", "v3", credentials=drive_creds)

# States for conversation
VOICE, PERMISSION, LANGUAGE, NAME = range(4)

# Start command
def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Hi dear friends and family!\n\n"
        "Together with my friend Daniel, I’m working on a fun little science project where we want to compare the "
        "real sound a rooster makes with how people say a rooster sounds in different languages.\n\n"
        "To do this, I’m collecting short voice messages of people saying their version of something like "
        "\"cock-a-doodle-doo\" in their native language. We’ve set a goal of at least 20 voices per language to include it in the analysis.\n\n"
        "Could you help me by recording yourself saying the rooster sound in your native language? "
        "Just one normal human voice saying it once — no need to imitate an actual rooster!\n\n"
        "Please send your voice message below 🐓✨"
    )
    return VOICE

# Handle voice
def handle_voice(update: Update, context: CallbackContext):
    voice = update.message.voice
    if voice.duration > 15:
        update.message.reply_text("Please send a voice message shorter than 15 seconds.")
        return VOICE

    context.user_data["voice"] = voice.file_id  # Store the voice for later

    update.message.reply_text(
        "Thanks! Got your voice message.\n\n"
        "1️⃣ May we make your recording public at the end of the project?\n"
        "It would be named with a name or pseudonym you provide, like: Kikeriki_German_Anna.wav\n\n"
        "Please reply with 'Yes' or 'No'."
    )
    return PERMISSION

# Handle permission
def handle_permission(update: Update, context: CallbackContext):
    context.user_data["permission"] = update.message.text.strip()
    update.message.reply_text("2️⃣ What language is this sound from?")
    return LANGUAGE

# Handle language
def handle_language(update: Update, context: CallbackContext):
    context.user_data["language"] = update.message.text.strip()
    update.message.reply_text("3️⃣ What is your name or pseudonym?")
    return NAME

# Handle name
def handle_name(update: Update, context: CallbackContext):
    context.user_data["name"] = update.message.text.strip()
    name = context.user_data["name"]
    language = context.user_data["language"]
    permission = context.user_data["permission"]
    voice_id = context.user_data["voice"]
    telegram_id = update.message.from_user.id

    # Download voice file from Telegram
    file = context.bot.get_file(voice_id)
    local_filename = f"Kikeriki_{language}_{name}.ogg"
    file.download(local_filename)

    # Upload to Google Drive
    media = MediaFileUpload(local_filename, mimetype="audio/ogg")
    file_metadata = {
        "name": local_filename,
        "parents": [],  # Optional: add folder ID here if needed
    }
    uploaded_file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id"
    ).execute()

    # Make file public
    drive_service.permissions().create(
        fileId=uploaded_file["id"],
        body={"role": "reader", "type": "anyone"},
    ).execute()

    # Generate public link
    public_url = f"https://drive.google.com/uc?id={uploaded_file['id']}&export=download"

    # Append all data to the sheet
    sheet.append_row([name, language, permission, voice_id, telegram_id, public_url])

    update.message.reply_text(
        "Thank you! 🎉 Your answers and voice have been saved to the project.\n"
        "You can type /start to send another voice."
    )

    return ConversationHandler.END

# Cancel command
def cancel(update: Update, context: CallbackContext):
    update.message.reply_text("Cancelled.")
    return ConversationHandler.END

# Main
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            VOICE: [MessageHandler(Filters.voice, handle_voice)],
            PERMISSION: [MessageHandler(Filters.text & ~Filters.command, handle_permission)],
            LANGUAGE: [MessageHandler(Filters.text & ~Filters.command, handle_language)],
            NAME: [MessageHandler(Filters.text & ~Filters.command, handle_name)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    dp.add_handler(conv_handler)
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
