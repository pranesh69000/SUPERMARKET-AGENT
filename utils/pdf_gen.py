import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from db import supabase

def generate_invoice_pdf(bill_id: str) -> str:
    """Generates a PDF invoice for a finalized bill."""
    try:
        # Fetch bill details
        res_bill = supabase.table("bills").select("*").eq("id", bill_id).execute()
        if not res_bill.data:
            return f"Error: Bill {bill_id} not found."
        bill = res_bill.data[0]
        
        # Fetch items
        res_items = supabase.table("bill_items").select("*, products(name, hsn_code, gst_rate)").eq("bill_id", bill_id).execute()
        
        pdf_path = f"invoice_{bill_id[:8]}.pdf"
        c = canvas.Canvas(pdf_path, pagesize=letter)
        
        # Header
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, 750, "KIRANA STORE INVOICE")
        c.setFont("Helvetica", 10)
        c.drawString(50, 730, f"Bill ID: {bill_id}")
        c.drawString(50, 715, f"Date: {bill['finalized_at']}")
        c.drawString(50, 700, f"Payment Mode: {bill['payment_mode']}")
        
        # Table Header
        y = 660
        c.setFont("Helvetica-Bold", 10)
        c.drawString(50, y, "Item")
        c.drawString(250, y, "Qty")
        c.drawString(320, y, "Price")
        c.drawString(400, y, "Tax (GST)")
        c.drawString(480, y, "Total")
        
        y -= 20
        c.setFont("Helvetica", 10)
        for item in res_items.data:
            name = item['products']['name']
            qty = str(item['quantity'])
            price = f"Rs {item['unit_price']:.2f}"
            tax = f"Rs {item['tax_amount']:.2f} ({item['products']['gst_rate']}%)"
            total = f"Rs {item['total_price']:.2f}"
            
            c.drawString(50, y, name[:30])
            c.drawString(250, y, qty)
            c.drawString(320, y, price)
            c.drawString(400, y, tax)
            c.drawString(480, y, total)
            y -= 20
            
        # Totals
        y -= 20
        c.setFont("Helvetica-Bold", 12)
        c.drawString(350, y, f"Total Tax: Rs {bill['total_tax']:.2f}")
        y -= 20
        c.drawString(350, y, f"Grand Total: Rs {bill['total_amount']:.2f}")
        
        c.save()
        return pdf_path
    except Exception as e:
        return f"Error generating PDF: {str(e)}"

# Register this as a tool
from langchain_core.tools import tool
@tool
def generate_invoice_pdf_tool(bill_id: str) -> str:
    """Generates a PDF invoice for a given bill_id and returns the local file path."""
    return generate_invoice_pdf(bill_id)
