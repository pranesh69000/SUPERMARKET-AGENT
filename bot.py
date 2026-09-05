import os
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
from agent import process_message
from db import supabase

load_dotenv()

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    await update.message.reply_text("Hello! I am your Supermarket Ops Agent. How can I help you today?")

async def new_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clears the chat history for this user."""
    session_id = str(update.effective_user.id)
    supabase.table("chat_history").delete().eq("session_id", session_id).execute()
    await update.message.reply_text("Chat history cleared. I still remember your store preferences!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process user messages via the LangChain agent."""
    user_message = update.message.text
    session_id = str(update.effective_user.id)
    
    # Send processing action
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    
    try:
        # Call LangChain Agent
        response = process_message(session_id, user_message)
        reply_text = response["text"]
        
        # Send text response
        await update.message.reply_text(reply_text)
        
        # Check if the text contains a file path we should upload (e.g. .pdf or .pptx)
        # In a real app, the tool could return a structured payload. Here we use regex.
        pdf_match = re.search(r'([\w-]+\.pdf)', reply_text)
        if pdf_match and os.path.exists(pdf_match.group(1)):
            await update.message.reply_document(document=open(pdf_match.group(1), 'rb'))
            
        pptx_match = re.search(r'([\w-]+\.pptx)', reply_text)
        if pptx_match and os.path.exists(pptx_match.group(1)):
            await update.message.reply_document(document=open(pptx_match.group(1), 'rb'))
            
    except Exception as e:
        await update.message.reply_text(f"Sorry, an error occurred: {str(e)}")

def main() -> None:
    """Start the bot."""
    if not TELEGRAM_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not found.")
        return
        
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("new", new_chat))

    # on non command i.e message - process via agent
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot is polling. Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
