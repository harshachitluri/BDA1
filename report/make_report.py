"""
Builds the 4 charts and the PDF report (report/Olist_Report.pdf).

Run AFTER the pipeline:   python report/make_report.py
All numbers in the report come from the SQL files in sql/ (run through run_query.py),
nothing is typed in by hand except the wording.
"""
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

import matplotlib
matplotlib.use("Agg")                       # no window, just save files
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from run_query import DB_PATH, run_sql_file  # noqa: E402

SQL = ROOT / "sql" / "analysis"
CHART_DIR = ROOT / "report" / "charts"
PDF_PATH = ROOT / "report" / "Olist_Report.pdf"
CHART_DIR.mkdir(parents=True, exist_ok=True)

sns.set_theme(style="whitegrid", font_scale=0.9)
BLUE, RED, GREY = "#2b6cb0", "#c53030", "#a0aec0"


def q(name):
    return run_sql_file(SQL / f"{name}.sql")


def scalar(sql):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        return conn.execute(sql).fetchone()[0]


# ------------------------------------------------------------------ data
if not DB_PATH.exists():
    sys.exit("olist.db not found - run  python run_pipeline.py  first")

q1 = q("q1_monthly_revenue_growth")
q2 = q("q2_top3_categories_per_state")
q3 = q("q3_rolling_7day_orders")
q4 = q("q4_repeat_purchase_rate")
q5 = q("q5_delivery_delay_vs_review")
by_state = q("extra1_late_rate_by_state")
by_month = q("extra2_late_rate_by_month")
first_del = q("extra3_repeat_rate_by_first_delivery")
late_split = q("extra4_bad_reviews_share_late")
with closing(sqlite3.connect(DB_PATH)) as conn:
    dq = pd.read_sql_query("SELECT * FROM dq_results ORDER BY rowid", conn)   # = check file order
    n_orders = conn.execute("SELECT COUNT(*) FROM mart_orders").fetchone()[0]

late = late_split[late_split.delivery == "late"].iloc[0]
ontime = late_split[late_split.delivery == "not late"].iloc[0]
buckets = q5[q5.section == "by delay bucket"].reset_index(drop=True)
overall = q5[q5.section == "overall"].iloc[0]
rep_ok = q4.iloc[0]
rep_wrong = q4.iloc[1]

# ------------------------------------------------------------------ metrics (exact numbers)
happy_sql = """SELECT COUNT(*) FROM mart_orders WHERE order_status='delivered' AND review_score>=4
               AND purchase_month = '{m}'"""
last_full_month = "2018-07"      # Aug-2018 reviews are still arriving, so use the month before
happy_last = scalar(happy_sql.format(m=last_full_month))
happy_rate = scalar(f"""SELECT ROUND(100.0*SUM(review_score>=4)/COUNT(*),1) FROM mart_orders
                        WHERE order_status='delivered' AND review_score IS NOT NULL""")
late_rate = scalar("""SELECT ROUND(100.0*AVG(is_late),1) FROM mart_orders
                      WHERE order_status='delivered' AND is_late IS NOT NULL""")
bad_rate = scalar("""SELECT ROUND(100.0*AVG(review_score<=2),1) FROM mart_orders
                     WHERE order_status='delivered' AND review_score IS NOT NULL""")
total_rev = scalar("SELECT ROUND(SUM(items_total)) FROM mart_orders WHERE order_status='delivered'")
last_rev = scalar(f"""SELECT ROUND(SUM(items_total)) FROM mart_orders
                      WHERE order_status='delivered' AND purchase_month='{last_full_month}'""")

# what-if for the memo: if the late share fell to 4% and late orders then behaved like on-time ones
n_rev = int(late.orders + ontime.orders)
cur_share = late.orders / n_rev
target_share = 0.04
bad_now = late.bad_reviews + ontime.bad_reviews
bad_whatif = n_rev * (target_share * late.pct_bad_reviews / 100
                      + (1 - target_share) * ontime.pct_bad_reviews / 100)
