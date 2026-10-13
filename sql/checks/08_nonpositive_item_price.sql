-- name: nonpositive_item_price
-- handling: DROPPED if it ever happens (none expected) - an item with price <= 0 or negative freight
--           would corrupt revenue
-- max_allowed: 0
-- BEFORE (raw_order_items)
SELECT COUNT(*) FROM raw_order_items
WHERE CAST(price AS REAL) <= 0 OR CAST(freight_value AS REAL) < 0;
-- AFTER (stg_order_items)
SELECT COUNT(*) FROM stg_order_items WHERE price <= 0 OR freight_value < 0;
