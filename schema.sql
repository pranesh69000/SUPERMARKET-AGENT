-- Nebula Supermarket Ops Agent - Database Schema

-- 1. Owner Preferences
CREATE TABLE IF NOT EXISTS owner_preferences (
    key VARCHAR PRIMARY KEY,
    value VARCHAR NOT NULL
);

-- 2. Products (Inventory)
CREATE TABLE IF NOT EXISTS products (
    sku VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    category VARCHAR,
    unit VARCHAR NOT NULL, -- kg, g, litre, ml, packet, dozen, piece
    cost_price NUMERIC NOT NULL,
    mrp NUMERIC NOT NULL,
    stock_quantity NUMERIC NOT NULL DEFAULT 0,
    reorder_level NUMERIC NOT NULL DEFAULT 0,
    gst_rate NUMERIC NOT NULL DEFAULT 0 -- 0, 5, 12, 18
);

-- 3. Customers (Khata / Credit)
CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR UNIQUE NOT NULL,
    phone VARCHAR,
    khata_balance NUMERIC NOT NULL DEFAULT 0 -- Positive means they owe us money
);

-- 4. Transactions (Khata Ledger)
CREATE TABLE IF NOT EXISTS khata_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES customers(id),
    amount NUMERIC NOT NULL,
    transaction_type VARCHAR NOT NULL, -- 'credit_added', 'payment_received'
    reference VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. Bills (Invoices)
CREATE TABLE IF NOT EXISTS bills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status VARCHAR NOT NULL DEFAULT 'draft', -- 'draft', 'finalized'
    total_amount NUMERIC NOT NULL DEFAULT 0,
    total_tax NUMERIC NOT NULL DEFAULT 0,
    payment_mode VARCHAR, -- 'Cash', 'UPI', 'Card'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    finalized_at TIMESTAMP WITH TIME ZONE
);

-- 6. Bill Items
CREATE TABLE IF NOT EXISTS bill_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bill_id UUID REFERENCES bills(id) ON DELETE CASCADE,
    product_sku VARCHAR REFERENCES products(sku),
    quantity NUMERIC NOT NULL,
    unit_price NUMERIC NOT NULL, -- Stored here in case MRP changes later
    tax_amount NUMERIC NOT NULL DEFAULT 0,
    total_price NUMERIC NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 7. Chat History (for Langchain / Agent Memory)
CREATE TABLE IF NOT EXISTS chat_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR NOT NULL,
    message JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