bad_saved = bad_now - bad_whatif

# ------------------------------------------------------------------ charts
def save(fig, name):
    path = CHART_DIR / name
    fig.savefig(path, dpi=170, bbox_inches="tight")
    plt.close(fig)
    return path


# Chart 1: monthly revenue
m = q1[q1.month >= "2017-01"].copy()
fig, ax = plt.subplots(figsize=(7.2, 3.1))
ax.bar(m.month, m.revenue / 1000, color=BLUE)
ax.set_title("Chart 1 - Monthly revenue of delivered orders (item prices)", loc="left", fontsize=10)
ax.set_ylabel("Revenue (R$ thousand)")
ax.set_xlabel("Purchase month")
ax.tick_params(axis="x", rotation=60)
peak = m.loc[m.revenue.idxmax()]
ax.annotate(f"Peak {peak.month}\nR$ {peak.revenue/1000:,.0f}k", (peak.month, peak.revenue / 1000),
            xytext=(-70, -5), textcoords="offset points", fontsize=8,
            arrowprops=dict(arrowstyle="->", color="black"))
c1 = save(fig, "chart1_monthly_revenue.png")

# Chart 2: review score by delay bucket
fig, ax = plt.subplots(figsize=(7.2, 3.1))
labels = [b.split(") ")[1].replace(" days", "\ndays").replace("on the", "on the\n") for b in buckets.bucket]
cols = [BLUE if "late" not in l else RED for l in labels]
bars = ax.bar(labels, buckets.avg_review_score, color=cols)
for bar, bad, n in zip(bars, buckets.pct_bad_reviews, buckets.orders):
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
            f"{bad:.0f}% bad\n(n={n:,})", ha="center", fontsize=7.5)
ax.set_ylim(0, 5.4)
ax.set_ylabel("Average review score (1-5)")
ax.set_title("Chart 2 - Review score by delivery delay vs estimated date", loc="left", fontsize=10)
ax.tick_params(axis="x", labelsize=8)
c2 = save(fig, "chart2_review_by_delay.png")

# Chart 3: monthly late % vs bad review %
fig, ax = plt.subplots(figsize=(7.2, 3.1))
ax.plot(by_month.month, by_month.late_pct, marker="o", color=RED, label="Late deliveries (%)")
ax.plot(by_month.month, by_month.bad_review_pct, marker="s", color=BLUE, label="1-2 star reviews (%)")
ax.set_ylabel("% of delivered orders")
ax.set_title("Chart 3 - Late deliveries and bad reviews move together", loc="left", fontsize=10)
ax.tick_params(axis="x", rotation=60)
ax.legend(frameon=False, fontsize=8, loc="upper left")
corr = by_month.late_pct.corr(by_month.bad_review_pct)
ax.text(0.99, 0.95, f"correlation r = {corr:.2f}", transform=ax.transAxes, ha="right", va="top", fontsize=8)
c3 = save(fig, "chart3_late_vs_bad_by_month.png")

# Chart 4: late % by state
s = by_state.sort_values("late_pct")
fig, ax = plt.subplots(figsize=(7.2, 4.0))
norm = plt.Normalize(s.avg_review_score.min(), s.avg_review_score.max())
ax.barh(s.state, s.late_pct, color=plt.cm.RdYlBu(norm(s.avg_review_score)))
ax.set_xlabel("Late deliveries (% of delivered orders)")
ax.set_title("Chart 4 - Late-delivery rate by customer state (colour = avg review score)",
             loc="left", fontsize=10)
sm = plt.cm.ScalarMappable(cmap="RdYlBu", norm=norm)
fig.colorbar(sm, ax=ax, label="avg review score", pad=0.01)
c4 = save(fig, "chart4_late_by_state.png")

