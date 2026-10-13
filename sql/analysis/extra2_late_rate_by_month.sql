-- Extra 2 (for the report): monthly late-delivery rate and average review score
-- Months before 2017-01 have only a few hundred orders, so we start in 2017.
SELECT
    purchase_month                       AS month,
    COUNT(*)                             AS delivered_orders,
    ROUND(100.0 * AVG(is_late), 2)       AS late_pct,
    ROUND(AVG(review_score), 2)          AS avg_review_score,
    ROUND(100.0 * AVG(CASE WHEN review_score <= 2 THEN 1.0 ELSE 0.0 END), 1) AS bad_review_pct
FROM mart_orders
WHERE order_status = 'delivered' AND is_late IS NOT NULL AND review_score IS NOT NULL
  AND purchase_month >= '2017-01'
GROUP BY purchase_month
ORDER BY purchase_month;
