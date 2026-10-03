CREATE PROCEDURE dq.usp_TestRules
AS
BEGIN
    TRUNCATE TABLE dq.rule_test;

    IF OBJECT_ID('tempdb..#rules') IS NOT NULL DROP TABLE #rules;

    CREATE TABLE #rules WITH (DISTRIBUTION = ROUND_ROBIN) AS
    SELECT ROW_NUMBER() OVER (ORDER BY rule_id) AS rn, rule_id, rule_sql
    FROM dq.rule_catalog;

    DECLARE @i INT = 1, @n INT, @rule_id VARCHAR(20), @rule_sql VARCHAR(4000), @sql NVARCHAR(MAX);
    SELECT @n = COUNT(*) FROM #rules;

    WHILE @i <= @n
    BEGIN
        SELECT @rule_id = rule_id, @rule_sql = rule_sql FROM #rules WHERE rn = @i;

        SET @sql = N'INSERT INTO dq.rule_test (rule_id, test_status, failed_rows, error_message, tested_at) '
                 + N'SELECT ''' + @rule_id + N''', ''OK'', COUNT(*), NULL, GETDATE() '
                 + N'FROM (' + @rule_sql + N') t;';

        BEGIN TRY
            EXEC (@sql);
        END TRY
        BEGIN CATCH
            INSERT INTO dq.rule_test (rule_id, test_status, failed_rows, error_message, tested_at)
            SELECT @rule_id, 'ERROR', NULL, LEFT(ERROR_MESSAGE(), 1000), GETDATE();
        END CATCH

        SET @i = @i + 1;
    END
END;

EXEC dq.usp_TestRules;


select * from dq.rule_test


SELECT description, rule_sql
FROM dq.rule_catalog
WHERE rule_id = 'CUR-R004';


SELECT t.rule_id, r.table_name, r.description, t.failed_rows
FROM dq.rule_test t
JOIN dq.rule_catalog r ON r.rule_id = t.rule_id
WHERE t.test_status = 'OK' AND t.failed_rows > 0
ORDER BY r.table_name, t.rule_id;

-- SELECT COUNT(*) AS cur_rules FROM dq.rule_catalog WHERE rule_id LIKE 'CUR-%';

-- SELECT rule_id, error_message
-- FROM dq.rule_test
-- WHERE test_status = 'ERROR';

-- DELETE FROM dq.data_dictionary WHERE table_name IN ('pres.DimSavingsAccount', 'curate.SavingsAccount');

-- DELETE FROM dq.data_dictionary WHERE table_name IN ('pres.DimSavingsAccount');

-- DELETE FROM dq.rule_catalog   WHERE rule_id LIKE 'DIM-%' OR rule_id LIKE 'CUR-%';

-- DELETE FROM dq.rule_catalog   WHERE rule_id LIKE  'CUR-%';



SELECT expected_values, documented_rules
FROM dq.data_dictionary
WHERE table_name = 'curate.SavingsAccount' 
AND column_name = 'AccountStatus';


SELECT rule_id, description FROM dq.rule_catalog
WHERE rule_id LIKE 'DIM-%' AND (description LIKE '%Close%' OR description LIKE '%Maturity%');

SELECT t.rule_id, t.error_message
FROM dq.rule_test t
WHERE t.test_status = 'ERROR';

SELECT column_name, documented_rules
FROM dq.data_dictionary
WHERE table_name = 'pres.DimSavingsAccount'
AND column_name 
IN ('AccountCloseDate', 'AccountMaturityDate');


