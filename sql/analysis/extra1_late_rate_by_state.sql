-- Extra 1 (for the report): late-delivery rate, delivery time and review score by customer state
-- Delivered orders only. States with fewer than 300 delivered orders are left out (too noisy).
SELECT
    customer_state                                         AS state,
    COUNT(*)                                               AS delivered_orders,
    ROUND(100.0 * AVG(is_late), 1)                         AS late_pct,
    ROUND(AVG(delivery_days), 1)                           AS avg_delivery_days,
    ROUND(AVG(delay_days), 1)                              AS avg_delay_days,
    ROUND(AVG(review_score), 2)                            AS avg_review_score
FROM mart_orders
WHERE order_status = 'delivered' AND is_late IS NOT NULL
GROUP BY customer_state
HAVING COUNT(*) >= 300
ORDER BY late_pct DESC;