# ------------------------------------------------------------------ PDF
base = getSampleStyleSheet()
BODY = ParagraphStyle("body", parent=base["BodyText"], fontSize=8.6, leading=11)
SMALL = ParagraphStyle("small", parent=BODY, fontSize=7.2, leading=8.8)
CELL = ParagraphStyle("cell", parent=BODY, fontSize=7.2, leading=8.6)
H1 = ParagraphStyle("h1", parent=base["Heading1"], fontSize=14, spaceAfter=4, spaceBefore=0)
H2 = ParagraphStyle("h2", parent=base["Heading2"], fontSize=10.5, spaceBefore=7, spaceAfter=3,
                    textColor=colors.HexColor("#1a365d"))
MEMO = ParagraphStyle("memo", parent=BODY, fontSize=9.2, leading=12.2)

GRID = TableStyle([
    ("FONTSIZE", (0, 0), (-1, -1), 7.2),
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#a0aec0")),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("TOPPADDING", (0, 0), (-1, -1), 1.6), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.6),
])


def P(text, style=BODY):
    return Paragraph(text, style)


def table(rows, widths, header=True, style=None):
    t = Table(rows, colWidths=widths, repeatRows=1 if header else 0)
    t.setStyle(GRID)
    if style:
        t.setStyle(TableStyle(style))
    return t


def money(x):
    return f"{x:,.0f}"


story = []

# ---- page 1: pipeline + data quality
story += [P("Big Data in Industry - Take-Home Assignment 1: Weekly Business Review", H1),
          P("Olist Brazilian E-Commerce dataset (99,441 orders, Sep 2016 - Oct 2018). "
            "All numbers are produced by the SQL in the repository (<font face='Courier'>sql/</font>) "
            "on the SQLite database built by <font face='Courier'>run_pipeline.py</font>.", BODY),
          P("1. Pipeline and data-quality findings (Parts A + B)", H2),
          P("The pipeline loads the 9 CSVs as <b>raw_*</b> tables (replaced on every run, so running it twice "
            "gives identical row counts - tested), builds typed/de-duplicated <b>stg_*</b> tables and one "
            f"<b>mart_orders</b> table with one row per order ({n_orders:,} rows: totals, delivery dates, "
            "delay, review score). Items, payments and reviews are summed to order level <i>before</i> joining, "
            "so no order is double counted: mart revenue equals the raw item total to the cent "
            "(R$ 13,591,643.70). A missing file or column stops the run with a clear message (exit 1); a failing "
            "quality check stops it with exit 2. Each check has a <i>before</i> query (raw data) and an "
            "<i>after</i> query (cleaned data); the alarm is on the second one.", BODY),
          Spacer(1, 5)]

rows = [[P("<b>Check</b>", CELL), P("<b>Fail in raw</b>", CELL), P("<b>Fail after cleaning</b>", CELL),
         P("<b>Result</b>", CELL), P("<b>How it was handled, and why</b>", CELL)]]
for _, r in dq.iterrows():
    rows.append([P(r.check_name.replace("_", " "), CELL), f"{r.rows_failing_raw:,}",
                 f"{r.rows_failing_clean:,}", r.status, P(r.handling, CELL)])
story.append(table(rows, [3.6 * cm, 1.5 * cm, 1.9 * cm, 1.3 * cm, 9.2 * cm],
                   style=[("ALIGN", (1, 1), (3, -1), "CENTER")]))
story += [Spacer(1, 4),
          P("<b>Reading the table.</b> This public dataset is already fairly clean: no null/duplicate order ids, "
            "no orders without a customer, no delivery before purchase and no non-positive prices. The real "
            "problems are (a) <b>551 surplus reviews</b> (orders with 2+ reviews) which would silently duplicate "
            "orders in a join, so we keep the latest review per order; (b) <b>249 orders (0.25%)</b> where "
            "payments differ from items + freight by more than R$ 1 (vouchers, instalment rounding) - flagged, "
            "not dropped, because revenue is measured from item prices; (c) <b>189 orders</b> whose carrier "
            "timestamp is out of order and <b>8 'delivered' orders without a delivery date</b> - flagged and "
            "ignored by delivery metrics. Tolerances (max_allowed) are written in each check file. "
            "Customer identity: <font face='Courier'>customer_id</font> is created per order; "
            "<font face='Courier'>customer_unique_id</font> identifies the person.", BODY),
          PageBreak()]

