import os
import sys
from synapse import get_connection
from Agents import call_agent
import pyodbc

def latest_run_id() -> int:
    with get_connection() as conn:
        return conn.cursor().execute("SELECT MAX(run_id) FROM dq.run_log").fetchone()[0]


def build_run_message(run_id: int) -> str:
    """Aggregated results only: no customer data leaves Synapse."""
    with get_connection() as conn:
        cur = conn.cursor()
        run = cur.execute("""
            SELECT run_id, run_mode, run_date, rules_run, rules_failed, rules_error
            FROM dq.run_log WHERE run_id = ?""", run_id).fetchone()
        prev = cur.execute("""
            SELECT TOP 1 run_id, rules_run, rules_failed, rules_error
            FROM dq.run_log WHERE run_id < ? ORDER BY run_id DESC""", run_id).fetchone()
        rows = cur.execute("""
            SELECT r.rule_id, r.table_name, r.category, r.severity, r.origin,
                   c.description, r.outcome, r.failed_rows, r.error_message
            FROM dq.results r
            JOIN dq.rule_catalog c ON c.rule_id = r.rule_id
            WHERE r.run_id = ? AND r.outcome <> 'PASS'
            ORDER BY r.table_name, r.rule_id""", run_id).fetchall()

    lines = [
        f"Run {run.run_id} | mode {run.run_mode} | date {run.run_date}",
        f"Totals: {run.rules_run} rules run, {run.rules_failed} failed, {run.rules_error} errored",
    ]
    if prev:
        lines.append(f"Previous run {prev.run_id}: {prev.rules_run} run, "
                     f"{prev.rules_failed} failed, {prev.rules_error} errored")
    else:
        lines.append("No previous run.")

    lines.append("\nFailed or errored rules:")
    for r in rows:
        detail = f"{r.failed_rows} failed rows" if r.outcome == "FAIL" else f"ERROR: {r.error_message}"
        lines.append(f"- {r.rule_id} | {r.table_name} | {r.category} | {r.severity} | "
                     f"{r.origin} | {r.description} | {detail}")
    if not rows:
        lines.append("- none")
    return "\n".join(lines)


def save_summary(run_id: int, text: str) -> None:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM dq.ai_summary WHERE run_id = ?", run_id)
        # Send the text as NVARCHAR(MAX): long strings otherwise go as 'ntext',
        # which Synapse dedicated pools don't support
        cur.setinputsizes([(pyodbc.SQL_INTEGER, 0, 0), (pyodbc.SQL_WVARCHAR, 0, 0)])
        cur.execute("""
            INSERT INTO dq.ai_summary (run_id, summary_text, created_at)
            SELECT ?, ?, GETDATE()""", run_id, text[:8000])


if __name__ == "__main__":
    # Latest run:   python src/summarize_run.py
    # Specific run: python src/summarize_run.py 3
    run_id = int(sys.argv[1]) if len(sys.argv) > 1 else latest_run_id()

    message = build_run_message(run_id)
    report = call_agent("dq-summary", os.getenv("SUMMARY_AGENT_VERSION"), message)
    save_summary(run_id, report)

    os.makedirs("reports", exist_ok=True)
    path = f"reports/run_{run_id}.md"
    with open(path, "w", encoding="utf-8") as f:
        f.write(report)

    print(report)
    print(f"\nSaved to {path} and dq.ai_summary")