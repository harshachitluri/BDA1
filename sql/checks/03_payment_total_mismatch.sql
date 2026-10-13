-- name: payment_total_mismatch
-- handling: FLAGGED - kept, mart_orders.payment_mismatch = 1. Revenue uses item prices, not payments,
--           so these rows do not distort the revenue numbers. Alarm only if the rate gets unusually high.
-- max_allowed: 500
-- BEFORE: orders where sum(payments) differs from sum(price) + sum(freight) by more than 1 BRL.
-- Both sides are summed per order first, otherwise orders with many items/payments get double counted.
SELECT COUNT(*)
FROM (SELECT order_id, SUM(CAST(price AS REAL)) + SUM(CAST(freight_value AS REAL)) AS item_total
      FROM raw_order_items GROUP BY order_id) i
JOIN (SELECT order_id, SUM(CAST(payment_value AS REAL)) AS paid
      FROM raw_order_payments GROUP BY order_id) p ON p.order_id = i.order_id
WHERE abs(p.paid - i.item_total) > 1.0;
-- AFTER (mart_orders)
SELECT COUNT(*) FROM mart_orders WHERE payment_mismatch = 1;
