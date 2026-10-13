-- stg_customers: one row per customer_id.
-- NOTE: customer_id is generated per ORDER. customer_unique_id is the real person.
DROP TABLE IF EXISTS stg_customers;
CREATE TABLE stg_customers AS
SELECT
    trim(customer_id)              AS customer_id,
    trim(customer_unique_id)       AS customer_unique_id,
    trim(customer_zip_code_prefix) AS zip_prefix,
    lower(trim(customer_city))     AS city,
    upper(trim(customer_state))    AS state
FROM raw_customers
WHERE customer_id IS NOT NULL
GROUP BY trim(customer_id);

CREATE UNIQUE INDEX idx_stg_customers_cid ON stg_customers(customer_id);
