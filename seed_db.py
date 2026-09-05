import os
from dotenv import load_dotenv
from db import supabase

seed_products = [
    {
        "sku": "AASH-ATTA-5KG",
        "name": "Aashirvaad Atta 5kg",
        "category": "Staples",
        "unit": "packet",
        "cost_price": 200,
        "mrp": 225,
        "stock_quantity": 0,
        "reorder_level": 5,
        "gst_rate": 0
    },
    {
        "sku": "AASH-ATTA-10KG",
        "name": "Aashirvaad Atta 10kg",
        "category": "Staples",
        "unit": "packet",
        "cost_price": 390,
        "mrp": 440,
        "stock_quantity": 0,
        "reorder_level": 5,
        "gst_rate": 0
    },
    {
        "sku": "TATA-SALT-1KG",
        "name": "Tata Salt 1kg",
        "category": "Staples",
        "unit": "packet",
        "cost_price": 20,
        "mrp": 25,
        "stock_quantity": 0,
        "reorder_level": 10,
        "gst_rate": 0
    },
    {
        "sku": "AMUL-BTR-100G",
        "name": "Amul Butter 100g",
        "category": "Dairy",
        "unit": "packet",
        "cost_price": 48,
        "mrp": 54,
        "stock_quantity": 0,
        "reorder_level": 10,
        "gst_rate": 12
    },
    {
        "sku": "AMUL-BTR-500G",
        "name": "Amul Butter 500g",
        "category": "Dairy",
        "unit": "packet",
        "cost_price": 240,
        "mrp": 270,
        "stock_quantity": 0,
        "reorder_level": 5,
        "gst_rate": 12
    },
    {
        "sku": "FRT-SUN-OIL-1L",
        "name": "Fortune Sunflower Oil 1L",
        "category": "Oils",
        "unit": "packet",
        "cost_price": 120,
        "mrp": 140,
        "stock_quantity": 0,
        "reorder_level": 10,
        "gst_rate": 5
    },
    {
        "sku": "MAGGI-70G",
        "name": "Maggi 70g",
        "category": "Snacks",
        "unit": "packet",
        "cost_price": 12,
        "mrp": 14,
        "stock_quantity": 0,
        "reorder_level": 20,
        "gst_rate": 18
    },
    {
        "sku": "MAGGI-140G",
        "name": "Maggi 140g",
        "category": "Snacks",
        "unit": "packet",
        "cost_price": 24,
        "mrp": 28,
        "stock_quantity": 0,
        "reorder_level": 10,
        "gst_rate": 18
    },
    {
        "sku": "PARLE-G-800G",
        "name": "Parle-G 800g",
        "category": "Snacks",
        "unit": "packet",
        "cost_price": 65,
        "mrp": 75,
        "stock_quantity": 0,
        "reorder_level": 10,
        "gst_rate": 18
    },
    {
        "sku": "SURF-EXCEL-1KG",
        "name": "Surf Excel 1kg",
        "category": "Cleaning",
        "unit": "packet",
        "cost_price": 115,
        "mrp": 130,
        "stock_quantity": 0,
        "reorder_level": 5,
        "gst_rate": 18
    },
    {
        "sku": "LOOSE-SUGAR",
        "name": "Loose Sugar",
        "category": "Staples",
        "unit": "kg",
        "cost_price": 38,
        "mrp": 42,
        "stock_quantity": 0,
        "reorder_level": 20,
        "gst_rate": 5
    },
    {
        "sku": "LOOSE-RICE",
        "name": "Loose Rice (Basmati)",
        "category": "Staples",
        "unit": "kg",
        "cost_price": 75,
        "mrp": 90,
        "stock_quantity": 0,
        "reorder_level": 25,
        "gst_rate": 5
    },
    {
        "sku": "LOOSE-DAL",
        "name": "Loose Toor Dal",
        "category": "Staples",
        "unit": "kg",
        "cost_price": 120,
        "mrp": 140,
        "stock_quantity": 0,
        "reorder_level": 15,
        "gst_rate": 5
    }
]

def run():
    print("Seeding database...")
    for prod in seed_products:
        try:
            # Upsert logic to not fail if it already exists
            supabase.table("products").upsert(prod).execute()
            print(f"Upserted: {prod['name']}")
        except Exception as e:
            print(f"Failed to upsert {prod['name']}: {e}")
    print("Done seeding.")

if __name__ == "__main__":
    run()
