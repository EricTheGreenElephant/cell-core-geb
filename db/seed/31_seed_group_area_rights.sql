SET NOCOUNT ON;

-- Expect sqlcmd -v variables for each group OID:
--   -v PROD_READ_OID="..."   -v PROD_WRITE_OID="..."
--   -v LOG_READ_OID="..."    -v LOG_WRITE_OID="..."
--   -v QM_READ_OID="..."     -v QM_WRITE_OID="..."
--   -v SALES_READ_OID="..."  -v SALES_WRITE_OID="..."
--   -v GLOBAL_ADMIN_OID="..."   (optional)

DECLARE @ProdRead   UNIQUEIDENTIFIER = TRY_CONVERT(UNIQUEIDENTIFIER, N'$(PROD_READ_OID)');
DECLARE @ProdWrite  UNIQUEIDENTIFIER = TRY_CONVERT(UNIQUEIDENTIFIER, N'$(PROD_WRITE_OID)');
DECLARE @LogRead    UNIQUEIDENTIFIER = TRY_CONVERT(UNIQUEIDENTIFIER, N'$(LOG_READ_OID)');
DECLARE @LogWrite   UNIQUEIDENTIFIER = TRY_CONVERT(UNIQUEIDENTIFIER, N'$(LOG_WRITE_OID)');
DECLARE @QMRead     UNIQUEIDENTIFIER = TRY_CONVERT(UNIQUEIDENTIFIER, N'$(QM_READ_OID)');
DECLARE @QMWrite    UNIQUEIDENTIFIER = TRY_CONVERT(UNIQUEIDENTIFIER, N'$(QM_WRITE_OID)');
DECLARE @SalesRead  UNIQUEIDENTIFIER = TRY_CONVERT(UNIQUEIDENTIFIER, N'$(SALES_READ_OID)');
DECLARE @SalesWrite UNIQUEIDENTIFIER = TRY_CONVERT(UNIQUEIDENTIFIER, N'$(SALES_WRITE_OID)');
DECLARE @GlobalAdmin UNIQUEIDENTIFIER = TRY_CONVERT(UNIQUEIDENTIFIER, N'$(GLOBAL_ADMIN_OID)');

IF @ProdRead IS NULL AND @ProdWrite IS NULL AND
   @LogRead IS NULL AND @LogWrite IS NULL AND
   @QMRead IS NULL AND @QMWrite IS NULL AND
   @SalesRead IS NULL AND @SalesWrite IS NULL AND
   @GlobalAdmin IS NULL
BEGIN
    PRINT 'Group seed: no OIDs provided, skipping.';
    RETURN;
END;

-- Resolve application area IDs once
DECLARE @Area_Production INT = (SELECT id FROM dbo.application_areas WHERE area_name = N'Production');
DECLARE @Area_Logistics  INT = (SELECT id FROM dbo.application_areas WHERE area_name = N'Logistics');
DECLARE @Area_QM         INT = (SELECT id FROM dbo.application_areas WHERE area_name = N'Quality Management');
DECLARE @Area_Sales      INT = (SELECT id FROM dbo.application_areas WHERE area_name = N'Sales');
DECLARE @Area_Admin      INT = (SELECT id FROM dbo.application_areas WHERE area_name = N'Admin');

;WITH all_groups AS (
    SELECT * FROM (VALUES
        (@ProdRead,   @Area_Production, N'Read'),
        (@ProdWrite,  @Area_Production, N'Write'),
        (@LogRead,    @Area_Logistics,  N'Read'),
        (@LogWrite,   @Area_Logistics,  N'Write'),
        (@QMRead,     @Area_QM,         N'Read'),
        (@QMWrite,    @Area_QM,         N'Write'),
        (@SalesRead,  @Area_Sales,      N'Read'),
        (@SalesWrite, @Area_Sales,      N'Write')
    ) AS v(group_oid, area_id, access_level)
),
src AS (
    SELECT group_oid, area_id, access_level
    FROM all_groups
    WHERE group_oid IS NOT NULL         -- skip any groups you didn’t provide
      AND area_id IS NOT NULL           -- skip if an area name wasn’t found
)
MERGE dbo.group_area_rights AS tgt
USING src
  ON  tgt.group_oid = src.group_oid
  AND tgt.area_id   = src.area_id
WHEN MATCHED AND tgt.access_level <> src.access_level
  THEN UPDATE SET tgt.access_level = src.access_level
WHEN NOT MATCHED BY TARGET
  THEN INSERT (group_oid, area_id, access_level)
       VALUES (src.group_oid, src.area_id, src.access_level);

-- Optional: Global Admin group gets Admin on all areas
IF @GlobalAdmin IS NOT NULL
BEGIN
    ;WITH src_admin AS (
        SELECT @GlobalAdmin AS group_oid, a.id AS area_id, N'Admin' AS access_level
        FROM dbo.application_areas a
    )
    MERGE dbo.group_area_rights AS tgt
    USING src_admin
      ON  tgt.group_oid = src_admin.group_oid
      AND tgt.area_id   = src_admin.area_id
    WHEN MATCHED AND tgt.access_level <> src_admin.access_level
      THEN UPDATE SET tgt.access_level = src_admin.access_level
    WHEN NOT MATCHED BY TARGET
      THEN INSERT (group_oid, area_id, access_level)
           VALUES (src_admin.group_oid, src_admin.area_id, src_admin.access_level);
END;
