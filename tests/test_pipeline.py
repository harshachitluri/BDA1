"""
Small tests for the pipeline. They use a tiny fake dataset (a few rows) so they run in seconds.

Run:  python -m unittest tests.test_pipeline -v      (from the project folder)
"""
import csv
import sqlite3
from contextlib import closing
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import run_pipeline as rp  # noqa: E402


def write_mini_dataset(folder, with_items=True, drop_column=None, skip_file=None):
    """Write 9 tiny CSVs with the right columns. One delivered order, 1 item, 1 payment, 1 review."""
    rows = {
        "customers": [["c1", "u1", "01001", "sao paulo", "SP"]],
        "geolocation": [["01001", "-23.5", "-46.6", "sao paulo", "SP"]],
        "order_items": [["o1", "1", "p1", "s1", "2018-01-05 00:00:00", "100.0", "10.0"]] if with_items else [],
        "order_payments": [["o1", "1", "credit_card", "1", "110.0"]],
        "order_reviews": [["r1", "o1", "5", "", "", "2018-01-12 00:00:00", "2018-01-13 10:00:00"]],
        "orders": [["o1", "c1", "delivered", "2018-01-01 10:00:00", "2018-01-01 10:30:00",
                    "2018-01-02 09:00:00", "2018-01-10 15:00:00", "2018-01-15 00:00:00"]],
        "products": [["p1", "beleza_saude", "500", ]],
        "sellers": [["s1", "01001", "sao paulo", "SP"]],
        "category_translation": [["beleza_saude", "health_beauty"]],
    }
    for table, (filename, columns) in rp.EXPECTED.items():
        if filename == skip_file:
            continue
        data = rows[table]
        # products has 9 columns in the real file, we only fill the ones the pipeline needs
        cols = [c for c in columns]
        if drop_column and table == "orders":
            idx = cols.index(drop_column)
            cols.pop(idx)
            data = [[v for i, v in enumerate(r) if i != idx] for r in data]
        with open(Path(folder) / filename, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(cols)
            w.writerows(data)


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        tmp = Path(self.tmp.name)
        (tmp / "data").mkdir()
        # point the pipeline at the temp folder instead of the real data/olist.db
        self._old = (rp.DATA_DIR, rp.DB_PATH, rp.LOG_DIR)
        rp.DATA_DIR, rp.DB_PATH, rp.LOG_DIR = tmp / "data", tmp / "test.db", tmp / "logs"

    def tearDown(self):
        rp.DATA_DIR, rp.DB_PATH, rp.LOG_DIR = self._old
        for h in list(rp.log.handlers):
            h.close()
            rp.log.removeHandler(h)
        self.tmp.cleanup()

    def table_counts(self):
        # note: "with sqlite3.connect()" does NOT close the file, on Windows that blocks cleanup
        with closing(sqlite3.connect(rp.DB_PATH)) as conn:
            names = [r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
            return {n: conn.execute(f"SELECT COUNT(*) FROM {n}").fetchone()[0] for n in names}

    def test_runs_and_is_idempotent(self):
        write_mini_dataset(rp.DATA_DIR)
        self.assertEqual(rp.main(), 0)
        first = self.table_counts()
        self.assertEqual(first["mart_orders"], 1)
        self.assertEqual(rp.main(), 0)          # second run
        self.assertEqual(first, self.table_counts(), "row counts changed on the 2nd run")

    def test_missing_file_fails_loudly(self):
        write_mini_dataset(rp.DATA_DIR, skip_file="olist_sellers_dataset.csv")
        with self.assertLogs("olist", level="ERROR") as cm:
            self.assertEqual(rp.main(), 1)
        self.assertIn("olist_sellers_dataset.csv", "\n".join(cm.output))

    def test_missing_column_fails_loudly(self):
        write_mini_dataset(rp.DATA_DIR, drop_column="order_status")
        with self.assertLogs("olist", level="ERROR") as cm:
            self.assertEqual(rp.main(), 1)
        self.assertIn("order_status", "\n".join(cm.output))

    def test_quality_check_raises_alarm(self):
        # a delivered order without any item must trip check 05 -> exit code 2
        write_mini_dataset(rp.DATA_DIR, with_items=False)
        with self.assertLogs("olist", level="ERROR") as cm:
            self.assertEqual(rp.main(), 2)
        self.assertIn("delivered_orders_without_items", "\n".join(cm.output))


if __name__ == "__main__":
    unittest.main()
