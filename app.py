import os
import re
from flask import Flask, request
from telegram import Update, Bot
from agent import process_message
from db import supabase

app = Flask(__name__)

# Initialize standard Python Telegram Bot instance
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN missing in environment")
bot = Bot(token=TELEGRAM_TOKEN)

@app.route('/')
def home():
    return "Nebula Supermarket Ops Agent Webhook Server is running!"

@app.route('/webhook', methods=['POST'])
async def webhook():
    """Endpoint for Telegram to send updates to."""
    if request.method == "POST":
        try:
            update = Update.de_json(request.get_json(force=True), bot)
            
            # Basic validation
            if not update or not update.message or not update.message.text:
                return 'OK'
                
            user_message = update.message.text
            session_id = str(update.effective_user.id)
            
            # Handle special /new command
            if user_message.strip() == '/new':
                supabase.table("chat_history").delete().eq("session_id", session_id).execute()
                await bot.send_message(chat_id=update.effective_chat.id, text="Chat history cleared. I still remember your store preferences!")
                return 'OK'
                
            # Send typing action
            await bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
            
            # Process via LangChain agent
            response = process_message(session_id, user_message)
            reply_text = response.get("text", "Sorry, I had trouble processing that.")
            
            # Reply to user
            await bot.send_message(chat_id=update.effective_chat.id, text=reply_text)
            
            # Check for generated files (PDFs/PPTXs) and send them
            pdf_match = re.search(r'([\w-]+\.pdf)', reply_text)
            if pdf_match and os.path.exists(pdf_match.group(1)):
                with open(pdf_match.group(1), 'rb') as f:
                    await bot.send_document(chat_id=update.effective_chat.id, document=f)
                    
            pptx_match = re.search(r'([\w-]+\.pptx)', reply_text)
            if pptx_match and os.path.exists(pptx_match.group(1)):
                with open(pptx_match.group(1), 'rb') as f:
                    await bot.send_document(chat_id=update.effective_chat.id, document=f)
                    
        except Exception as e:
            # Shield user from stack traces
            print(f"Webhook error: {e}")
            if update and update.effective_chat:
                await bot.send_message(chat_id=update.effective_chat.id, text="Sorry, I encountered an internal error. Please try again or clarify your request.")
            
    return 'OK'

@app.route('/cron/reminders', methods=['GET'])
async def cron_reminders():
    """Triggered by a cron job (e.g. Render Cron) to send Khata payment reminders."""
    try:
        # Find customers who owe money
        res = supabase.table("customers").select("*").gt("khata_balance", 0).execute()
        if not res.data:
            return "No reminders needed."
            
        # Get active session_id (chat_id) from history to know who to message
        hist = supabase.table("chat_history").select("session_id").limit(1).execute()
        if not hist.data: return "No active chats."
        chat_id = hist.data[0]['session_id']
        
        message = "📅 *Khata Payment Reminder*\nThe following customers have pending balances:\n"
        for c in res.data:
            message += f"- {c['name']}: ₹{c['khata_balance']}\n"
            
        await bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
        return "Reminders sent."
    except Exception as e:
        print(f"Cron error: {e}")
        return str(e), 500

@app.route('/cron/weekly_report', methods=['GET'])
async def cron_weekly_report():
    """Triggered by a cron job to send a weekly PPTX report."""
    try:
        hist = supabase.table("chat_history").select("session_id").limit(1).execute()
        if not hist.data: return "No active chats."
        chat_id = hist.data[0]['session_id']
        
        from utils.pptx_gen import generate_analysis_deck
        pptx_path = generate_analysis_deck()
        
        await bot.send_message(chat_id=chat_id, text="📊 *Your Weekly Analysis Deck is ready!*", parse_mode="Markdown")
        with open(pptx_path, 'rb') as f:
            await bot.send_document(chat_id=chat_id, document=f)
            
        return "Report sent."
    except Exception as e:
        print(f"Cron error: {e}")
        return str(e), 500

if __name__ == '__main__':
    # When testing locally, you can use ngrok: ngrok http 5000
    # Then set webhook: https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://<NGROK_URL>/webhook
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
