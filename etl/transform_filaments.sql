BEGIN TRY
  BEGIN TRAN;

  /* -------- 0) Preconditions -------- */
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

  /* -------- 1) Upsert storage locations from `shelf` -------- */
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

  /* -------- 2) Build normalized source -------- */
  ;WITH base AS (
    SELECT
      /* sheet columns -> raw fields (trim & cast defensively) */
      NULLIF(LTRIM(RTRIM(CAST(filament_id  AS NVARCHAR(200)))),'') AS serial_number,
      NULLIF(LTRIM(RTRIM(CAST(filament     AS NVARCHAR(200)))),'') AS lot_number,
      NULLIF(LTRIM(RTRIM(CAST(shelf        AS NVARCHAR(200)))),'') AS shelf_name,
      NULLIF(LTRIM(RTRIM(CAST(vsc_operator AS NVARCHAR(200)))),'') AS operator_legacy,
      /* numeric weight: handle comma decimal, blanks -> NULL (we'll default later) */
      TRY_CONVERT(decimal(10,2), REPLACE(CAST(weight_fl AS NVARCHAR(100)), ',', '.')) AS weight_grams,
      /* received date: try dd.mm.yyyy then generic */
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
      COALESCE(b.weight_grams, 0.00)       AS weight_grams,   -- default if missing
      COALESCE(b.received_at, SYSUTCDATETIME()) AS received_at,
      /* resolve operator -> users.id: mapping, else direct match on display_name (case-insensitive), else fallback */
      COALESCE(map.user_id,
               u.id,
               @fallback_user_id) AS received_by,
      /* normalize QC to PASS/FAIL */
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
    LEFT JOIN dbo.users u
      ON u.display_name COLLATE Latin1_General_CI_AI
       = b.operator_legacy COLLATE Latin1_General_CI_AI
    WHERE b.serial_number IS NOT NULL
  )

  /* -------- 3) Upsert into dbo.filaments (idempotent) -------- */
  MERGE dbo.filaments AS tgt
  USING (
    SELECT DISTINCT
      serial_number, lot_number, location_id, weight_grams, received_at, received_by, qc_result
    FROM norm
  ) AS src
    ON tgt.serial_number = src.serial_number
  WHEN MATCHED THEN
    UPDATE SET
      tgt.lot_number   = src.lot_number,
      tgt.location_id  = src.location_id,
      tgt.weight_grams = COALESCE(src.weight_grams, tgt.weight_grams, 0.00),
      tgt.received_at  = COALESCE(src.received_at, tgt.received_at),
      tgt.received_by  = src.received_by,
      tgt.qc_result    = src.qc_result
  WHEN NOT MATCHED THEN
    INSERT (serial_number, lot_number, location_id, weight_grams, received_at, received_by, qc_result)
    VALUES (src.serial_number, src.lot_number, src.location_id, src.weight_grams, src.received_at, src.received_by, src.qc_result);

  COMMIT TRAN;
END TRY
BEGIN CATCH
  IF @@TRANCOUNT > 0 ROLLBACK TRAN;
  THROW;
END CATCH;