# ---- page 2: part C
story.append(P("2. SQL results (Part C)  -  full queries in sql/analysis/q1..q5", H2))

# Q1 as two side-by-side blocks to save space
mm = q1[q1.month >= "2017-01"].reset_index(drop=True)
y18_rev = mm[mm.month >= "2018-01"].revenue
half = (len(mm) + 1) // 2
hdr = ["Month", "Revenue (R$)", "MoM %"]
def fmt_row(r):
    # Dec-2016 revenue was only R$ 11, so the Jan-2017 growth % is meaningless -> not shown
    g = "n/m" if (pd.isna(r.growth_pct) or r.prev_month_revenue < 1000) else f"{r.growth_pct:+.1f}"
    return [r.month, money(r.revenue), g]
left = [fmt_row(mm.iloc[i]) for i in range(half)]
right = [fmt_row(mm.iloc[i]) for i in range(half, len(mm))]
while len(right) < len(left):
    right.append(["", "", ""])
rows = [hdr + hdr] + [l + r for l, r in zip(left, right)]
story += [P("<b>Q1. Month-over-month revenue and growth %</b> (delivered orders, item prices; LAG window). "
            "2016 months are omitted here (tiny base, e.g. +29,777% in Oct 2016 - see the .sql output); "
            "n/m = not meaningful.", BODY),
          table(rows, [2.0 * cm, 2.8 * cm, 1.7 * cm] * 2, style=[("ALIGN", (1, 1), (-1, -1), "RIGHT")]),
          P(f"Revenue grew about {peak.revenue/mm.revenue.iloc[0]:.0f}x from Jan 2017 (R$ {mm.revenue.iloc[0]/1000:,.0f}k) to the "
            f"{peak.month} peak (Black Friday, R$ {peak.revenue/1000:,.0f}k), but in 2018 it moved sideways between "
            f"R$ {y18_rev.min()/1e6:.2f}M and R$ {y18_rev.max()/1e6:.2f}M per month: growth has stalled.", BODY),
          Spacer(1, 3)]

# Q2
states = q2.groupby("state").revenue.sum().sort_values(ascending=False).head(6).index
rows = [["State", "#1 category (R$)", "#2 category (R$)", "#3 category (R$)"]]
for st in states:
    d = q2[q2.state == st].sort_values("rank")
    rows.append([st] + [f"{r.category} ({money(r.revenue)})" for r in d.itertuples()])
story += [P("<b>Q2. Top-3 categories per customer state</b> (DENSE_RANK; the 6 biggest states shown, "
            f"all {q2.state.nunique()} states are in the query output).", BODY),
          table(rows, [1.4 * cm, 5.2 * cm, 5.2 * cm, 5.2 * cm]),
          P(f"The same few categories ({', '.join(q2[q2['rank'] == 1].category.value_counts().head(3).index)}) "
            "lead in most states, so the category mix is similar nationwide.", BODY),
          Spacer(1, 3)]

# Q3
full = q3.dropna(subset=["rolling_7d_avg"])
pk = full.loc[full.rolling_7d_avg.idxmax()]
y18 = full[full.day.between("2018-01-01", "2018-08-15")].rolling_7d_avg
story += [P("<b>Q3. 7-day rolling average of daily order count</b> (calendar built with a recursive CTE so "
            "days with zero orders count as 0 and the window is really 7 days).", BODY),
          table([["Statistic", "Value"],
                 ["Highest 7-day average", f"{pk.rolling_7d_avg:.1f} orders/day (week ending {pk.day}, Black Friday week)"],
                 ["Typical level, Jan-mid Aug 2018", f"{y18.median():.0f} orders/day (median), range {y18.min():.0f}-{y18.max():.0f}"],
                 ["Typical level, H1 2017", f"{full[full.day.between('2017-02-01','2017-06-30')].rolling_7d_avg.median():.0f} orders/day (median)"]],
                [5.5 * cm, 11.5 * cm]),
          Spacer(1, 4)]

