from langchain_core.tools import tool
from db import supabase
from datetime import datetime

@tool
def daily_close() -> str:
    """
    Summarizes today's sales, tax collected, and payment mode splits.
    """
    try:
        today_date = datetime.now().strftime("%Y-%m-%d")
        
        # Get all finalized bills from today
        res = supabase.table("bills").select("*").eq("status", "finalized").gte("finalized_at", f"{today_date}T00:00:00").execute()
        
        if not res.data:
            return f"No finalized sales recorded for today ({today_date})."
            
        total_sales = sum(float(b['total_amount']) for b in res.data)
        total_tax = sum(float(b['total_tax']) for b in res.data)
        
        cash_sales = sum(float(b['total_amount']) for b in res.data if b['payment_mode'] == 'Cash')
        upi_sales = sum(float(b['total_amount']) for b in res.data if b['payment_mode'] == 'UPI')
        card_sales = sum(float(b['total_amount']) for b in res.data if b['payment_mode'] == 'Card')
        
        report = f"--- Daily Close Report ({today_date}) ---\n"
        report += f"Total Bills: {len(res.data)}\n"
        report += f"Total Sales: ₹{total_sales:.2f}\n"
        report += f"GST Collected: ₹{total_tax:.2f}\n"
        report += f"--- Payment Split ---\n"
        report += f"UPI: ₹{upi_sales:.2f}\n"
        report += f"Cash: ₹{cash_sales:.2f}\n"
        report += f"Card: ₹{card_sales:.2f}\n"
        
        return report
    except Exception as e:
        return f"Error generating daily close report: {str(e)}"

@tool
def set_preference(key: str, value: str) -> str:
    """
    Sets a global preference for the shop owner (e.g., key="default_payment_mode", value="UPI").
    """
    try:
        # Upsert
        supabase.table("owner_preferences").upsert({"key": key, "value": value}).execute()
        return f"Preference saved: {key} = {value}"
    except Exception as e:
        return f"Error setting preference: {str(e)}"

@tool
def get_preferences() -> str:
    """
    Gets all saved global preferences for the shop owner.
    """
    try:
        res = supabase.table("owner_preferences").select("*").execute()
        if not res.data: return "No preferences set."
        lines = [f"{p['key']}: {p['value']}" for p in res.data]
        return "Saved Preferences:\n" + "\n".join(lines)
    except Exception as e:
        return f"Error getting preferences: {str(e)}"
