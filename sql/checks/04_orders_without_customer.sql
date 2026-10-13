-- name: orders_without_customer
-- handling: DROPPED - an order we cannot attach to a customer/state is useless for the analysis
-- max_allowed: 0
-- BEFORE (raw_orders LEFT JOIN raw_customers)
SELECT COUNT(*)
FROM raw_orders o
LEFT JOIN raw_customers c ON c.customer_id = o.customer_id
WHERE c.customer_id IS NULL;
-- AFTER (mart_orders must always have a customer_unique_id)
SELECT COUNT(*) FROM mart_orders WHERE customer_unique_id IS NULL;