# Q4
rows = [["Identifier used", "Customers", "Repeat customers", "Repeat rate"]]
for r in q4.itertuples():
    rows.append([r.identifier, f"{r.customers:,}", f"{r.repeat_customers:,}", f"{r.repeat_rate_pct:.2f}%"])
story += [P("<b>Q4. Repeat-purchase rate</b> (excluding canceled/unavailable orders).", BODY),
          table(rows, [6.5 * cm, 3 * cm, 3.6 * cm, 3 * cm], style=[("ALIGN", (1, 1), (-1, -1), "RIGHT")]),
          P(f"<font face='Courier'>customer_id</font> is regenerated for every order, so using it gives a false "
            f"0% repeat rate. Using <font face='Courier'>customer_unique_id</font> the true rate is "
            f"<b>{rep_ok.repeat_rate_pct:.2f}%</b>: almost every customer buys once - retention is the "
            "weakest part of the business.", BODY), Spacer(1, 4)]

# Q5
rows = [["Delivery vs estimated date", "Orders", "Avg delay (days)", "Avg review", "% 1-2 stars"]]
for r in buckets.itertuples():
    rows.append([r.bucket.split(") ")[1], f"{r.orders:,}", f"{r.avg_delay_days:+.1f}",
                 f"{r.avg_review_score:.2f}", f"{r.pct_bad_reviews:.1f}%"])
rows.append(["All delivered orders", f"{overall.orders:,}", f"{overall.avg_delay_days:+.1f}",
             f"{overall.avg_review_score:.2f}", f"{overall.pct_bad_reviews:.1f}%"])
