DECLARE @next BIGINT;

SELECT @next = ISNULL(MAX(filament_id), 0) + 1
FROM dbo.filaments WITH (HOLDLOCK, TABLOCKX);

-- Create or restart the sequence to @next
IF NOT EXISTS (
    SELECT 1 FROM sys.sequences
    WHERE name = N'filament_id_seq' AND schema_id = SCHEMA_ID(N'dbo')
)
BEGIN
    DECLARE @sql_create NVARCHAR(MAX) =
        N'CREATE SEQUENCE dbo.filament_id_seq AS BIGINT START WITH ' +
        CONVERT(NVARCHAR(50), @next) + N' INCREMENT BY 1;';
    EXEC(@sql_create);
END
ELSE
BEGIN
    DECLARE @sql_alter NVARCHAR(MAX) =
        N'ALTER SEQUENCE dbo.filament_id_seq RESTART WITH ' +
        CONVERT(NVARCHAR(50), @next) + N';';
    EXEC(@sql_alter);
END;

-- Ensure the column auto-fills from the sequence when omitted
IF NOT EXISTS (
    SELECT 1
    FROM sys.default_constraints dc
    JOIN sys.columns c
      ON c.object_id = dc.parent_object_id AND c.column_id = dc.parent_column_id
    WHERE dc.parent_object_id = OBJECT_ID(N'dbo.filaments')
      AND c.name = N'filament_id'
)
BEGIN
    ALTER TABLE dbo.filaments
    ADD CONSTRAINT DF_filaments_filament_id
        DEFAULT (NEXT VALUE FOR dbo.filament_id_seq) FOR filament_id;
END