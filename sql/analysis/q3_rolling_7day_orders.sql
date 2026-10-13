-- Q3: 7-day rolling average of daily order count
-- Days with zero orders do not exist in the data, so a plain "6 PRECEDING ROWS" window would
-- silently stretch over more than 7 calendar days. We build a calendar first (recursive CTE),
-- left join the counts (missing day = 0) and then use the window over calendar days.
-- All orders count (any status), by purchase date. The first 6 days have no full week -> NULL.
WITH RECURSIVE calendar(day) AS (
    SELECT MIN(purchase_date) FROM mart_orders
    UNION ALL
    SELECT date(day, '+1 day') FROM calendar
    WHERE day < (SELECT MAX(purchase_date) FROM mart_orders)
),
daily AS (
    SELECT purchase_date AS day, COUNT(*) AS orders
    FROM mart_orders
    GROUP BY purchase_date
),
filled AS (
    SELECT c.day, COALESCE(d.orders, 0) AS orders
    FROM calendar c
    LEFT JOIN daily d ON d.day = c.day
)
SELECT
    day,
    orders,
    CASE WHEN ROW_NUMBER() OVER (ORDER BY day) >= 7
         THEN ROUND(AVG(orders) OVER (ORDER BY day ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 2)
    END AS rolling_7d_avg
FROM filled
ORDER BY day;
