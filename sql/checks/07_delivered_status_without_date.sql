-- name: delivered_status_without_date
-- handling: FLAGGED - kept, but delivery_days / delay_days are NULL so they are skipped in delivery metrics
-- max_allowed: 10
-- BEFORE (raw_orders): status says delivered but there is no delivery timestamp
SELECT COUNT(*) FROM raw_orders
WHERE order_status = 'delivered' AND order_delivered_customer_date IS NULL;
-- AFTER (mart_orders)
SELECT COUNT(*) FROM mart_orders WHERE order_status = 'delivered' AND delivered_ts IS NULL;
