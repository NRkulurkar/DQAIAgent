-- ALTER TABLE dq.rule_catalog ADD reviewed_by VARCHAR(100) NULL;
-- ALTER TABLE dq.rule_catalog ADD reviewed_at DATETIME2 NULL;
-- ALTER TABLE dq.rule_catalog ADD review_note VARCHAR(1000) NULL;

EXEC dq.usp_TestRules;

SELECT table_name, status, COUNT(*) AS rules
FROM dq.rule_catalog
GROUP BY table_name, status
ORDER BY table_name, status;

SELECT table_name, status, COUNT(*) AS rules
FROM dq.rule_catalog
GROUP BY table_name, status
ORDER BY table_name, status;

SELECT rule_id, description, origin
FROM dq.rule_catalog
WHERE table_name = 'pres.FactSavingsAccount' AND status = 'Proposed';

DELETE FROM dq.rule_catalog WHERE table_name = 'pres.FactSavingsAccount' AND status = 'Proposed';

CREATE TABLE dq.rule_generation_log
(
    table_name       VARCHAR(100) NOT NULL,
    dictionary_hash  VARCHAR(64)  NOT NULL,
    generated_at     DATETIME2    NOT NULL
)
WITH (DISTRIBUTION = ROUND_ROBIN, HEAP);

DELETE FROM dq.rule_catalog WHERE table_name = 'pres.FactSavingsAccount' AND status = 'Proposed';
CREATE TABLE dq.run_log
(
    run_id        INT           NOT NULL,   -- 1, 2, 3, ...
    run_mode      VARCHAR(20)   NOT NULL,   -- FULL / INCREMENTAL
    run_date      DATE          NOT NULL,   -- the load date being checked
    started_at    DATETIME2     NOT NULL,
    finished_at   DATETIME2     NULL,
    status        VARCHAR(20)   NOT NULL,   -- Running / Completed / Failed
    rules_run     INT           NULL,
    rules_failed  INT           NULL,
    rules_error   INT           NULL
)
WITH (DISTRIBUTION = ROUND_ROBIN, HEAP);

CREATE TABLE dq.results
(
    run_id         INT            NOT NULL,
    rule_id        VARCHAR(100)   NOT NULL,
    table_name     VARCHAR(100)   NOT NULL,
    category       VARCHAR(50)    NULL,
    severity       VARCHAR(20)    NULL,
    origin         VARCHAR(20)    NULL,
    outcome        VARCHAR(20)    NOT NULL,   -- PASS / FAIL / ERROR
    failed_rows    INT            NULL,
    error_message  VARCHAR(1000)  NULL,
    checked_at     DATETIME2      NOT NULL
)
WITH (DISTRIBUTION = ROUND_ROBIN, HEAP);

SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = 'dq' AND TABLE_NAME IN ('run_log', 'results');



CREATE PROCEDURE dq.usp_RunDailyChecks
    @run_mode VARCHAR(20),
    @run_date DATE
AS
BEGIN
    IF @run_mode IS NULL SET @run_mode = 'FULL';
    IF @run_date IS NULL SET @run_date = CAST(GETDATE() AS DATE);

    -- 1. Start the run
    DECLARE @run_id INT;
    SELECT @run_id = ISNULL(MAX(run_id), 0) + 1 FROM dq.run_log;

    INSERT INTO dq.run_log (run_id, run_mode, run_date, started_at, status)
    SELECT @run_id, @run_mode, @run_date, GETDATE(), 'Running';

    -- 2. Approved rules only
    IF OBJECT_ID('tempdb..#rules') IS NOT NULL DROP TABLE #rules;
    CREATE TABLE #rules WITH (DISTRIBUTION = ROUND_ROBIN) AS
    SELECT ROW_NUMBER() OVER (ORDER BY rule_id) AS rn,
           rule_id, table_name, category, severity, origin, rule_sql
    FROM dq.rule_catalog
    WHERE status = 'Approved';

    DECLARE @i INT = 1, @n INT,
            @rule_id VARCHAR(100), @table VARCHAR(100), @cat VARCHAR(50),
            @sev VARCHAR(20), @org VARCHAR(20), @rule_sql VARCHAR(4000), @sql NVARCHAR(MAX);
    SELECT @n = COUNT(*) FROM #rules;

    -- 3. Run each rule
    WHILE @i <= @n
    BEGIN
        SELECT @rule_id = rule_id, @table = table_name, @cat = category,
               @sev = severity, @org = origin, @rule_sql = rule_sql
        FROM #rules WHERE rn = @i;

        -- Placeholder for later incremental rules
        SET @rule_sql = REPLACE(@rule_sql, '{run_date}', CONVERT(VARCHAR(10), @run_date, 120));

        SET @sql = N'INSERT INTO dq.results (run_id, rule_id, table_name, category, severity, origin, '
                 + N'outcome, failed_rows, error_message, checked_at) '
                 + N'SELECT ' + CAST(@run_id AS NVARCHAR(10)) + N', '
                 + N'''' + @rule_id + N''', ''' + @table + N''', '
                 + N'''' + ISNULL(@cat, '') + N''', ''' + ISNULL(@sev, '') + N''', ''' + ISNULL(@org, '') + N''', '
                 + N'CASE WHEN COUNT(*) = 0 THEN ''PASS'' ELSE ''FAIL'' END, COUNT(*), NULL, GETDATE() '
                 + N'FROM (' + @rule_sql + N') t;';

        BEGIN TRY
            EXEC (@sql);
        END TRY
        BEGIN CATCH
            INSERT INTO dq.results (run_id, rule_id, table_name, category, severity, origin,
                                    outcome, failed_rows, error_message, checked_at)
            SELECT @run_id, @rule_id, @table, @cat, @sev, @org,
                   'ERROR', NULL, LEFT(ERROR_MESSAGE(), 1000), GETDATE();
        END CATCH

        SET @i = @i + 1;
    END

    -- 4. Close the run with totals
    DECLARE @run INT, @failed INT, @errors INT;
    SELECT @run    = COUNT(*) FROM dq.results WHERE run_id = @run_id;
    SELECT @failed = COUNT(*) FROM dq.results WHERE run_id = @run_id AND outcome = 'FAIL';
    SELECT @errors = COUNT(*) FROM dq.results WHERE run_id = @run_id AND outcome = 'ERROR';

    UPDATE dq.run_log
    SET finished_at = GETDATE(), status = 'Completed',
        rules_run = @run, rules_failed = @failed, rules_error = @errors
    WHERE run_id = @run_id;
END;



EXEC dq.usp_RunDailyChecks 'FULL', '2026-09-29';

EXEC dq.usp_RunDailyChecks 'FULL', NULL;

SELECT run_id, run_mode, run_date, status, rules_run, rules_failed, rules_error
FROM dq.run_log ORDER BY run_id DESC;


CREATE TABLE dq.ai_summary
(
    run_id        INT            NOT NULL,
    summary_text  VARCHAR(8000)  NOT NULL,
    created_at    DATETIME2      NOT NULL
)
WITH (DISTRIBUTION = ROUND_ROBIN, HEAP);


SELECT run_id, LEFT(summary_text, 300) AS start_of_report, created_at
FROM dq.ai_summary ORDER BY run_id DESC;