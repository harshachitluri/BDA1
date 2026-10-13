-- mart_orders: ONE ROW PER ORDER, ready for analysis.
-- Items, payments and reviews are aggregated to order level BEFORE joining, so the joins
-- can never multiply rows (an order with 3 items and 2 payments stays 1 row).
--
-- Definitions
--   items_total = sum of item prices (no freight)   <- "revenue" everywhere in this project
--   order_value = items_total + freight_total
--   delay_days  = delivered DATE - estimated DATE (calendar days; > 0 means late)
DROP TABLE IF EXISTS mart_orders;
CREATE TABLE mart_orders AS
WITH items AS (
    SELECT order_id, COUNT(*) AS n_items, SUM(price) AS items_total,
           SUM(freight_value) AS freight_total
    FROM stg_order_items GROUP BY order_id
),
pay AS (
    SELECT order_id, SUM(payment_value) AS payment_total, COUNT(*) AS n_payments
    FROM stg_order_payments GROUP BY order_id
)
SELECT
    o.order_id,
    o.customer_id,
    c.customer_unique_id,
    c.state                               AS customer_state,
    c.city                                AS customer_city,
    o.order_status,
    o.purchase_ts,
    date(o.purchase_ts)                   AS purchase_date,
    substr(o.purchase_ts, 1, 7)           AS purchase_month,
    o.delivered_ts,
    o.estimated_ts,
    COALESCE(i.n_items, 0)                AS n_items,
    i.items_total,
    i.freight_total,
    i.items_total + i.freight_total       AS order_value,
    p.payment_total,
    r.review_score,
    CASE WHEN o.delivered_ts IS NOT NULL
         THEN julianday(o.delivered_ts) - julianday(o.purchase_ts) END               AS delivery_days,
    CASE WHEN o.delivered_ts IS NOT NULL
         THEN julianday(date(o.delivered_ts)) - julianday(date(o.estimated_ts)) END  AS delay_days,
    CASE WHEN o.delivered_ts IS NULL THEN NULL
         WHEN date(o.delivered_ts) > date(o.estimated_ts) THEN 1 ELSE 0 END          AS is_late,
    -- flagged, not removed: payments do not add up to items + freight (vouchers, rounding...)
    CASE WHEN i.items_total IS NOT NULL AND p.payment_total IS NOT NULL
          AND abs(p.payment_total - (i.items_total + i.freight_total)) > 1.0
         THEN 1 ELSE 0 END                AS payment_mismatch
FROM stg_orders o
JOIN stg_customers c ON c.customer_id = o.customer_id
LEFT JOIN items i ON i.order_id = o.order_id
LEFT JOIN pay   p ON p.order_id = o.order_id
LEFT JOIN stg_reviews r ON r.order_id = o.order_id;

CREATE UNIQUE INDEX idx_mart_orders_oid ON mart_orders(order_id);
