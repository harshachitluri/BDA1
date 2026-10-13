-- name: delivery_timeline_out_of_order
-- handling: FLAGGED - kept. The order happened and was paid, only a timestamp (carrier pickup) looks
--           wrong. The delivery metrics use purchase -> customer delivery, not the carrier timestamp.
--           Alarm only above 0.5% of orders.
-- max_allowed: 500
-- BEFORE (raw_orders): carrier pickup before purchase, or customer delivery before carrier pickup
SELECT COUNT(*) FROM raw_orders
WHERE order_delivered_carrier_date < order_purchase_timestamp
   OR order_delivered_customer_date < order_delivered_carrier_date;
-- AFTER (stg_orders)
SELECT COUNT(*) FROM stg_orders
WHERE carrier_ts < purchase_ts OR delivered_ts < carrier_ts;
