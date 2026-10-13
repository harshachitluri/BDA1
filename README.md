# Olist Weekly Business Review - Take-Home Assignment 1

An ELT pipeline + data-quality checks + SQL analysis for the
[Olist Brazilian E-Commerce dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
(99,441 orders, 2016-2018). Everything runs on Python 3.10+ and SQLite, no database server needed.

## Run it (step by step)

```bash
# 1. get the code and install the libraries
pip install -r requirements.txt

# 2. download the dataset from Kaggle (needs a free login) and unzip ALL 9 CSVs into data/
#    data/olist_orders_dataset.csv, data/olist_customers_dataset.csv, ... (see "Folder layout")

# 3. run the pipeline (raw -> staging -> mart -> data quality alarm). Takes about 30 seconds.
python run_pipeline.py

# 4. look at any analysis query (Part C) - prints the result table
python run_query.py sql/analysis/q1_monthly_revenue_growth.sql

# 5. build the charts and the PDF report -> report/Olist_Report.pdf
python report/make_report.py

# 6. (optional) run the tests
python -m unittest tests.test_pipeline -v
```

Exit codes of `run_pipeline.py`: `0` = ok, `1` = missing file / missing column / SQL error,
`2` = a data-quality check failed (the alarm). Logs go to the console and to `logs/pipeline.log`.

## Folder layout

```
run_pipeline.py          the pipeline (Part A + the alarm of Part B)
run_query.py             helper: run one .sql file and print the result
sql/staging/             one file per staging table (cleaning rules are written as comments)
sql/mart/                mart_orders = one row per order
sql/checks/              Part B - data-quality checks (9 files)
sql/analysis/            Part C - q1..q5, plus extra1..4 used in the report/memo
dags/olist_daily_dag.py  Bonus - Airflow DAG, @daily
report/make_report.py    charts + PDF; report/Olist_Report.pdf is the generated report
tests/test_pipeline.py   idempotency, missing file, missing column, alarm
data/                    the 9 Olist CSVs (not committed - download from Kaggle)
```

## How the pipeline works (Part A)

1. **Validate** - every CSV must exist and contain the expected columns, otherwise the run stops
   immediately with a message such as `Missing input file: ...` or
   `olist_orders_dataset.csv is missing expected column(s): ['order_status']`.
2. **Load raw** - each CSV becomes a `raw_*` table, all columns as text (exactly what was in the file).
3. **Raw checks** - the "before" half of every quality check is counted and logged.
4. **Staging** - `stg_*` tables: typed, trimmed, de-duplicated, orphan rows removed.
5. **Mart** - `mart_orders` has one row per order with item totals, freight, payment total, review score,
   delivery days, delay vs estimate and late flag. Items/payments/reviews are summed *before* joining,
   so an order with 3 items and 2 payments is still one row (no double counting).
6. **Alarm** - the "after" half of every check runs on the cleaned tables; if one is above its
   allowed number the run stops with exit code 2. Results are saved in table `dq_results`.

**Idempotent:** raw tables are loaded with `if_exists="replace"`, every staging/mart/results table is
`DROP TABLE IF EXISTS` + `CREATE TABLE AS`. Running the pipeline twice gives identical row counts
(checked by a test and by hand on the full data).

## Data-quality checks (Part B)

Each file in `sql/checks/` has a header (`name`, `handling`, `max_allowed`) and two queries separated by a
`-- AFTER` line: the first counts failing rows in the **raw** tables, the second counts what is still failing
after cleaning (this one triggers the alarm).

| # | Check | Raw rows failing | Handling |
|---|-------|------------------|----------|
| 1 | null or duplicate order_id | 0 | dropped |
| 2 | delivered before purchase | 0 | fixed (timestamp set to NULL) |
| 3 | payment total != items + freight | 249 | flagged (`payment_mismatch`) |
| 4 | orders without a customer | 0 | dropped |
| 5 | delivered orders without items (own check) | 0 | flagged |
| 6 | duplicate reviews per order / bad score | 551 | de-duplicated (latest kept) |
| 7 | 'delivered' status without delivery date (own check) | 8 | flagged |
| 8 | item price <= 0 or negative freight (own check) | 0 | dropped |
| 9 | carrier / delivery timestamps out of order (own check) | 189 | flagged |

The numbers above are from the last run; the PDF report explains the reasoning for each.

## Decisions worth knowing (for the viva)

- **Customer identity:** `customer_id` changes with every order, so it can never repeat. The person is
  `customer_unique_id` - used in the repeat-purchase query (Q4). Using the wrong column gives 0%.
- **Revenue** = sum of item `price` of *delivered* orders (freight excluded). Payments are not used for revenue
  because 249 orders have payments that do not match (vouchers, rounding).
- **Late** = delivered *date* is after estimated *date* (calendar days, not timestamps, because the estimate
  has no time of day).
- **Reviews:** 551 orders have more than one review; joining them directly would duplicate orders, so
  `stg_reviews` keeps only the most recent review per order.
- **7-day rolling average** uses a generated calendar so that days without orders count as 0 and the window
  is really 7 days.
- SQLite was chosen because it needs no setup; the SQL is plain (CTEs, window functions) and would run on
  Postgres with small changes (`julianday`/`date` -> date arithmetic).

## Bonus: Airflow DAG

`dags/olist_daily_dag.py` runs `run_pipeline.py` every day (`@daily`, `catchup=False`, one retry,
`max_active_runs=1`). To try it: `pip install apache-airflow`, set `OLIST_PROJECT_DIR` to this folder and copy
the file into your Airflow `dags/` folder. Airflow is not needed for anything else, so it is not in
`requirements.txt`. (I have not run it inside a live Airflow install.)

## Dataset

Olist, "Brazilian E-Commerce Public Dataset by Olist", Kaggle -
https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
