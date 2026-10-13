-- stg_reviews: ONE review per order.
-- Some orders have 2+ reviews (and some review_ids repeat across orders), which would
-- double count orders when joined. We keep the most recent review for each order.
-- Reviews with a score outside 1..5 are dropped.
DROP TABLE IF EXISTS stg_reviews;
CREATE TABLE stg_reviews AS
WITH ranked AS (
    SELECT
        trim(order_id)                   AS order_id,
        trim(review_id)                  AS review_id,
        CAST(review_score AS INTEGER)    AS review_score,
        review_creation_date,
        review_answer_timestamp,
        ROW_NUMBER() OVER (PARTITION BY trim(order_id)
                           ORDER BY review_answer_timestamp DESC, review_creation_date DESC,
                                    review_id) AS rn
    FROM raw_order_reviews
    WHERE review_score IN ('1', '2', '3', '4', '5')
      AND trim(order_id) IN (SELECT order_id FROM stg_orders)
)
SELECT order_id, review_id, review_score, review_creation_date, review_answer_timestamp
FROM ranked
WHERE rn = 1;

CREATE UNIQUE INDEX idx_stg_reviews_oid ON stg_reviews(order_id);
