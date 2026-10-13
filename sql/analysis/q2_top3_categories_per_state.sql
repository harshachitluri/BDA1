-- Q2: Top 3 product categories per customer state by revenue
-- Revenue = item price of delivered orders. We go through stg_order_items (one row per item) so
-- that every item is attributed to its own category; mart_orders is only used for state + status.
-- DENSE_RANK so that categories with exactly the same revenue share a rank (no gaps).
WITH category_revenue AS (
    SELECT
        o.customer_state                    AS state,
        p.category                          AS category,
        ROUND(SUM(i.price), 2)              AS revenue
    FROM stg_order_items i
    JOIN mart_orders  o ON o.order_id  = i.order_id
    JOIN stg_products p ON p.product_id = i.product_id
    WHERE o.order_status = 'delivered'
    GROUP BY o.customer_state, p.category
),
ranked AS (
    SELECT
        state, category, revenue,
        DENSE_RANK() OVER (PARTITION BY state ORDER BY revenue DESC) AS rnk
    FROM category_revenue
)
SELECT state, rnk AS rank, category, revenue
FROM ranked
WHERE rnk <= 3
ORDER BY state, rnk;
