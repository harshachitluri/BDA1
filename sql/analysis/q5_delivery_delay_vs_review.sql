-- Q5: Delivery delay versus the estimated date, and how it relates to review score
-- delay_days = delivered DATE - estimated DATE (negative = early, positive = late).
-- Only delivered orders with a delivery date AND a review are used.
-- One result with three sections (column "section"): the overall average, the same numbers per
-- delay bucket (the main answer), and the average delay for each review score.
WITH base AS (
    SELECT order_id, delay_days, review_score,
           CASE
               WHEN delay_days <= -8 THEN '1) 8+ days early'
               WHEN delay_days <= -1 THEN '2) 1-7 days early'
               WHEN delay_days = 0   THEN '3) on the estimated day'
               WHEN delay_days <= 3  THEN '4) 1-3 days late'
               WHEN delay_days <= 7  THEN '5) 4-7 days late'
               ELSE                       '6) 8+ days late'
           END AS bucket
    FROM mart_orders
    WHERE order_status = 'delivered'
      AND delay_days IS NOT NULL
      AND review_score IS NOT NULL
)
SELECT 'overall' AS section,
       'all delivered orders' AS bucket,
       COUNT(*) AS orders,
       ROUND(AVG(delay_days), 2) AS avg_delay_days,
       ROUND(AVG(review_score), 2) AS avg_review_score,
       ROUND(100.0 * SUM(CASE WHEN review_score <= 2 THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_bad_reviews
FROM base
UNION ALL
SELECT 'by delay bucket', bucket, COUNT(*),
       ROUND(AVG(delay_days), 2),
       ROUND(AVG(review_score), 2),
       ROUND(100.0 * SUM(CASE WHEN review_score <= 2 THEN 1 ELSE 0 END) / COUNT(*), 1)
FROM base
GROUP BY bucket
UNION ALL
SELECT 'by review score', 'score ' || review_score, COUNT(*),
       ROUND(AVG(delay_days), 2),
       ROUND(AVG(review_score), 2),
       NULL
FROM base
GROUP BY review_score
ORDER BY 1 DESC, 2;
