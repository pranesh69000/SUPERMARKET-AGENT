from langchain_core.tools import tool
from db import supabase
from typing import List, Dict, Any

@tool
def resolve_product(search_term: str) -> str:
    """
    ALWAYS USE THIS TOOL FIRST when the user mentions a product (e.g. for billing, receiving stock, or querying).
    Searches the Product Master database for matching products.
    Returns a list of exact matching SKUs, names, and static details.
    
    If multiple materially different variants match (e.g. 5kg vs 10kg), 
    you MUST ask the user to clarify before proceeding with billing or inventory tools.
    If exactly one matches, use its SKU for the subsequent tool call.
    If zero match, you may assume it's a completely new product and use add_new_product.
    """
    try:
        # Search by name or SKU
        res = supabase.table("products").select("sku, name, category, unit, mrp, stock_quantity").ilike("name", f"%{search_term}%").execute()
        
        if not res.data:
            return f"No products found matching '{search_term}'. This might be a completely new item."
            
        results = []
        for p in res.data:
            results.append(f"- SKU: {p['sku']} | Name: {p['name']} | Unit: {p['unit']} | MRP: ₹{p['mrp']} | Current Stock: {p['stock_quantity']}")
            
        return f"Found {len(res.data)} matching products:\n" + "\n".join(results)
    except Exception as e:
        return f"Error resolving product: {str(e)}"
