-- Q1: Month-over-month revenue and growth %
-- Revenue = sum of item prices (no freight) of DELIVERED orders, by purchase month.
-- LAG() looks at the previous month's revenue; growth % = (this - last) / last * 100.
-- The first month has no previous month, so growth is NULL.
WITH monthly AS (
    SELECT
        purchase_month                   AS month,
        COUNT(*)                         AS orders,
        ROUND(SUM(items_total), 2)       AS revenue
    FROM mart_orders
    WHERE order_status = 'delivered'
    GROUP BY purchase_month
)
SELECT
    month,
    orders,
    revenue,
    LAG(revenue) OVER (ORDER BY month)   AS prev_month_revenue,
    ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY month))
          / LAG(revenue) OVER (ORDER BY month), 1)  AS growth_pct
FROM monthly
ORDER BY month;
