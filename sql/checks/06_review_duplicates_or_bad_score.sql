-- name: review_duplicates_or_bad_score
-- handling: DROPPED/DEDUPED - reviews with a score outside 1..5 are removed; when an order has several
--           reviews only the most recent is kept (otherwise joins double count the order)
-- max_allowed: 0
-- BEFORE (raw_order_reviews): scores outside 1..5 + surplus reviews on the same order
SELECT
    (SELECT COUNT(*) FROM raw_order_reviews
      WHERE review_score IS NULL OR review_score NOT IN ('1','2','3','4','5'))
  + (SELECT COUNT(*) - COUNT(DISTINCT order_id) FROM raw_order_reviews);
-- AFTER (stg_reviews)
SELECT
    (SELECT COUNT(*) FROM stg_reviews WHERE review_score NOT BETWEEN 1 AND 5)
  + (SELECT COUNT(*) - COUNT(DISTINCT order_id) FROM stg_reviews);
