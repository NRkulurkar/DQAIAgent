import getpass
import pandas as pd
import streamlit as st
from synapse import get_connection

st.set_page_config(page_title="Review rules", layout="wide")
st.title("Review proposed rules")


@st.cache_data(ttl=60)
def query(sql: str, params: list | None = None) -> pd.DataFrame:
    with get_connection() as conn:
        return pd.read_sql(sql, conn, params=params)


def set_status(rule_id: str, status: str, note: str) -> None:
    with get_connection() as conn:
        conn.cursor().execute("""
            UPDATE dq.rule_catalog
            SET status = ?, reviewed_by = ?, reviewed_at = GETDATE(), review_note = ?
            WHERE rule_id = ?
        """, status, getpass.getuser(), note or None, rule_id)
    st.cache_data.clear()          # show fresh data after a decision


proposed = query("""
    SELECT c.rule_id, c.table_name, c.column_name, c.description, c.category,
           c.severity, c.origin, c.rule_sql, t.test_status, t.failed_rows, t.error_message
    FROM dq.rule_catalog c
    LEFT JOIN dq.rule_test t ON t.rule_id = c.rule_id
    WHERE c.status = 'Proposed'
    ORDER BY c.table_name, c.rule_id
""")

if proposed.empty:
    st.success("No rules waiting for review.")
else:
    tables = ["All"] + sorted(proposed["table_name"].unique())
    choice = st.sidebar.selectbox("Table", tables)
    if choice != "All":
        proposed = proposed[proposed["table_name"] == choice]
    st.caption(f"{len(proposed)} rule(s) waiting for review")

    for r in proposed.itertuples():
        if r.test_status == "ERROR":
            result = f"ERROR: {r.error_message}"
        elif pd.isna(r.test_status):
            result = "not tested yet"
        else:
            result = f"{int(r.failed_rows)} failing row(s)"

        with st.expander(f"{r.rule_id}  ·  {r.description}"):
            st.write(f"**Table:** {r.table_name}  ·  **Column:** {r.column_name or 'table-level'}")
            st.write(f"**Origin:** {r.origin}  ·  **Severity:** {r.severity}  ·  **Category:** {r.category}")
            st.write(f"**Last test:** {result}")
            st.code(r.rule_sql, language="sql")
            note = st.text_input("Note or reason", key=f"note_{r.rule_id}")
            c1, c2 = st.columns(2)
            if c1.button("Approve", key=f"approve_{r.rule_id}", type="primary"):
                set_status(r.rule_id, "Approved", note)
                st.rerun()
            if c2.button("Reject", key=f"reject_{r.rule_id}"):
                if not note:
                    st.warning("Please give a reason for rejecting.")
                else:
                    set_status(r.rule_id, "Rejected", note)
                    st.rerun()

st.divider()
st.subheader("Recent decisions")
st.dataframe(query("""
    SELECT TOP 20 rule_id, table_name, status, reviewed_by, reviewed_at, review_note
    FROM dq.rule_catalog
    WHERE reviewed_at IS NOT NULL
    ORDER BY reviewed_at DESC
"""), use_container_width=True, hide_index=True)