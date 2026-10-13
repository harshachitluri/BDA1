"""
Olist ELT pipeline (Take-Home Assignment 1, Parts A + B)

Steps
  1. validate   - every CSV exists and has the columns we expect (fail loudly if not)
  2. load raw   - CSVs -> raw_* tables in SQLite (tables are replaced, so re-runs don't duplicate)
  3. raw checks - run the "before cleaning" half of every data-quality check
  4. staging    - sql/staging/*.sql  -> stg_* tables (typed, de-duplicated, cleaned)
  5. mart       - sql/mart/*.sql     -> mart_orders (one row per order)
  6. DQ alarm   - run the "after cleaning" half of every check, stop with an error if one fails

Run:  python run_pipeline.py
Exit codes: 0 = ok, 1 = input/pipeline problem, 2 = data quality alarm
"""
import logging
import re
import sqlite3
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DB_PATH = ROOT / "olist.db"
SQL_DIR = ROOT / "sql"
LOG_DIR = ROOT / "logs"

# table name -> (csv file, columns we expect to find in it)
EXPECTED = {
    "customers": ("olist_customers_dataset.csv",
                  ["customer_id", "customer_unique_id", "customer_zip_code_prefix",
                   "customer_city", "customer_state"]),
    "geolocation": ("olist_geolocation_dataset.csv",
                    ["geolocation_zip_code_prefix", "geolocation_lat", "geolocation_lng",
                     "geolocation_city", "geolocation_state"]),
    "order_items": ("olist_order_items_dataset.csv",
                    ["order_id", "order_item_id", "product_id", "seller_id",
                     "shipping_limit_date", "price", "freight_value"]),
    "order_payments": ("olist_order_payments_dataset.csv",
                       ["order_id", "payment_sequential", "payment_type",
                        "payment_installments", "payment_value"]),
    "order_reviews": ("olist_order_reviews_dataset.csv",
                      ["review_id", "order_id", "review_score", "review_comment_title",
                       "review_comment_message", "review_creation_date",
                       "review_answer_timestamp"]),
    "orders": ("olist_orders_dataset.csv",
               ["order_id", "customer_id", "order_status", "order_purchase_timestamp",
                "order_approved_at", "order_delivered_carrier_date",
                "order_delivered_customer_date", "order_estimated_delivery_date"]),
    "products": ("olist_products_dataset.csv",
                 ["product_id", "product_category_name", "product_weight_g"]),
    "sellers": ("olist_sellers_dataset.csv",
                ["seller_id", "seller_zip_code_prefix", "seller_city", "seller_state"]),
    "category_translation": ("product_category_name_translation.csv",
                             ["product_category_name", "product_category_name_english"]),
}

log = logging.getLogger("olist")


class PipelineError(Exception):
    """Something is wrong with the inputs or a pipeline step."""


class DataQualityError(Exception):
    """At least one data quality check failed (the alarm)."""


def setup_logging():
    LOG_DIR.mkdir(exist_ok=True)
    fmt = logging.Formatter("%(asctime)s | %(levelname)-7s | %(message)s")
    log.setLevel(logging.INFO)
    # remove the handlers of a previous call (e.g. second run in the same process), but
    # leave any handler somebody else added alone
    for old in [h for h in log.handlers if getattr(h, "_from_pipeline", False)]:
        old.close()
        log.removeHandler(old)
    for handler in (logging.StreamHandler(sys.stdout),
                    logging.FileHandler(LOG_DIR / "pipeline.log", encoding="utf-8")):
        handler.setFormatter(fmt)
        handler._from_pipeline = True
        log.addHandler(handler)


# ---------------------------------------------------------------- step 1
def validate_inputs():
    log.info("STEP 1/6 validate input files")
    for table, (filename, wanted) in EXPECTED.items():
        path = DATA_DIR / filename
        if not path.exists():
            raise PipelineError(
                f"Missing input file: {path}. Download the Olist dataset from Kaggle and "
                f"put all 9 CSVs in the data/ folder (see README).")
        header = pd.read_csv(path, nrows=0).columns
        missing = [c for c in wanted if c not in header]
        if missing:
            raise PipelineError(f"{filename} is missing expected column(s): {missing}. "
                                f"Found columns: {list(header)}")
        log.info("  ok  %-22s %d columns", filename, len(header))


# ---------------------------------------------------------------- step 2
def load_raw(conn):
    log.info("STEP 2/6 load raw tables")
    for table, (filename, _) in EXPECTED.items():
        start = time.time()
        # everything is read as text on purpose: raw = exactly what was in the file.
        df = pd.read_csv(DATA_DIR / filename, dtype=str)
        # if_exists="replace" is what makes the load idempotent
        df.to_sql("raw_" + table, conn, if_exists="replace", index=False, chunksize=20000)
        log.info("  raw_%-22s %9d rows  (%.1fs)", table, len(df), time.time() - start)

    # indexes so the joins in the checks/staging don't take forever
    for stmt in ("CREATE INDEX idx_raw_orders_oid ON raw_orders(order_id)",
                 "CREATE INDEX idx_raw_orders_cid ON raw_orders(customer_id)",
                 "CREATE INDEX idx_raw_customers_cid ON raw_customers(customer_id)",
                 "CREATE INDEX idx_raw_items_oid ON raw_order_items(order_id)",
                 "CREATE INDEX idx_raw_pay_oid ON raw_order_payments(order_id)",
                 "CREATE INDEX idx_raw_rev_oid ON raw_order_reviews(order_id)"):
        conn.execute(stmt)
    conn.commit()


