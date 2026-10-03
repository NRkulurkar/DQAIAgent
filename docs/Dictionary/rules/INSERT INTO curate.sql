INSERT INTO curate.SavingsAccount
(AccountNumber, CustomerID, ProductCode, AccountStatus, Currency,
 AccountOpenDate, AccountMaturityDate, AccountCloseDate, InterestRate, Balance,
 ValidFrom, ValidTo, LoadTimestamp)
-- Day 1: 28 Sep 2026
SELECT 'ACC001','CUST01','EASY_ACCESS','OPEN','GBP','2023-01-15',NULL,NULL,3.50,12500.00,'2026-09-28','9999-12-31','2026-09-28 02:00' UNION ALL
SELECT 'ACC002','CUST02','FIXED_1Y','OPEN','GBP','2026-03-01','2027-03-01',NULL,4.75,25000.00,'2026-09-28','9999-12-31','2026-09-28 02:00' UNION ALL
SELECT 'ACC003','CUST03','EASY_ACCESS','OPEN','GBP','2021-06-10',NULL,NULL,3.50,800.00,'2026-09-28','2026-09-29','2026-09-28 02:00' UNION ALL
SELECT 'ACC004','CUST04','NOTICE_90','OPEN','GBP','2024-11-20',NULL,NULL,4.10,40000.00,'2026-09-28','9999-12-31','2026-09-28 02:00' UNION ALL
SELECT 'ACC005','CUST05','ISA','OPEN','GBP','2025-04-06',NULL,NULL,4.00,18000.00,'2026-09-28','2026-09-29','2026-09-28 02:00' UNION ALL
SELECT 'ACC006','CUST06','FIXED_1Y','OPEN','GBP','2025-10-01','2026-10-01',NULL,4.90,10000.00,'2026-09-28','9999-12-31','2026-09-28 02:00' UNION ALL
SELECT 'ACC007','CUST02','EASY_ACCESS','DORMANT','GBP','2019-02-11',NULL,NULL,3.50,150.00,'2026-09-28','9999-12-31','2026-09-28 02:00' UNION ALL
SELECT 'ACC008','CUST07','NOTICE_90','FROZEN','GBP','2022-08-30',NULL,NULL,4.10,5000.00,'2026-09-28','9999-12-31','2026-09-28 02:00' UNION ALL
-- Day 2: 29 Sep 2026 (new versions)
SELECT 'ACC003','CUST03','EASY_ACCESS','CLOSED','GBP','2021-06-10',NULL,'2026-09-29',3.50,0.00,'2026-09-29','9999-12-31','2026-09-29 02:00' UNION ALL
SELECT 'ACC005','CUST05','ISA','OPEN','GBP','2025-04-06',NULL,NULL,4.20,18050.00,'2026-09-29','9999-12-31','2026-09-29 02:00';


SELECT
    COUNT(*)                                             AS total_rows,
    SUM(CASE WHEN ValidTo = '9999-12-31' THEN 1 ELSE 0 END) AS current_rows
FROM curate.SavingsAccount;



CREATE PROCEDURE pres.usp_Load_DimSavingsAccount
AS
BEGIN
    TRUNCATE TABLE pres.DimSavingsAccount;

    INSERT INTO pres.DimSavingsAccount
    (AccountNumber, CustomerID, ProductCode, AccountStatus, Currency,
     AccountOpenDate, AccountMaturityDate, AccountCloseDate,
     ValidFrom, ValidTo, IsCurrent)
    SELECT
        AccountNumber, CustomerID, ProductCode, AccountStatus, Currency,
        AccountOpenDate, AccountMaturityDate, AccountCloseDate,
        ValidFrom,
        ValidTo,
        CASE WHEN ValidTo = '9999-12-31' THEN 1 ELSE 0 END AS IsCurrent
    FROM curate.SavingsAccount;
END;



EXEC pres.usp_Load_DimSavingsAccount;



SELECT AccountNumber, AccountStatus, ValidFrom, ValidTo, IsCurrent, SavingsAccountSK
FROM pres.DimSavingsAccount
ORDER BY AccountNumber, ValidFrom;


CREATE PROCEDURE pres.usp_Load_FactSavingsAccount
AS
BEGIN
    TRUNCATE TABLE pres.FactSavingsAccount;

    INSERT INTO pres.FactSavingsAccount
    (SavingsAccountSK, AccountNumber, DateSK, LoadDate, Balance, InterestRate)
    SELECT
        d.SavingsAccountSK,
        c.AccountNumber,
        CONVERT(INT, CONVERT(VARCHAR(8), c.ValidFrom, 112)) AS DateSK,   -- 20260928
        CAST(c.ValidFrom AS DATE)                           AS LoadDate,
        c.Balance,
        c.InterestRate
    FROM curate.SavingsAccount c
    JOIN pres.DimSavingsAccount d
      ON  d.AccountNumber = c.AccountNumber
      AND d.ValidFrom     = c.ValidFrom;
END;


EXEC pres.usp_Load_FactSavingsAccount;



SELECT f.AccountNumber, f.LoadDate, f.DateSK, f.Balance, f.InterestRate,
       d.AccountStatus, d.IsCurrent
FROM pres.FactSavingsAccount f
JOIN pres.DimSavingsAccount d ON d.SavingsAccountSK = f.SavingsAccountSK
ORDER BY f.AccountNumber, f.LoadDate;