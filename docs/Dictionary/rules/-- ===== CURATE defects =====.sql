-- ===== CURATE defects =====
INSERT INTO curate.SavingsAccount
(AccountNumber, CustomerID, ProductCode, AccountStatus, Currency,
 AccountOpenDate, AccountMaturityDate, AccountCloseDate, InterestRate, Balance,
 ValidFrom, ValidTo, LoadTimestamp)
-- D1: duplicate of ACC004 (same key, same ValidFrom)
SELECT 'ACC004','CUST04','NOTICE_90','OPEN','GBP','2024-11-20',NULL,NULL,4.10,40000.00,'2026-09-28','9999-12-31','2026-09-28 02:00' UNION ALL
-- D2: invalid status value 'CLSD'
SELECT 'ACC009','CUST08','EASY_ACCESS','CLSD','GBP','2020-07-07',NULL,NULL,3.50,300.00,'2026-09-29','9999-12-31','2026-09-29 02:00' UNION ALL
-- D3: open date after maturity date
SELECT 'ACC010','CUST09','FIXED_1Y','OPEN','GBP','2026-05-01','2025-05-01',NULL,4.80,15000.00,'2026-09-29','9999-12-31','2026-09-29 02:00';

-- ===== DIM defects =====
-- D4: two current rows for ACC005
UPDATE pres.DimSavingsAccount SET IsCurrent = 1
WHERE AccountNumber = 'ACC005' AND ValidFrom = '2026-09-28';

-- D5: overlapping validity periods for ACC003
UPDATE pres.DimSavingsAccount SET ValidTo = '2026-09-30'
WHERE AccountNumber = 'ACC003' AND ValidFrom = '2026-09-28';

-- D6: CLOSED account with no close date
UPDATE pres.DimSavingsAccount SET AccountCloseDate = NULL
WHERE AccountNumber = 'ACC003' AND ValidFrom = '2026-09-29';

-- D7: fixed-term account with no maturity date
UPDATE pres.DimSavingsAccount SET AccountMaturityDate = NULL
WHERE AccountNumber = 'ACC006';

-- ===== FACT defects =====
-- D8: null LoadDate
UPDATE pres.FactSavingsAccount SET LoadDate = NULL
WHERE AccountNumber = 'ACC001';

-- D9: CLOSED account with non-zero balance
UPDATE pres.FactSavingsAccount SET Balance = 250.00
WHERE AccountNumber = 'ACC003' AND DateSK = 20260929;

-- D10: orphan fact row (no matching Dim row)
INSERT INTO pres.FactSavingsAccount
(SavingsAccountSK, AccountNumber, DateSK, LoadDate, Balance, InterestRate)
SELECT 99999, 'ACC011', 20260929, '2026-09-29', 7000.00, 3.50;

SELECT 'curate' AS layer, COUNT(*) AS row_count FROM curate.SavingsAccount UNION ALL
SELECT 'dim',   COUNT(*) FROM pres.DimSavingsAccount UNION ALL
SELECT 'fact',  COUNT(*) FROM pres.FactSavingsAccount;