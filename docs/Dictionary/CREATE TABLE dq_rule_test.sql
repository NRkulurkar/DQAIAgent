CREATE TABLE dq.rule_test
(
    rule_id         VARCHAR(20)    NOT NULL,
    test_status     VARCHAR(10)    NOT NULL,   -- OK / ERROR
    failed_rows     INT            NULL,       -- rows the rule returned
    error_message   VARCHAR(1000)  NULL,
    tested_at       DATETIME2      NOT NULL
)
WITH (DISTRIBUTION = ROUND_ROBIN, HEAP);