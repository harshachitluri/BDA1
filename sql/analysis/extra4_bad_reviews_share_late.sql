-- Extra 4 (for the report): how much of the bad-review problem is delivery lateness?
-- Splits delivered + reviewed orders into late / not late and shows
--   * how many orders each group has,
--   * the average review score and the % of 1-2 star reviews in each group,
--   * what share of ALL 1-2 star reviews comes from each group.
WITH base AS (
    SELECT is_late, review_score,
           CASE WHEN review_score <= 2 THEN 1 ELSE 0 END AS is_bad
    FROM mart_orders
    WHERE order_status = 'delivered' AND is_late IS NOT NULL AND review_score IS NOT NULL
)
SELECT
    CASE WHEN is_late = 1 THEN 'late' ELSE 'not late' END           AS delivery,
    COUNT(*)                                                         AS orders,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)               AS pct_of_orders,
    ROUND(AVG(review_score), 2)                                      AS avg_review_score,
    ROUND(100.0 * AVG(is_bad), 1)                                    AS pct_bad_reviews,
    SUM(is_bad)                                                      AS bad_reviews,
    ROUND(100.0 * SUM(is_bad) / SUM(SUM(is_bad)) OVER (), 1)         AS pct_of_all_bad_reviews
FROM base
GROUP BY is_late
ORDER BY is_late DESC;
