DECLARE @next BIGINT;

SELECT @next = ISNULL(MAX(product_id), 0) + 1
FROM dbo.product_tracking WITH (HOLDLOCK, TABLOCKX);

-- Create or restart the sequence to @next
IF NOT EXISTS (
    SELECT 1 FROM sys.sequences
    WHERE name = N'product_id_seq' AND schema_id = SCHEMA_ID(N'dbo')
)
BEGIN
    DECLARE @sql_create NVARCHAR(MAX) =
        N'CREATE SEQUENCE dbo.product_id_seq AS BIGINT START WITH ' +
        CONVERT(NVARCHAR(50), @next) + N' INCREMENT BY 1;';
    EXEC(@sql_create);
END
ELSE
BEGIN
    DECLARE @sql_alter NVARCHAR(MAX) =
        N'ALTER SEQUENCE dbo.product_id_seq RESTART WITH ' +
        CONVERT(NVARCHAR(50), @next) + N';';
    EXEC(@sql_alter);
END;
-- Ensure the column auto-fills from the sequence when omitted
IF NOT EXISTS (
    SELECT 1
    FROM sys.default_constraints dc
    JOIN sys.columns c
      ON c.object_id = dc.parent_object_id AND c.column_id = dc.parent_column_id
    WHERE dc.parent_object_id = OBJECT_ID(N'dbo.product_tracking')
      AND c.name = N'product_id'
)
BEGIN
    ALTER TABLE dbo.product_tracking
    ADD CONSTRAINT DF_product_tracking_product_id
        DEFAULT (NEXT VALUE FOR dbo.product_id_seq) FOR product_id;
END