"""Run one .sql file against olist.db and print the result.

Usage:  python run_query.py sql/analysis/q1_monthly_revenue_growth.sql [max_rows]
"""
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).resolve().parent / "olist.db"


def run_sql_file(path):
    """Return the result of a .sql file as a DataFrame."""
    with closing(sqlite3.connect(DB_PATH)) as conn:
        return pd.read_sql_query(Path(path).read_text(encoding="utf-8"), conn)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    if not DB_PATH.exists():
        sys.exit("olist.db not found - run  python run_pipeline.py  first")
    max_rows = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    df = run_sql_file(sys.argv[1])
    pd.set_option("display.width", 200)
    print(df.head(max_rows).to_string(index=False))
    print(f"\n({len(df)} rows)")
