COPY INTO dq.data_dictionary
FROM 'https://dqsanavini.dfs.core.windows.net/dqcontainer/Dictionary/DimSavingsAccount.csv'
WITH
(
    FILE_TYPE  = 'CSV',
    FIRSTROW   = 2,                           -- skip the header row
    FIELDQUOTE = '"',                         -- handles commas inside quoted fields
    ENCODING   = 'UTF8',
    CREDENTIAL = (IDENTITY = 'Managed Identity')
);



SELECT table_name, COUNT(*) AS column_rows
FROM dq.data_dictionary
GROUP BY table_name;

SELECT column_name, expected_values, documented_rules
FROM dq.data_dictionary
WHERE column_name IN ('AccountStatus', 'Currency');


CREATE TABLE dq.rule_catalog
(
    rule_id          VARCHAR(20)     NOT NULL,  -- e.g. R001
    table_name       VARCHAR(100)    NOT NULL,
    column_name      VARCHAR(100)    NULL,      -- NULL for table-level rules
    description      VARCHAR(1000)   NOT NULL,  -- plain-English rule
    category         VARCHAR(50)     NULL,      -- e.g. Temporal & SCD, Domain & format
    severity         VARCHAR(20)     NULL,      -- Critical / High / Warning
    origin           VARCHAR(20)     NULL,      -- Documented / Inferred
    rule_sql         VARCHAR(4000)   NOT NULL,  -- query that returns FAILING rows
    status           VARCHAR(20)     NOT NULL,  -- Proposed / Approved / Rejected
    created_at       DATETIME2       NOT NULL
)
WITH
(
    DISTRIBUTION = ROUND_ROBIN,
    HEAP
);


SELECT COLUMN_NAME
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'dq' AND TABLE_NAME = 'rule_catalog';


SELECT STRING_AGG(
    CAST(CONCAT_WS(' | ', column_name, business_meaning, data_type, mandatory,
               expected_values, documented_rules, inferred_rules,
               is_business_key, is_metadata) AS VARCHAR(MAX)),
    CHAR(10)) AS dictionary_rows
FROM dq.data_dictionary
WHERE table_name LIKE '%DimSavingsAccount%';



SELECT STRING_AGG(
    CAST(CONCAT_WS(' | ', column_name, business_meaning, data_type, mandatory,
               expected_values, documented_rules, inferred_rules,
               is_business_key, is_metadata) AS VARCHAR(MAX)),
    CHAR(10)) AS dictionary_rows
FROM dq.data_dictionary
WHERE table_name LIKE '%curate%SavingsAccount%';

-- DELETE FROM dq.data_dictionary WHERE table_name LIKE '%DimSavingsAccount%';


   -- use the exact value from step 1



--    DELETE FROM dq.rule_catalog WHERE rule_id LIKE 'DIM-%';