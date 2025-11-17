
BEGIN TRY
  BEGIN TRAN;

  /* 0) baseline: staging row count */
  SELECT COUNT(*) AS staging_rows FROM dbo.stg_filament_excel_data;

  /* 1) fallback user + mapping table */
  DECLARE @fallback_user_id INT = (SELECT TOP 1 id FROM dbo.users ORDER BY id);
  IF @fallback_user_id IS NULL
    THROW 50010, 'No users present; seed users before loading filaments.', 1;

  IF OBJECT_ID('dbo.legacy_name_to_user','U') IS NULL
  BEGIN
    CREATE TABLE dbo.legacy_name_to_user(
      legacy_name NVARCHAR(200) PRIMARY KEY,
      user_id INT NOT NULL
        CONSTRAINT fk_legacy_map_user REFERENCES dbo.users(id)
    );
  END

  /* 2) ensure shelves exist as storage_locations */
  MERGE dbo.storage_locations AS tgt
  USING (
    SELECT DISTINCT NULLIF(LTRIM(RTRIM(shelf)),'') AS location_name
    FROM dbo.stg_filament_excel_data
  ) AS src
    ON tgt.location_name = src.location_name
  WHEN NOT MATCHED AND src.location_name IS NOT NULL THEN
    INSERT (location_name, location_type, description, is_active)
    VALUES (src.location_name, 'Shelf', 'Imported from legacy filaments', 1);

  IF NOT EXISTS (SELECT 1 FROM dbo.storage_locations WHERE location_name = 'Unassigned')
  BEGIN
    INSERT dbo.storage_locations(location_name, location_type, description, is_active)
    VALUES ('Unassigned', 'Virtual', 'Fallback for missing shelf', 1);
  END
  DECLARE @unassigned_loc_id INT = (SELECT TOP 1 id FROM dbo.storage_locations WHERE location_name='Unassigned');

  /* 3) build base + resolved and MATERIALIZE into temp table for inspection */
  IF OBJECT_ID('tempdb..#resolved','U') IS NOT NULL DROP TABLE #resolved;
  CREATE TABLE #resolved (
    serial_number NVARCHAR(200) NOT NULL,
    lot_number    NVARCHAR(200) NULL,
    location_id   INT NOT NULL,
    weight_grams  DECIMAL(10,2) NULL,
    received_at   DATETIME2 NOT NULL,
    received_by   INT NOT NULL,
    qc_result     NVARCHAR(10) NOT NULL
  );

  ;WITH base AS (
    SELECT
      /* These names MUST match your staging headers */
      NULLIF(LTRIM(RTRIM(CAST(filament_id AS NVARCHAR(200)))),'')   AS serial_number,
      NULLIF(LTRIM(RTRIM(CAST(filament    AS NVARCHAR(200)))),'')   AS lot_number,
      NULLIF(LTRIM(RTRIM(CAST(shelf       AS NVARCHAR(200)))),'')   AS shelf_name,
      NULLIF(LTRIM(RTRIM(CAST(vsc_operator AS NVARCHAR(200)))),'')  AS operator_legacy,

      TRY_CONVERT(decimal(10,2), REPLACE(CAST(weight_fl AS NVARCHAR(100)), ',', '.')) AS weight_grams,

      COALESCE(
        TRY_CONVERT(datetime2, vsc_date, 104),
        TRY_CONVERT(datetime2, vsc_date)
      ) AS received_at,

      COALESCE(CAST(vs_check AS NVARCHAR(100)),'') AS vs_check
    FROM dbo.stg_filament_excel_data
  ),
norm AS (
  SELECT
    b.serial_number,
    b.lot_number,
    COALESCE(loc.id, @unassigned_loc_id) AS location_id,
    COALESCE(b.weight_grams, 0.00)       AS weight_grams,   -- <— default
    COALESCE(b.received_at, SYSUTCDATETIME()) AS received_at,
    COALESCE(map.user_id, @fallback_user_id)  AS received_by,
    CASE
      WHEN UPPER(LTRIM(RTRIM(b.vs_check))) IN (N'FAIL', N'FAILED', N'NO', N'NEIN', N'N', N'FALSE', N'0', N'REJECT', N'REJECTED')
        THEN N'FAIL'
      WHEN UPPER(LTRIM(RTRIM(b.vs_check))) IN (N'OK', N'PASS', N'PASSED', N'GOOD', N'ACCEPT', N'ACCEPTED', N'JA', N'YES', N'Y', N'TRUE', N'1')
        THEN N'PASS'
      ELSE N'PASS'
    END AS qc_result
  FROM base b
  LEFT JOIN dbo.storage_locations loc
    ON loc.location_name = b.shelf_name
  LEFT JOIN dbo.legacy_name_to_user map
    ON map.legacy_name = b.operator_legacy
  WHERE b.serial_number IS NOT NULL
)
  INSERT INTO #resolved(serial_number, lot_number, location_id, weight_grams, received_at, received_by, qc_result)
  SELECT serial_number, lot_number, location_id, weight_grams, received_at, received_by, qc_result
  FROM norm;

  /* Show what we resolved before touching live tables */
  SELECT COUNT(*) AS resolved_rows FROM #resolved;
  SELECT TOP 10 * FROM #resolved ORDER BY received_at DESC;

  /* 4) MERGE with output to see action taken */
  IF OBJECT_ID('tempdb..#merge_out','U') IS NOT NULL DROP TABLE #merge_out;
  CREATE TABLE #merge_out(action NVARCHAR(10));

  MERGE dbo.filaments AS tgt
  USING (
    SELECT DISTINCT
      serial_number, lot_number, location_id, weight_grams, received_at, received_by, qc_result
    FROM #resolved
  ) AS src
    ON tgt.serial_number = src.serial_number
  WHEN MATCHED THEN
  UPDATE SET
    tgt.lot_number   = src.lot_number,
    tgt.location_id  = src.location_id,
    tgt.weight_grams = COALESCE(src.weight_grams, tgt.weight_grams, 0.00), -- <—
    tgt.received_at  = COALESCE(src.received_at, tgt.received_at),
    tgt.received_by  = src.received_by,
    tgt.qc_result    = src.qc_result
  WHEN NOT MATCHED THEN
    INSERT (serial_number, lot_number, location_id, weight_grams, received_at, received_by, qc_result)
    VALUES (src.serial_number, src.lot_number, src.location_id, src.weight_grams, src.received_at, src.received_by, src.qc_result)
  OUTPUT $action INTO #merge_out(action);

  /* 5) Report results */
  SELECT
    SUM(CASE WHEN action = 'INSERT' THEN 1 ELSE 0 END) AS inserted,
    SUM(CASE WHEN action = 'UPDATE' THEN 1 ELSE 0 END) AS updated
  FROM #merge_out;

  SELECT COUNT(*) AS filaments_total_after FROM dbo.filaments;

  COMMIT TRAN;
END TRY
BEGIN CATCH
  IF @@TRANCOUNT > 0 ROLLBACK TRAN;
  THROW;
END CATCH;