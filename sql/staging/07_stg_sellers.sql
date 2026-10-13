-- stg_sellers: one row per seller, tidy city/state text.
DROP TABLE IF EXISTS stg_sellers;
CREATE TABLE stg_sellers AS
SELECT
    trim(seller_id)             AS seller_id,
    lower(trim(seller_city))    AS city,
    upper(trim(seller_state))   AS state
FROM raw_sellers
GROUP BY trim(seller_id);
