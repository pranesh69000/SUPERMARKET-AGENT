-- Atomic Stock Decrement Function
-- Prevents race conditions during concurrent checkouts

CREATE OR REPLACE FUNCTION decrement_stock_safe(p_sku VARCHAR, p_quantity NUMERIC)
RETURNS NUMERIC AS $$
DECLARE
    current_stock NUMERIC;
BEGIN
    -- Select the current stock and lock the row
    SELECT stock_quantity INTO current_stock
    FROM products
    WHERE sku = p_sku
    FOR UPDATE;

    IF current_stock IS NULL THEN
        RAISE EXCEPTION 'Product with SKU % not found.', p_sku;
    END IF;

    IF current_stock < p_quantity THEN
        RAISE EXCEPTION 'Oversell Guard: Not enough stock. Available: %, Requested: %', current_stock, p_quantity;
    END IF;

    -- Update the stock
    UPDATE products
    SET stock_quantity = stock_quantity - p_quantity
    WHERE sku = p_sku;

    RETURN current_stock - p_quantity;
END;
$$ LANGUAGE plpgsql;
