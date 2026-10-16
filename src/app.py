import pandas as pd
import streamlit as st
from synapse import get_connection

st.set_page_config(page_title="DQ Agent", layout="wide")


@st.cache_data(ttl=60)          # re-query Synapse at most once a minute
def query(sql: str, params: list | None = None) -> pd.DataFrame:
    with get_connection() as conn:
        return pd.read_sql(sql, conn, params=params)


st.title("Data Quality Agent")

runs = query("""
    SELECT run_id, run_mode, run_date, status, rules_run, rules_failed, rules_error
    FROM dq.run_log ORDER BY run_id DESC
""").fillna({"rules_run": 0, "rules_failed": 0, "rules_error": 0})

if runs.empty:
    st.info("No runs yet. Trigger the pipeline pl_dq_daily_checks first.")
    st.stop()

# Pick a run (latest first)
labels = {r.run_id: f"Run {r.run_id}  ·  {r.run_date}  ·  {r.run_mode}" for r in runs.itertuples()}
run_id = st.selectbox("Run", list(labels), format_func=labels.get)
run = runs.set_index("run_id").loc[run_id]

# Headline numbers
c1, c2, c3, c4 = st.columns(4)
c1.metric("Rules run", int(run.rules_run))
c2.metric("Failed", int(run.rules_failed))
c3.metric("Errors", int(run.rules_error))
c4.metric("Passed", int(run.rules_run - run.rules_failed - run.rules_error))

tab_fail, tab_report, tab_trend = st.tabs(["Failures", "AI report", "Trend"])

with tab_fail:
    fails = query("""
        SELECT r.severity, r.table_name, c.column_name, r.rule_id, c.description, r.origin,
               r.outcome, r.failed_rows, r.error_message
        FROM dq.results r
        JOIN dq.rule_catalog c ON c.rule_id = r.rule_id
        WHERE r.run_id = ? AND r.outcome <> 'PASS'
        ORDER BY CASE r.severity WHEN 'Critical' THEN 1 WHEN 'High' THEN 2 ELSE 3 END,
                 r.table_name, r.rule_id
    """, [int(run_id)])
    if fails.empty:
        st.success("All approved rules passed.")
    else:
        st.dataframe(fails, use_container_width=True, hide_index=True)

with tab_report:
    report = query("SELECT summary_text FROM dq.ai_summary WHERE run_id = ?", [int(run_id)])
    if report.empty:
        st.info(f"No AI report for this run yet. Run: python src/summarize_run.py {run_id}")
    else:
        st.markdown(report.iloc[0, 0])

with tab_trend:
    trend = runs.sort_values("run_id").set_index("run_id")[["rules_failed", "rules_error"]]
    st.line_chart(trend)