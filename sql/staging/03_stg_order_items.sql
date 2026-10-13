-- stg_order_items: typed prices; items that point to an unknown order are dropped.
DROP TABLE IF EXISTS stg_order_items;
CREATE TABLE stg_order_items AS
SELECT
    trim(order_id)                    AS order_id,
    CAST(order_item_id AS INTEGER)    AS order_item_id,
    trim(product_id)                  AS product_id,
    trim(seller_id)                   AS seller_id,
    CAST(price AS REAL)               AS price,
    CAST(freight_value AS REAL)       AS freight_value
FROM raw_order_items
WHERE trim(order_id) IN (SELECT order_id FROM stg_orders);

CREATE INDEX idx_stg_items_oid ON stg_order_items(order_id);
