import os
import time
import threading
import requests
from pyngrok import ngrok
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

def start_tunnel():
    print("[TUNNEL] Starting ngrok tunnel...")
    # Open a ngrok tunnel to the dev server port
    public_url = ngrok.connect(5000).public_url
    print(f"\n✅ [TUNNEL CONNECTED] Public URL: {public_url}")
    
    # Set Webhook in Telegram
    webhook_url = f"{public_url}/webhook"
    print(f"[TELEGRAM] Setting webhook to: {webhook_url}")
    
    response = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook?url={webhook_url}")
    
    if response.status_code == 200 and response.json().get('ok'):
        print("✅ [TELEGRAM ACKNOWLEDGED] Webhook successfully set! You can now chat with the bot.")
    else:
        print(f"❌ [ERROR] Failed to set webhook: {response.text}")

if __name__ == '__main__':
    # Start the tunnel in a separate thread so Flask can run in the main thread
    threading.Thread(target=start_tunnel, daemon=True).start()
    
    # Start the Flask app
    print("[SERVER] Starting Flask server on port 5000...")
    
    # Import and run the app from app.py
    from app import app
    app.run(host='0.0.0.0', port=5000, use_reloader=False)
