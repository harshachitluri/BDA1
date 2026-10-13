-- name: delivered_orders_without_items
-- handling: FLAGGED - kept in mart_orders (n_items = 0, revenue NULL); they add nothing to revenue.
--           Own check: a delivered order must contain something, so any hit raises the alarm.
-- max_allowed: 0
-- BEFORE (raw_orders)
SELECT COUNT(*)
FROM raw_orders o
WHERE o.order_status = 'delivered'
  AND NOT EXISTS (SELECT 1 FROM raw_order_items i WHERE i.order_id = o.order_id);
-- AFTER (mart_orders)
SELECT COUNT(*) FROM mart_orders WHERE order_status = 'delivered' AND n_items = 0;
