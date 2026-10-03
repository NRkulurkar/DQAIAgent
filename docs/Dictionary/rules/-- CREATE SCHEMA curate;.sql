-- CREATE SCHEMA curate;
-- GO
-- CREATE SCHEMA pres;
-- GO
-- CREATE SCHEMA dq;
-- GO

-- SELECT name FROM sys.schemas WHERE name IN ('curate', 'pres', 'dq');




CREATE TABLE curate.SavingsAccount
(
    -- Business columns (from "source")
    AccountNumber        VARCHAR(20)    NOT NULL,  -- business key
    CustomerID           VARCHAR(20)    NOT NULL,
    ProductCode          VARCHAR(20)    NULL,      -- EASY_ACCESS / FIXED_1Y / NOTICE_90 / ISA
    AccountStatus        VARCHAR(10)    NULL,      -- OPEN / CLOSED / DORMANT / FROZEN
    Currency             CHAR(3)        NULL,      -- GBP
    AccountOpenDate      DATE           NULL,
    AccountMaturityDate  DATE           NULL,      -- only for fixed-term products
    AccountCloseDate     DATE           NULL,      -- only when CLOSED
    InterestRate         DECIMAL(5,2)   NULL,      -- e.g. 4.25
    Balance              DECIMAL(18,2)  NULL,

    -- Metadata columns (added by the pipeline)
    ValidFrom            DATETIME2      NOT NULL,
    ValidTo              DATETIME2      NOT NULL,  -- 9999-12-31 for the current version
    LoadTimestamp        DATETIME2      NOT NULL
)
WITH
(
    DISTRIBUTION = ROUND_ROBIN,
    HEAP
);


SELECT COLUMN_NAME, DATA_TYPE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'curate' AND TABLE_NAME = 'SavingsAccount';


CREATE TABLE pres.DimSavingsAccount
(
    SavingsAccountSK     INT IDENTITY(1,1) NOT NULL,  -- surrogate key, one per version
    AccountNumber        VARCHAR(20)    NOT NULL,     -- business key
    CustomerID           VARCHAR(20)    NOT NULL,
    ProductCode          VARCHAR(20)    NULL,
    AccountStatus        VARCHAR(10)    NULL,
    Currency             CHAR(3)        NULL,
    AccountOpenDate      DATE           NULL,
    AccountMaturityDate  DATE           NULL,
    AccountCloseDate     DATE           NULL,

    -- SCD metadata columns
    ValidFrom            DATETIME2      NOT NULL,
    ValidTo              DATETIME2      NOT NULL,     -- 9999-12-31 for the current version
    IsCurrent            BIT            NOT NULL      -- 1 = current version
)
WITH
(
    DISTRIBUTION = ROUND_ROBIN,
    HEAP
);

SELECT COLUMN_NAME, DATA_TYPE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'pres' AND TABLE_NAME = 'DimSavingsAccount';


CREATE TABLE pres.FactSavingsAccount
(
    SavingsAccountSK     INT            NOT NULL,  -- links to pres.DimSavingsAccount
    AccountNumber        VARCHAR(20)    NOT NULL,  -- business key, kept for easy checks
    DateSK               INT            NOT NULL,  -- e.g. 20260930
    LoadDate             DATE           NULL,      -- = ValidFrom from Curate

    -- Measures
    Balance              DECIMAL(18,2)  NULL,
    InterestRate         DECIMAL(5,2)   NULL
)
WITH
(
    DISTRIBUTION = ROUND_ROBIN,
    HEAP
);

SELECT COLUMN_NAME, DATA_TYPE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'pres' AND TABLE_NAME = 'FactSavingsAccount';