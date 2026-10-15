import getpass
import sys
from synapse import get_connection


def latest_results() -> dict:
    with get_connection() as conn:
        rows = conn.cursor().execute(
            "SELECT rule_id, test_status, failed_rows, error_message FROM dq.rule_test").fetchall()
    return {r.rule_id: r for r in rows}


def review(table_name: str | None = None) -> None:
    reviewer = getpass.getuser()
    sql = ("SELECT rule_id, table_name, description, category, severity, origin, rule_sql "
           "FROM dq.rule_catalog WHERE status = 'Proposed'")
    params = []
    if table_name:
        sql += " AND table_name = ?"
        params.append(table_name)
    sql += " ORDER BY rule_id"

    with get_connection() as conn:
        rules = conn.cursor().execute(sql, *params).fetchall()
    tests = latest_results()
    print(f"\n{len(rules)} Proposed rule(s) to review\n")

    for i, r in enumerate(rules, start=1):
        t = tests.get(r.rule_id)
        if not t:
            result = "not tested yet"
        elif t.test_status == "ERROR":
            result = f"ERROR - {t.error_message}"
        else:
            result = f"{t.failed_rows} failing row(s)"

        print(f"[{i}/{len(rules)}] {r.rule_id}  ({r.origin}, {r.severity}, {r.category})")
        print(f"  {r.description}")
        print(f"  Last test: {result}")

        while True:
            choice = input("  [a]pprove  [r]eject  [v]iew SQL  [s]kip  [q]uit > ").strip().lower()
            if choice == "v":
                print("\n" + r.rule_sql + "\n")
                continue
            if choice in ("a", "r", "s", "q"):
                break

        if choice == "q":
            break
        if choice == "s":
            print()
            continue

        status = "Approved" if choice == "a" else "Rejected"
        prompt = "  Note (optional): " if choice == "a" else "  Reason for rejecting: "
        note = input(prompt).strip() or None

        with get_connection() as conn:
            conn.cursor().execute("""
                UPDATE dq.rule_catalog
                SET status = ?, reviewed_by = ?, reviewed_at = GETDATE(), review_note = ?
                WHERE rule_id = ?
            """, status, reviewer, note, r.rule_id)
        print(f"  -> {status}\n")


if __name__ == "__main__":
    # One table:  python src/review_rules.py pres.DimSavingsAccount
    # All tables: python src/review_rules.py
    review(sys.argv[1] if len(sys.argv) > 1 else None)