# ---------------------------------------------------------------- steps 4 + 5
def run_sql_folder(conn, folder, label):
    files = sorted((SQL_DIR / folder).glob("*.sql"))
    if not files:
        raise PipelineError(f"No .sql files found in {SQL_DIR / folder}")
    for f in files:
        start = time.time()
        try:
            conn.executescript(f.read_text(encoding="utf-8"))
        except sqlite3.Error as e:
            raise PipelineError(f"{label} step {f.name} failed: {e}") from e
        # each file builds one table with the same name as the file (minus the number prefix)
        table = f.stem.split("_", 1)[1]
        n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        log.info("  %-24s %9d rows  (%.1fs)", table, n, time.time() - start)


# ---------------------------------------------------------------- data quality
def read_check(path):
    """A check file looks like:
         -- name: ...
         -- handling: ...
         -- max_allowed: N          (optional, default 0)
         SELECT ... (rows failing BEFORE cleaning, on raw_ tables)
         -- AFTER
         SELECT ... (rows failing AFTER cleaning, on stg_/mart_ tables)
    """
    text = path.read_text(encoding="utf-8")
    meta = {"name": path.stem, "handling": "", "max_allowed": 0}
    in_handling = False
    for line in text.splitlines():
        if line.startswith("-- name:"):
            meta["name"] = line.split(":", 1)[1].strip()
            in_handling = False
        elif line.startswith("-- handling:"):
            meta["handling"] = line.split(":", 1)[1].strip()
            in_handling = True
        elif in_handling and re.match(r"^--\s{2,}\S", line):
            # the handling text may continue on the next comment lines (indented)
            meta["handling"] += " " + line[2:].strip()
        elif line.startswith("-- max_allowed:"):
            meta["max_allowed"] = int(line.split(":", 1)[1])
            in_handling = False
        else:
            in_handling = False
    # split on the whole "-- AFTER ..." line (the rest of that line is just a comment)
    parts = re.split(r"^-- AFTER.*$", text, maxsplit=1, flags=re.MULTILINE)
    if len(parts) != 2:
        raise PipelineError(f"{path.name}: expected a '-- AFTER' line splitting the two queries")
    meta["before_sql"], meta["after_sql"] = parts
    return meta


def count_rows(conn, sql, check_name):
    try:
        return conn.execute(sql).fetchone()[0]
    except sqlite3.Error as e:
        raise PipelineError(f"check '{check_name}' could not run: {e}") from e


def load_checks():
    files = sorted((SQL_DIR / "checks").glob("*.sql"))
    if len(files) < 5:
        raise PipelineError("Need at least 5 data quality checks in sql/checks/")
    return [read_check(f) for f in files]


def run_raw_checks(conn, checks):
    log.info("STEP 3/6 data quality checks on RAW data (information only)")
    for c in checks:
        c["rows_raw"] = count_rows(conn, c["before_sql"], c["name"])
        log.info("  %-34s %6d rows fail in raw", c["name"], c["rows_raw"])


def run_alarm_checks(conn, checks):
    log.info("STEP 6/6 data quality checks after cleaning (ALARM)")
    failed = []
    for c in checks:
        c["rows_clean"] = count_rows(conn, c["after_sql"], c["name"])
        c["status"] = "PASS" if c["rows_clean"] <= c["max_allowed"] else "FAIL"
        level = logging.INFO if c["status"] == "PASS" else logging.ERROR
        log.log(level, "  %-34s %6d rows fail after cleaning (allowed %d) -> %s",
                c["name"], c["rows_clean"], c["max_allowed"], c["status"])
        if c["status"] == "FAIL":
            failed.append(c["name"])

    # save results so the report can read them. Table is rebuilt every run -> idempotent
    conn.execute("DROP TABLE IF EXISTS dq_results")
    conn.execute("""CREATE TABLE dq_results (check_name TEXT, rows_failing_raw INTEGER,
                    rows_failing_clean INTEGER, max_allowed INTEGER, status TEXT, handling TEXT)""")
    conn.executemany("INSERT INTO dq_results VALUES (?,?,?,?,?,?)",
                     [(c["name"], c["rows_raw"], c["rows_clean"], c["max_allowed"],
                       c["status"], c["handling"]) for c in checks])
    conn.commit()

    if failed:
        raise DataQualityError(f"Data quality check(s) failed: {', '.join(failed)}")


# ---------------------------------------------------------------- main
def main():
    setup_logging()
    log.info("=== Olist pipeline started ===")
    conn = None
    try:
        validate_inputs()
        checks = load_checks()          # fail early if a check file is broken
        conn = sqlite3.connect(DB_PATH)
        load_raw(conn)
        run_raw_checks(conn, checks)
        log.info("STEP 4/6 build staging tables")
        run_sql_folder(conn, "staging", "staging")
        log.info("STEP 5/6 build mart tables")
        run_sql_folder(conn, "mart", "mart")
        conn.commit()
        run_alarm_checks(conn, checks)
    except PipelineError as e:
        log.error("PIPELINE FAILED: %s", e)
        return 1
    except DataQualityError as e:
        log.error("DATA QUALITY ALARM: %s", e)
        return 2
    except Exception:                    # anything unexpected: still log it, then fail
        log.exception("Unexpected error")
        return 1
    finally:
        if conn:
            conn.close()
    log.info("=== Pipeline finished OK ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
