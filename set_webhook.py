import os
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN missing in environment")

if __name__ == "__main__":
    url = input("Paste your public webhook URL root (e.g. https://your-app.onrender.com): ").strip()
    if not url.endswith("/webhook"):
        url = url.rstrip("/") + "/webhook"
    resp = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/setWebhook",
        json={"url": url},
        timeout=30
    )
    data = resp.json()
    if data.get("ok"):
        print("Webhook set:", url)
        # Show current webhook
        info = requests.get(f"https://api.telegram.org/bot{TOKEN}/getWebhookInfo", timeout=30).json()
        result = info.get("result")
        if result:
            print("Webhook info -> url:", result.get("url"))
            print("          pending_updates:", result.get("pending_update_count"))
        else:
            print("getWebhookInfo returned no result:", info.get("description"))
    else:
        print("Failed to set webhook:", data.get("description") or data)
