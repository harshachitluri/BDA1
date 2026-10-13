-- Extra 3 (for the report): does a bad FIRST delivery experience reduce repeat purchases?
-- For every customer_unique_id we take their first delivered order (ROW_NUMBER by purchase time),
-- note whether it was late, and then check if the customer has any later order.
-- Customers whose first order was in the last 6 months of the data are excluded so everybody
-- had at least ~6 months of chance to come back (otherwise recent customers look like churners).
WITH ordered AS (
    SELECT
        customer_unique_id, order_id, purchase_ts, is_late, review_score,
        ROW_NUMBER() OVER (PARTITION BY customer_unique_id ORDER BY purchase_ts) AS nth_order,
        COUNT(*)     OVER (PARTITION BY customer_unique_id)                      AS total_orders
    FROM mart_orders
    WHERE order_status = 'delivered'
),
first_orders AS (
    SELECT * FROM ordered
    WHERE nth_order = 1
      AND is_late IS NOT NULL
      AND purchase_ts < (SELECT date(MAX(purchase_ts), '-6 months') FROM mart_orders)
)
SELECT
    CASE WHEN is_late = 1 THEN 'first order LATE' ELSE 'first order on time' END AS first_delivery,
    COUNT(*)                                                       AS customers,
    SUM(CASE WHEN total_orders >= 2 THEN 1 ELSE 0 END)             AS came_back,
    ROUND(100.0 * AVG(CASE WHEN total_orders >= 2 THEN 1.0 ELSE 0.0 END), 2) AS repeat_rate_pct
FROM first_orders
GROUP BY is_late
ORDER BY is_late;
