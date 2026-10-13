-- stg_orders: one clean row per order_id.
-- Cleaning rules:
--   * drop rows with a null/blank order_id
--   * keep only one row per order_id (earliest purchase wins)
--   * drop orders whose customer_id does not exist in the customers file
--   * delivery timestamp earlier than purchase timestamp is impossible -> set to NULL (fixed)
--   * blank strings become NULL, status is lower-cased
DROP TABLE IF EXISTS stg_orders;
CREATE TABLE stg_orders AS
WITH ranked AS (
    SELECT
        trim(order_id)                                       AS order_id,
        trim(customer_id)                                    AS customer_id,
        lower(trim(order_status))                            AS order_status,
        NULLIF(trim(order_purchase_timestamp), '')           AS purchase_ts,
        NULLIF(trim(order_approved_at), '')                  AS approved_ts,
        NULLIF(trim(order_delivered_carrier_date), '')       AS carrier_ts,
        NULLIF(trim(order_delivered_customer_date), '')      AS delivered_ts,
        NULLIF(trim(order_estimated_delivery_date), '')      AS estimated_ts,
        ROW_NUMBER() OVER (PARTITION BY trim(order_id)
                           ORDER BY order_purchase_timestamp) AS rn
    FROM raw_orders
    WHERE order_id IS NOT NULL AND trim(order_id) <> ''
)
SELECT
    order_id, customer_id, order_status, purchase_ts, approved_ts, carrier_ts,
    CASE WHEN delivered_ts < purchase_ts THEN NULL ELSE delivered_ts END AS delivered_ts,
    estimated_ts
FROM ranked
WHERE rn = 1
  AND customer_id IN (SELECT customer_id FROM raw_customers);

CREATE UNIQUE INDEX idx_stg_orders_oid ON stg_orders(order_id);
