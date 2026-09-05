from pydantic import BaseModel, Field
from langchain_core.tools import tool
from db import supabase
from typing import Optional, List, Dict, Any
import uuid

@tool
def manage_bill(action: str, current_bill_id: Optional[str] = None, sku: Optional[str] = None, quantity: Optional[float] = None, payment_mode: Optional[str] = None) -> str:
    """
    Handles multi-turn billing.
    Actions:
    - 'start': Starts a new draft bill. Returns the new bill_id. (Requires no other arguments).
    - 'add_item': Adds an item to the draft bill. (Requires current_bill_id, sku, quantity). You MUST use resolve_product first to find the exact sku!
    - 'remove_item': Removes an item from the draft bill. (Requires current_bill_id, sku).
    - 'view': Views the current contents and total of the draft bill. (Requires current_bill_id).
    - 'finalize': Finalizes the bill, decrements stock atomically, and records payment mode. (Requires current_bill_id, payment_mode [Cash, UPI, Card]).
    """
    try:
        action = action.strip().lower()
        if action == 'start':
            res = supabase.table("bills").insert({"status": "draft"}).execute()
            bill_id = res.data[0]['id']
            return f"Started new draft bill. ID: {bill_id}. Keep this ID to add items."
            
        if not current_bill_id:
            return "Error: current_bill_id is required for this action."
            
        if action == 'add_item':
            if not sku or not quantity: return "Error: sku and quantity required."
            
            # Find product by exact SKU
            prod_res = supabase.table("products").select("*").eq("sku", sku).execute()
            if not prod_res.data: return f"Product with SKU '{sku}' not found."
            product = prod_res.data[0]
            
            # Oversell Guard at draft level
            if float(product['stock_quantity']) < float(quantity):
                return f"Cannot add {quantity} {product['unit']} of {product['name']}. Only {product['stock_quantity']} in stock."
                
            mrp = float(product['mrp'])
            gst_rate = float(product['gst_rate'])
            
            # Calculate taxes
            base_price = mrp / (1 + (gst_rate / 100))
            tax_amount = (mrp - base_price) * float(quantity)
            total_price = mrp * float(quantity)
            
            item_data = {
                "bill_id": current_bill_id,
                "product_sku": product['sku'],
                "quantity": float(quantity),
                "unit_price": mrp,
                "tax_amount": tax_amount,
                "total_price": total_price
            }
            supabase.table("bill_items").insert(item_data).execute()
            return f"Added {quantity} x {product['name']} to bill. Item total: ₹{total_price:.2f}."
            
        elif action == 'remove_item':
            if not sku: return "Error: sku required."
            # Delete from bill items
            supabase.table("bill_items").delete().eq("bill_id", current_bill_id).eq("product_sku", sku).execute()
            return f"Removed SKU {sku} from bill."
            
        elif action == 'view':
            res = supabase.table("bill_items").select("*, products(name)").eq("bill_id", current_bill_id).execute()
            if not res.data: return "Bill is currently empty."
            
            lines = []
            total = 0
            for item in res.data:
                name = item['products']['name']
                qty = item['quantity']
                price = item['total_price']
                total += price
                lines.append(f"- {name}: {qty} qty -> ₹{price:.2f}")
            
            return f"Current Bill:\n" + "\n".join(lines) + f"\nTotal: ₹{total:.2f}"
            
        elif action == 'finalize':
            if not payment_mode: return "Error: payment_mode (Cash/UPI/Card) required to finalize."
            
            # Fetch bill to check if already finalized (Idempotency)
            bill_res = supabase.table("bills").select("status").eq("id", current_bill_id).execute()
            if not bill_res.data: return f"Error: Bill {current_bill_id} not found."
            if bill_res.data[0]['status'] == 'finalized':
                return f"Bill {current_bill_id} is already finalized. No further action needed."
            
            # Fetch all items
            items_res = supabase.table("bill_items").select("*").eq("bill_id", current_bill_id).execute()
            if not items_res.data: return "Cannot finalize an empty bill."
            
            # Atomically decrement stock and calculate totals
            total_amount = 0
            total_tax = 0
            
            for item in items_res.data:
                sku = item['product_sku']
                qty = float(item['quantity'])
                total_amount += float(item['total_price'])
                total_tax += float(item['tax_amount'])
                
                # Atomic decrement via RPC
                try:
                    supabase.rpc('decrement_stock_safe', {'p_sku': sku, 'p_quantity': qty}).execute()
                except Exception as e:
                    # Supabase Python client raises exception on RPC error (e.g. from RAISE EXCEPTION)
                    return f"Oversell guard triggered for SKU {sku}! Database refused to decrement stock: {str(e)}"
                
            # Update bill status
            update_data = {
                "status": "finalized",
                "payment_mode": payment_mode,
                "total_amount": total_amount,
                "total_tax": total_tax,
                "finalized_at": "now()"
            }
            supabase.table("bills").update(update_data).eq("id", current_bill_id).execute()
            
            return f"Bill {current_bill_id} finalized successfully!\nPayment Mode: {payment_mode}\nTotal Amount: ₹{total_amount:.2f}\nTotal Tax: ₹{total_tax:.2f}."
            
        else:
            return f"Unknown action: {action}"
            
    except Exception as e:
        return f"Error managing bill: {str(e)}"
