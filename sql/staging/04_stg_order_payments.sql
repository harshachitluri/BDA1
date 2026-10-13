-- stg_order_payments: typed values; payments for unknown orders are dropped.
-- One order can have several payment rows (e.g. card + voucher) -> always SUM before joining.
DROP TABLE IF EXISTS stg_order_payments;
CREATE TABLE stg_order_payments AS
SELECT
    trim(order_id)                        AS order_id,
    CAST(payment_sequential AS INTEGER)   AS payment_sequential,
    lower(trim(payment_type))             AS payment_type,
    CAST(payment_installments AS INTEGER) AS installments,
    CAST(payment_value AS REAL)           AS payment_value
FROM raw_order_payments
WHERE trim(order_id) IN (SELECT order_id FROM stg_orders);

CREATE INDEX idx_stg_pay_oid ON stg_order_payments(order_id);