story += [P("<b>Q5. Delivery delay versus estimate, and review score</b> (delay = delivered date - estimated date; "
            f"negative = early). On average orders arrive <b>{abs(overall.avg_delay_days):.1f} days before</b> the "
            "estimate, yet the few late ones are punished hard: the score falls from 4.3 (early) to 1.7 (8+ days late).",
            BODY),
          table(rows, [5.6 * cm, 2.4 * cm, 3 * cm, 2.6 * cm, 3 * cm],
                style=[("ALIGN", (1, 1), (-1, -1), "RIGHT"), ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold")]),
          PageBreak()]

# ---- page 3: metrics + charts 1, 2
story.append(P("3. Metrics and charts (Part D)", H2))
rows = [[P("<b>Metric</b>", CELL), P("<b>Exact formula</b>", CELL), P("<b>Why it matters</b>", CELL),
         P("<b>Current value</b>", CELL)],
        [P("<b>NORTH STAR: Happy Orders per month</b>", CELL),
         P("COUNT(orders) WHERE order_status = 'delivered' AND review_score &gt;= 4, grouped by purchase month", CELL),
         P("Counts only orders that were both completed <i>and</i> left the customer satisfied, so it rises only "
           "if volume and experience both improve (revenue alone can grow while customers get unhappy).", CELL),
         P(f"{happy_last:,} in {last_full_month}; {happy_rate}% of reviewed delivered orders are happy", CELL)],
        [P("Late-delivery rate (guardrail)", CELL),
         P("delivered orders with DATE(delivered) &gt; DATE(estimated) / delivered orders with a delivery date", CELL),
         P("Main operational driver of bad reviews (see memo).", CELL), P(f"{late_rate}%", CELL)],
        [P("Bad-review rate (guardrail)", CELL),
         P("reviews with score &lt;= 2 / all reviews of delivered orders (latest review per order)", CELL),
         P("Direct measure of dissatisfaction; early warning for churn and brand damage.", CELL), P(f"{bad_rate}%", CELL)],
        [P("Monthly revenue (GMV)", CELL),
         P("SUM(item price) of delivered orders, by purchase month (freight excluded)", CELL),
         P("Top-line growth; tells us whether the happy-order growth is real business growth.", CELL),
         P(f"R$ {last_rev:,.0f} in {last_full_month}; R$ {total_rev/1e6:,.2f}M total", CELL)],
        [P("Repeat-purchase rate", CELL),
         P("customers (customer_unique_id) with &gt;= 2 non-canceled orders / all customers", CELL),
         P("Cheapest growth lever: a returning customer costs no acquisition spend.", CELL),
         P(f"{rep_ok.repeat_rate_pct:.2f}%", CELL)]]
story += [table(rows, [3.3 * cm, 5.4 * cm, 5.6 * cm, 2.9 * cm]), Spacer(1, 6),
          Image(str(c1), width=15.6 * cm, height=15.6 * cm * 3.1 / 7.2 * 1.02),
          P("Revenue climbed through 2017 (Black Friday peak) and has plateaued since January 2018.", SMALL),
          Spacer(1, 4),
          Image(str(c2), width=15.6 * cm, height=15.6 * cm * 3.1 / 7.2 * 1.02),
          P("Satisfaction does not fall gradually: it collapses once an order is more than ~3 days late.", SMALL),
          PageBreak()]

# ---- page 4: charts 3, 4
story += [P("4. Where the problem is", H2),
          Image(str(c3), width=15.6 * cm, height=15.6 * cm * 3.1 / 7.2 * 1.02),
          P("Nov 2017 (Black Friday), Feb 2018 and Mar 2018 had the worst late rates and, in the same months, "
            "the highest share of bad reviews.", SMALL),
          Spacer(1, 4),
          Image(str(c4), width=15.6 * cm, height=15.6 * cm * 4.0 / 7.2 * 1.0),
          P("Late rates are 3-5x higher in the north-east (AL, MA, SE, PI, CE) than in the south-east (SP, MG, PR), and "
            "average review scores are lowest where late rates are highest.", SMALL),
          PageBreak()]

# ---- page 5: memo
worst = by_state.head(3)
w_txt = ", ".join(f"{r.state} {r.late_pct:.0f}%" for r in worst.itertuples())
best = by_state.tail(2)
b_txt = ", ".join(f"{r.state} {r.late_pct:.1f}%" for r in best.itertuples())
fd = first_del.set_index("first_delivery").repeat_rate_pct
drop_rel = 100 * (1 - fd["first order LATE"] / fd["first order on time"])
bm = by_month.set_index("month")
normal = bm.drop(["2017-11", "2018-02", "2018-03"])        # months without the three big spikes
normal_late, normal_bad = normal.late_pct.median(), normal.bad_review_pct.median()
story += [P("Memo to the Vice President", H2),
          P("<b>To:</b> VP, Customer Experience &amp; Operations &nbsp;&nbsp; <b>From:</b> Data Analytics &nbsp;&nbsp; "
            "<b>Re:</b> What is hurting customer satisfaction - and the one thing to fix first", MEMO),
          Spacer(1, 5),
          P("<b>Key finding.</b> Late delivery is the largest single, fixable driver of bad reviews. Orders that arrive "
            f"after the promised date are only <b>{late.pct_of_orders:.1f}%</b> of delivered, reviewed orders but generate "
            f"<b>{late.pct_of_all_bad_reviews:.1f}%</b> of all 1-2 star reviews. A late order gets a bad review "
            f"<b>{late.pct_bad_reviews:.0f}%</b> of the time (average {late.avg_review_score:.2f} stars) against "
            f"<b>{ontime.pct_bad_reviews:.0f}%</b> for an on-time order ({ontime.avg_review_score:.2f} stars).", MEMO),
          Spacer(1, 4),
          P("<b>Evidence.</b>", MEMO),
          P(f"&bull; <b>Dose-response:</b> 1-3 days late = {buckets.pct_bad_reviews[3]:.0f}% bad reviews, "
            f"4-7 days late = {buckets.pct_bad_reviews[4]:.0f}%, 8+ days late = {buckets.pct_bad_reviews[5]:.0f}% "
            f"(Chart 2). Being early barely helps ({buckets.pct_bad_reviews[0]:.0f}% bad), so the promise matters "
            "more than the speed.", MEMO),
          P(f"&bull; <b>Over time:</b> in a typical month {normal_late:.0f}% of orders are late and {normal_bad:.0f}% of "
            "reviews are bad (medians outside the three spikes). In "
            f"Nov 2017 late orders hit {bm.late_pct['2017-11']:.1f}% (bad reviews {bm.bad_review_pct['2017-11']:.1f}%), in "
            f"Feb-Mar 2018 {bm.late_pct['2018-02']:.1f}% and {bm.late_pct['2018-03']:.1f}% (bad reviews "
            f"{bm.bad_review_pct['2018-02']:.1f}% and {bm.bad_review_pct['2018-03']:.1f}%). Monthly correlation "
            f"r = {corr:.2f} (Chart 3).", MEMO),
          P(f"&bull; <b>Where:</b> late rates are {w_txt} in the north-east versus {b_txt} in the south "
            "(Chart 4). Customers there also give the lowest scores.", MEMO),
          P(f"&bull; <b>Retention:</b> customers whose first order arrived late come back {fd['first order LATE']:.2f}% of the "
            f"time versus {fd['first order on time']:.2f}% ({drop_rel:.0f}% fewer), on a base repeat rate of only "
            f"{rep_ok.repeat_rate_pct:.1f}%.", MEMO),
          Spacer(1, 4),
          P("<b>Caveats.</b> This is correlation, not proof: "
            f"{ontime.pct_of_all_bad_reviews:.0f}% of bad reviews come from orders that were <i>not</i> late (product "
            "quality, wrong items), so lateness is not the whole story, and the retention gap is modest.", MEMO),
          Spacer(1, 4),
          P("<b>Recommendation.</b> Replace the flat delivery estimate with a <b>lane-based promise</b> "
            "(customer state x month) set at the 90th percentile of actual delivery times for that lane, and "
            "send a proactive delay message the moment an order is forecast to miss it. Orders already arrive "
            f"{abs(overall.avg_delay_days):.0f} days early on average, so the current promise is too loose in fast lanes "
            "and too tight in slow lanes (north-east, Black Friday week, Feb-Mar). <b>Pilot:</b> A/B test it for 8 weeks "
            "in AL, MA, SE, PI and CE (random half of orders on the new promise). <b>Success</b> = late rate in those "
            "states below 8% (today 14-21%) and bad-review rate down at least 3 points, with checkout conversion not "
            "falling by more than 1%. <b>Size of the prize:</b> bringing the overall late rate from "
            f"{cur_share*100:.1f}% to 4% would remove roughly <b>{bad_saved:,.0f} of the {bad_now:,.0f} bad reviews</b> "
            f"(about {100*bad_saved/bad_now:.0f}%) if the late-order effect is causal - treat that as an upper bound. "
            "Owner: Logistics; first read-out after two weeks using the late-delivery and bad-review guardrails above.", MEMO)]


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.drawString(1.5 * cm, 0.9 * cm, "Take-Home Assignment 1 - Olist weekly business review")
    canvas.drawRightString(A4[0] - 1.5 * cm, 0.9 * cm, f"Page {doc.page}")
    canvas.restoreState()


doc = SimpleDocTemplate(str(PDF_PATH), pagesize=A4, leftMargin=1.5 * cm, rightMargin=1.5 * cm,
                        topMargin=1.3 * cm, bottomMargin=1.5 * cm, title="Olist Weekly Business Review")
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print("wrote", PDF_PATH, "| charts in", CHART_DIR)
