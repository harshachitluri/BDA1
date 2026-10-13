-- name: order_id_null_or_duplicate
-- handling: DROPPED - rows with a blank order_id are removed, repeated order_ids are reduced to one row
-- max_allowed: 0
-- BEFORE (raw_orders): null/blank order_ids + surplus copies of an order_id
SELECT
    (SELECT COUNT(*) FROM raw_orders WHERE order_id IS NULL OR trim(order_id) = '')
  + (SELECT COUNT(*) - COUNT(DISTINCT order_id) FROM raw_orders WHERE order_id IS NOT NULL);
-- AFTER (stg_orders)
SELECT
    (SELECT COUNT(*) FROM stg_orders WHERE order_id IS NULL OR order_id = '')
  + (SELECT COUNT(*) - COUNT(DISTINCT order_id) FROM stg_orders);
