-- name: delivered_before_purchase
-- handling: FIXED - an impossible delivery timestamp is set to NULL (order kept, delivery metrics ignore it)
-- max_allowed: 0
-- BEFORE (raw_orders)
SELECT COUNT(*) FROM raw_orders
WHERE order_delivered_customer_date IS NOT NULL
  AND order_delivered_customer_date < order_purchase_timestamp;
-- AFTER (stg_orders)
SELECT COUNT(*) FROM stg_orders
WHERE delivered_ts IS NOT NULL AND delivered_ts < purchase_ts;
