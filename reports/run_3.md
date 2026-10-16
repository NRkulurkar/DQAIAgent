## Summary
45 rules ran on 2026-10-10; 13 failed, 0 errored. The number of failures is unchanged from the previous run (13), though one fewer rule was executed (46 → 45), so coverage is slightly reduced but failure count is stable.

## Critical and high issues
1. curate.SavingsAccount — Critical: Business-key duplicates on AccountNumber + ValidFrom (2 rows).  
2. pres.DimSavingsAccount — Critical: Exactly one current row violation on IsCurrent / ValidTo per AccountNumber (2 rows).  
3. pres.DimSavingsAccount — Critical: Overlapping ValidFrom/ValidTo ranges for the same AccountNumber (2 rows).  
4. pres.FactSavingsAccount — Critical: LoadDate is NULL (LoadDate column) — 1 row.  
5. pres.FactSavingsAccount — Critical: Referential integrity — SavingsAccountSK in fact has no matching pres.DimSavingsAccount (1 row).  
6. curate.SavingsAccount — High: AccountStatus has disallowed value(s) (AccountStatus column) — 1 row.  
7. curate.SavingsAccount — High: AccountMaturityDate null/invalid when ProductCode = FIXED_1Y (AccountMaturityDate, ProductCode, AccountOpenDate) — 1 row.  
8. pres.DimSavingsAccount — High: AccountMaturityDate missing when ProductCode = FIXED_1Y (AccountMaturityDate, ProductCode) — 1 row.  
9. pres.DimSavingsAccount — High: If AccountStatus = CLOSED then AccountCloseDate missing (AccountCloseDate, AccountStatus) — 1 row.  
10. pres.DimSavingsAccount — High: IsCurrent value/ValidTo mismatch or IsCurrent not 0/1 (IsCurrent, ValidTo) — 1 row.  
11. pres.FactSavingsAccount — High: LoadDate vs DimSavingsAccount.ValidFrom mismatch (LoadDate, ValidFrom) — 1 row.

## Likely root causes (hypotheses)
- Temporal/SCD processing problem: the Dim failures (duplicate business key, multiple current rows, overlapping ranges, IsCurrent/ValidTo mismatch) likely stem from SCD merge/dedup or load-order bugs when building pres.DimSavingsAccount.  
- Upstream curate → pres inconsistencies: curate business-key duplicates and temporal issues in curate.SavingsAccount may have propagated into the dimension load.  
- Fact/lookup timing or FK population: the NULL LoadDate and missing SavingsAccountSK in the fact suggest the fact load ran before the dimension or used inconsistent keys/lookup results.  
- Business-rule/data-entry gaps: AccountMaturityDate and AccountCloseDate nulls and invalid AccountStatus indicate source data or mapping issues for conditional fields.

## Warnings
- pres.FactSavingsAccount — Warning: Closed accounts with non-zero Balance (Balance, linked AccountStatus) — requires business confirmation/join to dimension.

## Rule errors
No rule executions errored; all problems are data or rule failures and need remediation.