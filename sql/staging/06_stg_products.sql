-- stg_products: adds the english category name. Missing category -> 'unknown'.
-- (a couple of categories have no translation in the translation file, we keep the
--  portuguese name for those)
DROP TABLE IF EXISTS stg_products;
CREATE TABLE stg_products AS
SELECT
    trim(p.product_id) AS product_id,
    COALESCE(t.product_category_name_english,
             NULLIF(trim(p.product_category_name), ''),
             'unknown')                AS category,
    CAST(p.product_weight_g AS REAL)   AS weight_g
FROM raw_products p
LEFT JOIN raw_category_translation t
       ON t.product_category_name = p.product_category_name
GROUP BY trim(p.product_id);

CREATE UNIQUE INDEX idx_stg_products_pid ON stg_products(product_id);
