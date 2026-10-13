# Savings Account – Data Definitions

## Overview
Savings account data is loaded daily from the core banking system into the
Curate layer (curate.SavingsAccount), then split into Presentation:
- pres.DimSavingsAccount – descriptive account details, SCD Type 2 history
- pres.FactSavingsAccount – daily balance and interest rate per account version

## Column definitions

| Column | Meaning | Type | Mandatory | Business rules |
|---|---|---|---|---|
| AccountNumber | Unique savings account number | varchar(20) | Yes | Unique per account version |
| CustomerID | Customer who owns the account | varchar(20) | Yes | One customer can hold several accounts |
| ProductCode | Savings product type | varchar(20) | Yes | Allowed values: EASY_ACCESS, FIXED_1Y, NOTICE_90, ISA |
| AccountStatus | Current status of the account | varchar(10) | Yes | Allowed values: OPEN, CLOSED, DORMANT, FROZEN |
| Currency | Account currency | char(3) | Yes | Always GBP |
| AccountOpenDate | Date the account was opened | date | Yes | – |
| AccountMaturityDate | Date a fixed-term account matures | date | No | Mandatory when ProductCode = FIXED_1Y |
| AccountCloseDate | Date the account was closed | date | No | Mandatory when AccountStatus = CLOSED |
| InterestRate | Annual interest rate (%) | decimal(5,2) | Yes | – |
| Balance | Account balance in GBP | decimal(18,2) | Yes | Must be 0.00 when AccountStatus = CLOSED |

## Product notes
- EASY_ACCESS: withdraw any time, variable rate
- FIXED_1Y: fixed rate for one year, no withdrawals before maturity
- NOTICE_90: 90 days' notice required before withdrawal
- ISA: tax-free savings, annual deposit limit applies

## Load process
- Full load in DEV and TEST; incremental load in STAGE and PROD.
- Curate keeps history using ValidFrom and ValidTo (9999-12-31 = current version).
- DimSavingsAccount adds IsCurrent (1 = current version).
- FactSavingsAccount LoadDate is taken from Curate ValidFrom; DateSK is the same date as yyyymmdd.


## DimSavingsAccount columns

| Column | Data type | Description |
|---|---|---|
| SavingsAccountSK | int | Unique key |
| AccountNumber | varchar | SavingsAccount.AccountNumber |
| CustomerID | varchar | SavingsAccount.CustomerID |
| ProductCode | varchar | SavingsAccount.ProductCode |
| AccountStatus | varchar | SavingsAccount.AccountStatus |
| Currency | char | SavingsAccount.Currency |
| AccountOpenDate | date | SavingsAccount.AccountOpenDate |
| AccountMaturityDate | date | SavingsAccount.AccountMaturityDate |
| AccountCloseDate | date | SavingsAccount.AccountCloseDate |

## FactSavingsAccount columns

| Column | Data type | Description |
|---|---|---|
| SavingsAccountSK | int | Unique key of DimSavingsAccount |
| AccountNumber | varchar | SavingsAccount.AccountNumber |
| DateSK | int | SavingsAccount.ValidFrom as yyyymmdd |
| LoadDate | date | SavingsAccount.ValidFrom |
| Balance | decimal | SavingsAccount.Balance |
| InterestRate | decimal | SavingsAccount.InterestRate |