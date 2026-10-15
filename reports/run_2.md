## Summary
46 rules ran, 13 failed, 0 errored. Counts are unchanged from the previous run (Run 1: 46 run, 13 failed, 0 errored) — no net improvement or regression.

## Critical and high issues
- pres.DimSavingsAccount — Temporal/SCD problems: exactly one current row violated (R014, Critical) and overlapping ValidFrom/ValidTo ranges present (R015, Critical); 2 rows affected for each.  
- curate.SavingsAccount — Business-key duplicates (R012, Critical): AccountNumber + ValidFrom not unique; 2 failed rows.  
- pres.FactSavingsAccount — Referential integrity (R014, Critical): SavingsAccountSK in fact has no matching pres.DimSavingsAccount; 1 failed row.  
- pres.FactSavingsAccount — Load metadata missing (R004, Critical): LoadDate NULL on 1 row.  
- curate.SavingsAccount — Domain/format & conditional rules (R003, R008, High): invalid AccountStatus (1 row) and missing/invalid AccountMaturityDate for FIXED_1Y (1 row).  
- pres.DimSavingsAccount — Conditional/temporal (R007, R010, R013, High): missing maturity for FIXED_1Y (1), missing AccountCloseDate when CLOSED (1), IsCurrent mismatch or invalid value (1).

## Likely root causes
- Upstream SCD/ingest ordering or deduplication: duplicate business keys in curate.SavingsAccount plus overlapping/duplicate current rows in pres.DimSavingsAccount suggest load-order or dedupe logic failed between curate → pres.  
- Dimension/fact sync gap: fact row referencing a dimension key while the dimension either missing or not yet current (explains referential integrity and LoadDate mismatch).  
- Data-entry or mapping gaps for conditional fields: Product-specific maturity and closed-date rules failing in both curate and pres indicate a gap in the source-to-curate mapping or validation.

## Warnings
- pres.FactSavingsAccount R011: CLOSED accounts with non-zero Balance (1 row) — needs business confirmation/join verification.

## Rule errors
No rule executions errored; all failures are data issues or rule violations (rules themselves ran successfully and need data or process fixes).