CREATE TABLE dq.data_dictionary
(
    table_name         VARCHAR(100)   NOT NULL,
    column_name        VARCHAR(100)   NOT NULL,
    business_meaning   VARCHAR(1000)  NULL,
    data_type          VARCHAR(50)    NULL,
    mandatory          VARCHAR(10)    NULL,
    expected_values    VARCHAR(1000)  NULL,
    documented_rules   VARCHAR(4000)  NULL,
    inferred_rules     VARCHAR(4000)  NULL,
    is_business_key    VARCHAR(10)    NULL,
    is_metadata        VARCHAR(10)    NULL
)
WITH
(
    DISTRIBUTION = ROUND_ROBIN,
    HEAP
);


SELECT COLUMN_NAME
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'dq' AND TABLE_NAME = 'data_dictionary';