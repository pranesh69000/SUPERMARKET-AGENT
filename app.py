import os
import re
import asyncio
import threading
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

# python-telegram-bot v21 `Bot` methods are async and backed by an internal
# httpx AsyncClient bound to the event loop they first run on. Calling
# asyncio.run() per request creates AND closes a fresh loop each time, so the
# second request hits a closed loop ("Event loop is closed"). Instead, run one
# persistent loop in a background thread and submit every coroutine to it.
_loop = asyncio.new_event_loop()
threading.Thread(target=_loop.run_forever, daemon=True).start()


def run_async(coro):
    """Run a coroutine on the persistent background loop and wait for its result."""
    return asyncio.run_coroutine_threadsafe(coro, _loop).result()


def send_file_if_present(chat_id, reply_text):
    """If the reply text references a generated local file (.pdf/.pptx), send it as a document."""
    for ext in ('.pdf', '.pptx'):
        match = re.search(r'([\w.-]+\.' + ext.lstrip('.') + r')', reply_text)
        if match and os.path.exists(match.group(1)):
            with open(match.group(1), 'rb') as f:
                run_async(bot.send_document(chat_id=chat_id, document=f))


async def _process_update(update):
    """Core async handling of one Telegram update."""
    if not update or not update.message or not update.message.text:
        return

    user_message = update.message.text
    session_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id

    # Handle special /new command
    if user_message.strip() == '/new':
        supabase.table("chat_history").delete().eq("session_id", session_id).execute()
        await bot.send_message(
            chat_id=chat_id,
            text="Chat history cleared. I still remember your store preferences!"
        )
        return

    # Send typing action
    await bot.send_chat_action(chat_id=chat_id, action='typing')

    # Process via LangChain agent
    response = process_message(session_id, user_message)
    reply_text = response.get("text", "Sorry, I had trouble processing that.")

    # Reply to user
    await bot.send_message(chat_id=chat_id, text=reply_text)

    # Check for generated files (PDFs/PPTXs) and send them
    send_file_if_present(chat_id, reply_text)


@app.route('/')
def home():
    return "Nebula Supermarket Ops Agent Webhook Server is running!"


@app.route('/webhook', methods=['POST'])
def webhook():
    """Endpoint for Telegram to send updates to. Synchronous Flask view."""
    if request.method == "POST":
        update = None
        try:
            update = Update.de_json(request.get_json(force=True), bot)
            if not update:
                return 'OK'
            run_async(_process_update(update))
        except Exception as e:
            # Shield user from stack traces
            print(f"Webhook error: {type(e).__name__}: {e}")
            try:
                if update and update.effective_chat:
                    run_async(bot.send_message(
                        chat_id=update.effective_chat.id,
                        text="Sorry, I encountered an internal error. Please try again or clarify your request."
                    ))
            except Exception as inner:
                print(f"Failed to send error reply: {inner}")

    return 'OK'


async def _send_khata_reminders():
    """Find customers who owe money and message the active chat."""
    res = supabase.table("customers").select("*").gt("khata_balance", 0).execute()
    if not res.data:
        return "No reminders needed."

    hist = supabase.table("chat_history").select("session_id").limit(1).execute()
    if not hist.data:
        return "No active chats."
    chat_id = hist.data[0]['session_id']

    message = "\U0001F4C5 *Khata Payment Reminder*\nThe following customers have pending balances:\n"
    for c in res.data:
        message += f"- {c['name']}: ₹{c['khata_balance']}\n"

    await bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
    return "Reminders sent."


@app.route('/cron/reminders', methods=['GET'])
def cron_reminders():
    """Triggered by a cron job (e.g. Render Cron) to send Khata payment reminders."""
    try:
        return run_async(_send_khata_reminders())
    except Exception as e:
        print(f"Cron error: {e}")
        return str(e), 500


async def _send_weekly_report():
    """Generate and send the weekly PPTX analysis deck."""
    hist = supabase.table("chat_history").select("session_id").limit(1).execute()
    if not hist.data:
        return "No active chats."
    chat_id = hist.data[0]['session_id']

    from utils.pptx_gen import generate_analysis_deck
    pptx_path = generate_analysis_deck()

    await bot.send_message(
        chat_id=chat_id,
        text="\U0001F4CA *Your Weekly Analysis Deck is ready!*",
        parse_mode="Markdown"
    )
    with open(pptx_path, 'rb') as f:
        await bot.send_document(chat_id=chat_id, document=f)

    return "Report sent."


@app.route('/cron/weekly_report', methods=['GET'])
def cron_weekly_report():
    """Triggered by a cron job to send a weekly PPTX report."""
    try:
        return run_async(_send_weekly_report())
    except Exception as e:
        print(f"Cron error: {e}")
        return str(e), 500


if __name__ == '__main__':
    # When testing locally, you can use ngrok: ngrok http 5000
    # Then set webhook: https://api.telegram.org/bot<TOKEN>/setWebhook?url=<NGROK_URL>/webhook
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
