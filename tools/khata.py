from langchain_core.tools import tool
from db import supabase
from typing import Optional

@tool
def manage_khata(customer_name: str, action: str, amount: Optional[float] = None, phone: Optional[str] = None) -> str:
    """
    Manages customer credit (Khata).
    Actions:
    - 'check_balance': Checks how much the customer owes. (Requires customer_name).
    - 'add_credit': Adds an amount to what the customer owes (they bought on credit). (Requires customer_name, amount).
    - 'record_payment': Records a payment from the customer, reducing what they owe. (Requires customer_name, amount).
    - 'create_customer': Creates a new customer for Khata. (Requires customer_name, optional phone).
    """
    try:
        # Check if customer exists
        res = supabase.table("customers").select("*").ilike("name", f"%{customer_name}%").execute()
        
        if action == 'create_customer':
            if res.data: return f"Customer '{res.data[0]['name']}' already exists."
            supabase.table("customers").insert({"name": customer_name, "phone": phone}).execute()
            return f"Customer '{customer_name}' created successfully."
            
        if not res.data:
            return f"Customer '{customer_name}' not found. Please create them first using 'create_customer' action."
            
        customer = res.data[0]
        customer_id = customer['id']
        current_balance = float(customer['khata_balance'])
        
        if action == 'check_balance':
            if current_balance == 0:
                return f"{customer['name']} owes nothing (Balance is ₹0)."
            return f"{customer['name']}'s balance is ₹{current_balance:.2f} (they owe you this amount)."
            
        elif action == 'add_credit':
            if amount is None or amount <= 0: return "Please specify a valid positive amount."
            new_balance = current_balance + amount
            supabase.table("customers").update({"khata_balance": new_balance}).eq("id", customer_id).execute()
            
            # Record transaction
            supabase.table("khata_transactions").insert({
                "customer_id": customer_id,
                "amount": amount,
                "transaction_type": "credit_added",
                "reference": "Bought on credit"
            }).execute()
            
            return f"Added ₹{amount} to {customer['name']}'s khata. New balance they owe: ₹{new_balance:.2f}."
            
        elif action == 'record_payment':
            if amount is None or amount <= 0: return "Please specify a valid positive amount."
            new_balance = current_balance - amount
            supabase.table("customers").update({"khata_balance": new_balance}).eq("id", customer_id).execute()
            
            # Record transaction
            supabase.table("khata_transactions").insert({
                "customer_id": customer_id,
                "amount": amount,
                "transaction_type": "payment_received",
                "reference": "Payment received"
            }).execute()
            
            return f"Recorded ₹{amount} payment from {customer['name']}. Remaining balance they owe: ₹{new_balance:.2f}."
            
        else:
            return f"Unknown action: {action}"
            
    except Exception as e:
        return f"Error managing khata: {str(e)}"
