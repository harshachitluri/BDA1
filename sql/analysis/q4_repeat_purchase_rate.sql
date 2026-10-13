-- Q4: Repeat-purchase rate
-- TRAP in this dataset: customer_id is generated fresh for EVERY order, so it never repeats.
-- The real person is customer_unique_id (see the dataset documentation).
-- Repeat rate = customers with 2+ orders / all customers. Canceled and unavailable orders
-- are not purchases, so they are excluded.
-- The last two rows show the WRONG answer (using customer_id) next to the right one.
WITH per_customer AS (
    SELECT customer_unique_id, COUNT(*) AS orders
    FROM mart_orders
    WHERE order_status NOT IN ('canceled', 'unavailable')
    GROUP BY customer_unique_id
),
per_customer_id AS (
    SELECT customer_id, COUNT(*) AS orders
    FROM mart_orders
    WHERE order_status NOT IN ('canceled', 'unavailable')
    GROUP BY customer_id
)
SELECT 'customer_unique_id (correct)' AS identifier,
       COUNT(*)                                                   AS customers,
       SUM(CASE WHEN orders >= 2 THEN 1 ELSE 0 END)               AS repeat_customers,
       ROUND(100.0 * SUM(CASE WHEN orders >= 2 THEN 1 ELSE 0 END) / COUNT(*), 2) AS repeat_rate_pct
FROM per_customer
UNION ALL
SELECT 'customer_id (wrong, per-order id)',
       COUNT(*),
       SUM(CASE WHEN orders >= 2 THEN 1 ELSE 0 END),
       ROUND(100.0 * SUM(CASE WHEN orders >= 2 THEN 1 ELSE 0 END) / COUNT(*), 2)
FROM per_customer_id;
