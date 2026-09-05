from pydantic import BaseModel, Field
from langchain_core.tools import tool
from db import supabase
from typing import Optional, List, Dict, Any

@tool
def receive_stock(item_name: str, quantity: float, cost_price: Optional[float] = None, mrp: Optional[float] = None) -> str:
    """
    Receives stock for an existing product, updating its quantity.
    Optionally updates cost_price and mrp if provided.
    Returns a success or error message.
    """
    try:
        # Check if product exists (case-insensitive search)
        res = supabase.table("products").select("*").ilike("name", f"%{item_name}%").execute()
        if not res.data:
            return f"Product matching '{item_name}' not found. Please add it as a new product first."
        
        product = res.data[0]
        new_quantity = float(product['stock_quantity']) + float(quantity)
        
        # Update product
        update_data = {
            "stock_quantity": new_quantity
        }
        if cost_price is not None: update_data["cost_price"] = float(cost_price)
        if mrp is not None: update_data["mrp"] = float(mrp)
            
        supabase.table("products").update(update_data).eq("sku", product["sku"]).execute()
        
        msg = f"Successfully received stock. {product['name']} now has {new_quantity} {product['unit']} in stock."
        if cost_price or mrp:
            msg += f" Prices updated."
        return msg
    except Exception as e:
        return f"Error receiving stock: {str(e)}"

@tool
def add_new_product(sku: str, name: str, category: str, unit: str, cost_price: float, mrp: float, initial_stock: float, reorder_level: float, gst_rate: float) -> str:
    """
    Adds a completely new product (SKU) to the inventory.
    """
    try:
        data = {
            "sku": sku,
            "name": name,
            "category": category,
            "unit": unit,
            "cost_price": float(cost_price),
            "mrp": float(mrp),
            "stock_quantity": float(initial_stock),
            "reorder_level": float(reorder_level),
            "gst_rate": float(gst_rate)
        }
        supabase.table("products").insert(data).execute()
        return f"Successfully added new product: {name} (SKU: {sku}) with {initial_stock} {unit} in stock."
    except Exception as e:
        return f"Error adding product: {str(e)}"

@tool
def query_stock(item_name: str) -> str:
    """
    Queries the current stock level and prices for a product.
    """
    try:
        res = supabase.table("products").select("*").ilike("name", f"%{item_name}%").execute()
        if not res.data:
            return f"No product found matching '{item_name}'."
        
        results = []
        for p in res.data:
            results.append(f"{p['name']} (SKU: {p['sku']}): {p['stock_quantity']} {p['unit']} left. MRP: ₹{p['mrp']}, Cost: ₹{p['cost_price']}, GST: {p['gst_rate']}%.")
        return "\n".join(results)
    except Exception as e:
        return f"Error querying stock: {str(e)}"

@tool
def query_low_stock(dummy: str = "") -> str:
    """
    Returns a list of products whose stock_quantity is at or below their reorder_level.
    """
    try:
        res = supabase.table("products").select("*").execute()
        low_stock = []
        for p in res.data:
            if float(p['stock_quantity']) <= float(p['reorder_level']):
                low_stock.append(f"- {p['name']}: {p['stock_quantity']} {p['unit']} (Reorder at: {p['reorder_level']})")
        
        if not low_stock:
            return "No items are currently running low on stock."
        return "Items low on stock:\n" + "\n".join(low_stock)
    except Exception as e:
        return f"Error checking low stock: {str(e)}"
