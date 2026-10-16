import contextlib
import io
import os
import pandas as pd
import streamlit as st
from synapse import get_connection, fill_references
from build_dictionary import build_dictionary, TABLES
from build_rules import build_rules
from summarize_run import build_run_message, save_summary, latest_run_id
from Agents import call_agent

st.set_page_config(page_title="Run pipeline", layout="wide")
st.title("Run the data quality pipeline")

TABLE_NAMES = [f"{s}.{t}" for s, t in TABLES]


def run_with_log(fn, *args, **kwargs):
    """Run a function and capture what it prints, so the log can be shown on the page."""
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            return fn(*args, **kwargs), buf.getvalue(), None
    except Exception as e:
        return None, buf.getvalue(), e


def query(sql: str, params: list | None = None) -> pd.DataFrame:
    with get_connection() as conn:
        return pd.read_sql(sql, conn, params=params)


def run_proc(sql: str) -> None:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql)
        while cur.nextset():          # wait until the procedure has fully finished
            pass


# ---------- Step 1 ----------
st.header("1. Build the data dictionary")
st.caption("The AI reads the documentation and the table structure. Code validates the result before loading it.")
t1 = st.selectbox("Table", TABLE_NAMES, key="dict_table")
if st.button("Build dictionary", type="primary"):
    schema, table = t1.split(".", 1)
    with st.status(f"Building the dictionary for {t1}...", expanded=True) as s:
        rows, log, err = run_with_log(build_dictionary, schema, table)
        if log:
            st.code(log)
        if err:
            s.update(label=f"Failed: {err}", state="error")
        else:
            linked, _, _ = run_with_log(fill_references)
            s.update(label=f"Loaded {rows} columns for {t1}; linked {linked} key(s) to Dim tables",
                     state="complete")
    st.dataframe(query("""
        SELECT column_name, business_meaning, mandatory, expected_values,
               documented_rules, source_table, source_column
        FROM dq.data_dictionary WHERE table_name = ?""", [t1]),
        hide_index=True, use_container_width=True)

# ---------- Step 2 ----------
st.header("2. Generate quality rules")
st.caption("The AI writes SQL rules from the dictionary. Each rule is validated and test-compiled in Synapse.")
t2 = st.selectbox("Table", TABLE_NAMES, key="rule_table")
force = st.checkbox("Regenerate even if the documentation hasn't changed")
if st.button("Generate rules", type="primary"):
    with st.status(f"Generating rules for {t2}...", expanded=True) as s:
        res, log, err = run_with_log(build_rules, t2, force=force)
        if log:
            st.code(log)
        if err:
            s.update(label=f"Failed: {err}", state="error")
        else:
            loaded, skipped = res
            if loaded:
                run_proc("EXEC dq.usp_TestRules")   # so the Review page shows test results
            s.update(label=f"{loaded} new rule(s) proposed; {skipped} skipped as already reviewed",
                     state="complete")
    st.dataframe(query("""
        SELECT status, COUNT(*) AS rules FROM dq.rule_catalog
        WHERE table_name = ? GROUP BY status""", [t2]), hide_index=True)

# ---------- Step 3 ----------
st.header("3. Review the rules")
st.caption("A person approves or rejects every rule. Only approved rules run.")
st.page_link("pages/1_Review.py", label="Open the Review page", icon="✅")

# ---------- Step 4 ----------
st.header("4. Run the daily checks")
st.caption("Synapse runs every approved rule as plain SQL. No AI is involved in this step.")
if st.button("Run checks", type="primary"):
    with st.status("Running the approved rules in Synapse...") as s:
        try:
            run_proc("EXEC dq.usp_RunDailyChecks 'FULL', NULL")
            st.cache_data.clear()
            s.update(label="Run completed", state="complete")
        except Exception as e:
            s.update(label=f"Failed: {e}", state="error")
    st.dataframe(query("""
        SELECT TOP 5 run_id, run_date, status, rules_run, rules_failed, rules_error
        FROM dq.run_log ORDER BY run_id DESC"""), hide_index=True)

# ---------- Step 5 ----------
st.header("5. Write the AI report")
st.caption("Only counts and rule descriptions are sent to the AI, never customer data.")
if st.button("Generate report", type="primary"):
    report = None
    with st.status("The AI is writing the report...") as s:
        try:
            run_id = latest_run_id()
            report = call_agent("dq-summary", os.getenv("SUMMARY_AGENT_VERSION"),
                                build_run_message(run_id))
            save_summary(run_id, report)
            st.cache_data.clear()
            s.update(label=f"Report saved for run {run_id}", state="complete")
        except Exception as e:
            s.update(label=f"Failed: {e}", state="error")
    if report:
        st.markdown(report)