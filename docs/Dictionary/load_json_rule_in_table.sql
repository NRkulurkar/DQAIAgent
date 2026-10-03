DECLARE @prefix VARCHAR(10)  = 'DIM-';          -- DIM- / FACT- / CUR-
DECLARE @json   NVARCHAR(MAX) = N'[
  {
    "rule_id": "R001",
    "table_name": "pres.DimSavingsAccount",
    "column_name": "SavingsAccountSK",
    "description": "Surrogate key SavingsAccountSK must not be null and must be unique per row.",
    "category": "Completeness",
    "severity": "Critical",
    "origin": "Documented",
    "rule_sql": "SELECT * FROM pres.DimSavingsAccount WHERE SavingsAccountSK IS NULL OR SavingsAccountSK IN (SELECT SavingsAccountSK FROM pres.DimSavingsAccount GROUP BY SavingsAccountSK HAVING COUNT(*)>1)"
  },
  {
    "rule_id": "R002",
    "table_name": "pres.DimSavingsAccount",
    "column_name": "AccountNumber",
    "description": "AccountNumber is mandatory and must not be null or empty.",
    "category": "Completeness",
    "severity": "Critical",
    "origin": "Documented",
    "rule_sql": "SELECT * FROM pres.DimSavingsAccount WHERE AccountNumber IS NULL OR LEN(AccountNumber)=0"
  },
  {
    "rule_id": "R003",
    "table_name": "pres.DimSavingsAccount",
    "column_name": "ProductCode",
    "description": "ProductCode is mandatory and must be one of the allowed values (EASY_ACCESS, FIXED_1Y, NOTICE_90, ISA).",
    "category": "Domain & format",
    "severity": "High",
    "origin": "Documented",
    "rule_sql": "SELECT * FROM pres.DimSavingsAccount WHERE ProductCode IS NULL OR ProductCode NOT IN (''EASY_ACCESS'',''FIXED_1Y'',''NOTICE_90'',''ISA'')"
  },
  {
    "rule_id": "R004",
    "table_name": "pres.DimSavingsAccount",
    "column_name": "AccountStatus",
    "description": "AccountStatus is mandatory and must be one of the allowed values (OPEN, CLOSED, DORMANT, FROZEN).",
    "category": "Domain & format",
    "severity": "High",
    "origin": "Documented",
    "rule_sql": "SELECT * FROM pres.DimSavingsAccount WHERE AccountStatus IS NULL OR AccountStatus NOT IN (''OPEN'',''CLOSED'',''DORMANT'',''FROZEN'')"
  },
  {
    "rule_id": "R005",
    "table_name": "pres.DimSavingsAccount",
    "column_name": "Currency",
    "description": "Currency is mandatory and must equal ''GBP'' and be 3 characters.",
    "category": "Domain & format",
    "severity": "High",
    "origin": "Documented",
    "rule_sql": "SELECT * FROM pres.DimSavingsAccount WHERE Currency IS NULL OR LEN(Currency)<>3 OR Currency<>''GBP''"
  },
  {
    "rule_id": "R006",
    "table_name": "pres.DimSavingsAccount",
    "column_name": "AccountOpenDate",
    "description": "AccountOpenDate is mandatory and must be <= today and not after AccountCloseDate when AccountCloseDate is present; must be earlier than AccountMaturityDate when AccountMaturityDate is present.",
    "category": "Temporal & SCD",
    "severity": "High",
    "origin": "Documented",
    "rule_sql": "SELECT * FROM pres.DimSavingsAccount WHERE AccountOpenDate IS NULL OR AccountOpenDate>GETDATE() OR (AccountCloseDate IS NOT NULL AND AccountOpenDate>AccountCloseDate) OR (AccountMaturityDate IS NOT NULL AND AccountOpenDate>=AccountMaturityDate)"
  },
  {
    "rule_id": "R007",
    "table_name": "pres.DimSavingsAccount",
    "column_name": "AccountMaturityDate,ProductCode",
    "description": "When ProductCode = ''FIXED_1Y'', AccountMaturityDate must be populated; if AccountMaturityDate is present it must be greater than AccountOpenDate.",
    "category": "Conditional business rule",
    "severity": "High",
    "origin": "Documented",
    "rule_sql": "SELECT * FROM pres.DimSavingsAccount WHERE (ProductCode=''FIXED_1Y'' AND AccountMaturityDate IS NULL) OR (AccountMaturityDate IS NOT NULL AND AccountMaturityDate<=AccountOpenDate)"
  },
  {
    "rule_id": "R008",
    "table_name": "pres.DimSavingsAccount",
    "column_name": "AccountCloseDate,AccountStatus,AccountOpenDate",
    "description": "When AccountStatus = ''CLOSED'', AccountCloseDate must be populated; when AccountCloseDate is populated it must be >= AccountOpenDate and <= today.",
    "category": "Conditional business rule",
    "severity": "High",
    "origin": "Documented",
    "rule_sql": "SELECT * FROM pres.DimSavingsAccount WHERE (AccountStatus=''CLOSED'' AND AccountCloseDate IS NULL) OR (AccountCloseDate IS NOT NULL AND (AccountCloseDate<AccountOpenDate OR AccountCloseDate>GETDATE()))"
  },
  {
    "rule_id": "R009",
    "table_name": "pres.DimSavingsAccount",
    "column_name": "ValidFrom,ValidTo",
    "description": "ValidFrom and ValidTo must be non-null and ValidFrom < ValidTo.",
    "category": "Temporal & SCD",
    "severity": "Critical",
    "origin": "Documented",
    "rule_sql": "SELECT * FROM pres.DimSavingsAccount WHERE ValidFrom IS NULL OR ValidTo IS NULL OR ValidFrom>=ValidTo"
  },
  {
    "rule_id": "R010",
    "table_name": "pres.DimSavingsAccount",
    "column_name": "AccountNumber,ValidFrom",
    "description": "Business key (AccountNumber) + ValidFrom must be unique (no duplicate versions with same effective start).",
    "category": "Business-key duplicates",
    "severity": "Critical",
    "origin": "Inferred",
    "rule_sql": "SELECT d.* FROM pres.DimSavingsAccount d JOIN (SELECT AccountNumber,ValidFrom FROM pres.DimSavingsAccount GROUP BY AccountNumber,ValidFrom HAVING COUNT(*)>1) dup ON d.AccountNumber=dup.AccountNumber AND d.ValidFrom=dup.ValidFrom"
  },
  {
    "rule_id": "R011",
    "table_name": "pres.DimSavingsAccount",
    "column_name": "AccountNumber,IsCurrent",
    "description": "Exactly one row per AccountNumber must have IsCurrent = 1.",
    "category": "Temporal & SCD",
    "severity": "High",
    "origin": "Documented",
    "rule_sql": "SELECT * FROM pres.DimSavingsAccount WHERE AccountNumber IN (SELECT AccountNumber FROM pres.DimSavingsAccount GROUP BY AccountNumber HAVING SUM(CASE WHEN IsCurrent=1 THEN 1 ELSE 0 END)<>1)"
  },
  {
    "rule_id": "R012",
    "table_name": "pres.DimSavingsAccount",
    "column_name": "IsCurrent,ValidTo",
    "description": "If IsCurrent = 1 then ValidTo must equal ''9999-12-31''.",
    "category": "Temporal & SCD",
    "severity": "High",
    "origin": "Documented",
    "rule_sql": "SELECT * FROM pres.DimSavingsAccount WHERE IsCurrent=1 AND CAST(ValidTo AS DATE)<>CAST(''9999-12-31'' AS DATE)"
  },
  {
    "rule_id": "R013",
    "table_name": "pres.DimSavingsAccount",
    "column_name": "AccountNumber,ValidFrom,ValidTo",
    "description": "SCD ranges for the same AccountNumber must not overlap: no two rows for same AccountNumber have overlapping [ValidFrom, ValidTo).",
    "category": "Temporal & SCD",
    "severity": "High",
    "origin": "Documented",
    "rule_sql": "SELECT a.* FROM pres.DimSavingsAccount a JOIN pres.DimSavingsAccount b ON a.AccountNumber=b.AccountNumber AND a.SavingsAccountSK<>b.SavingsAccountSK WHERE a.ValidFrom< b.ValidTo AND b.ValidFrom< a.ValidTo"
  },
  {
    "rule_id": "R014",
    "table_name": "pres.DimSavingsAccount",
    "column_name": "CustomerID",
    "description": "CustomerID is mandatory and must reference an existing customer in pres.DimParty.",
    "category": "Referential integrity",
    "severity": "High",
    "origin": "Inferred",
    "rule_sql": "SELECT d.* FROM pres.DimSavingsAccount d LEFT JOIN pres.DimParty p ON d.CustomerID=p.CustomerID WHERE d.CustomerID IS NULL OR p.CustomerID IS NULL"
  },
  {
    "rule_id": "R015",
    "table_name": "pres.DimSavingsAccount",
    "column_name": "AccountStatus,AccountCloseDate",
    "description": "If AccountStatus <> ''CLOSED'' then AccountCloseDate should normally be NULL (flag suspicious non-null close date for active accounts).",
    "category": "Conditional business rule",
    "severity": "Warning",
    "origin": "Inferred",
    "rule_sql": "SELECT * FROM pres.DimSavingsAccount WHERE AccountStatus<>''CLOSED'' AND AccountCloseDate IS NOT NULL"
  },
  {
    "rule_id": "R016",
    "table_name": "pres.DimSavingsAccount",
    "column_name": "AccountNumber,AccountStatus",
    "description": "Natural key AccountNumber should be unique per active business account across SCD2 versions (i.e., business key exists across versions but surrogate rows may repeat AccountNumber — flag if there are zero rows for an AccountNumber marked IsCurrent=1).",
    "category": "Business-key duplicates",
    "severity": "Warning",
    "origin": "Inferred",
    "rule_sql": "SELECT * FROM pres.DimSavingsAccount WHERE AccountNumber IN (SELECT AccountNumber FROM pres.DimSavingsAccount GROUP BY AccountNumber HAVING SUM(CASE WHEN IsCurrent=1 THEN 1 ELSE 0 END)=0)"
  }
]'

INSERT INTO dq.rule_catalog
(rule_id, table_name, column_name, description, category, severity, origin, rule_sql, status, created_at)
SELECT
    @prefix + rule_id,
    table_name, column_name, description, category, severity, origin, rule_sql,
    'Proposed',
    GETDATE()
FROM OPENJSON(@json)
WITH (
    rule_id      VARCHAR(20)    '$.rule_id',
    table_name   VARCHAR(100)   '$.table_name',
    column_name  VARCHAR(100)   '$.column_name',
    description  VARCHAR(1000)  '$.description',
    category     VARCHAR(50)    '$.category',
    severity     VARCHAR(20)    '$.severity',
    origin       VARCHAR(20)    '$.origin',
    rule_sql     VARCHAR(4000)  '$.rule_sql'
);


-- SELECT * FROM dq.rule_catalog ORDER BY RULE_ID;