BEGIN TRY
  BEGIN TRAN;

  /* -------- 0) Preconditions / fallbacks -------- */
  DECLARE @fallback_user_id INT = (SELECT TOP 1 id FROM dbo.users ORDER BY id);
  IF @fallback_user_id IS NULL
    THROW 50020, 'No users present; seed users before loading filament_mounting.', 1;

  -- Ensure an 'Unassigned' storage location (likely created already by filaments transform)
  IF NOT EXISTS (SELECT 1 FROM dbo.storage_locations WHERE location_name = 'Unassigned')
  BEGIN
    INSERT dbo.storage_locations(location_name, location_type, description, is_active)
    VALUES ('Unassigned', 'Virtual', 'Fallback for missing shelf', 1);
  END
  DECLARE @unassigned_loc_id INT = (SELECT TOP 1 id FROM dbo.storage_locations WHERE location_name = 'Unassigned');

  -- Ensure an 'UNASSIGNED' printer so unmounted rows have a valid printer_id
  IF NOT EXISTS (SELECT 1 FROM dbo.printers WHERE name = 'UNASSIGNED')
  BEGIN
    INSERT dbo.printers(name, location_id, status, is_active)
    VALUES ('UNASSIGNED', @unassigned_loc_id, 'Inactive', 1);
  END
  DECLARE @unassigned_printer_id INT = (SELECT TOP 1 id FROM dbo.printers WHERE name = 'UNASSIGNED');

  /* -------- 1) Resolve source rows from staging -------- */
  IF OBJECT_ID('tempdb..#all_staged_filaments','U') IS NOT NULL DROP TABLE #all_staged_filaments;
  IF OBJECT_ID('tempdb..#fm_resolved','U') IS NOT NULL DROP TABLE #fm_resolved;

  CREATE TABLE #all_staged_filaments (filament_id INT PRIMARY KEY);

  CREATE TABLE #fm_resolved (
    filament_id       INT           NOT NULL,
    printer_id        INT           NOT NULL,
    mounted_by        INT           NOT NULL,
    mounted_at        DATETIME2     NOT NULL,
    unmounted_at      DATETIME2     NULL,
    unmounted_by      INT           NULL,
    remaining_weight  DECIMAL(10,2) NOT NULL,
    status            NVARCHAR(50)  NOT NULL
  );

  ;WITH base AS (
    SELECT
      NULLIF(LTRIM(RTRIM(CAST(s.filament_id AS NVARCHAR(200)))),'') AS serial_number,
      NULLIF(LTRIM(RTRIM(CAST(s.printer_fi AS NVARCHAR(200)))),'')  AS printer_name,
      NULLIF(LTRIM(RTRIM(CAST(s.[usage] AS NVARCHAR(50)))),'')      AS usage_flag,
      TRY_CONVERT(decimal(10,2), REPLACE(CAST(s.weight_fl AS NVARCHAR(100)), ',', '.')) AS weight_grams,
      COALESCE(TRY_CONVERT(datetime2, s.use_date, 104), TRY_CONVERT(datetime2, s.use_date)) AS use_dt
    FROM dbo.stg_filament_excel_data s
  ),
  joined AS (
    SELECT
      f.id                                              AS filament_id,
      COALESCE(p.id, @unassigned_printer_id)            AS printer_id,
      @fallback_user_id                                 AS mounted_by,
      COALESCE(b.use_dt, SYSUTCDATETIME())              AS mounted_at,
      CAST(NULL AS DATETIME2)                           AS unmounted_at,
      CAST(NULL AS INT)                                 AS unmounted_by,
      COALESCE(b.weight_grams, 0.00)                    AS remaining_weight,
      CASE
        WHEN b.printer_name IS NOT NULL THEN N'In Use'   -- currently on a printer
        ELSE N'Unmounted'                                -- was used, now off a printer
      END AS status,
      b.printer_name,
      UPPER(b.usage_flag) AS usage_up
    FROM base b
    JOIN dbo.filaments f
      ON f.serial_number = b.serial_number
    LEFT JOIN dbo.printers p
      ON p.name COLLATE Latin1_General_CI_AI
       = b.printer_name COLLATE Latin1_General_CI_AI
    WHERE b.serial_number IS NOT NULL
      -- KEEP ONLY: currently on a printer OR explicitly used in the past
      AND NOT (
        b.printer_name IS NULL
        AND (b.usage_flag IS NULL OR b.usage_flag = '' OR UPPER(b.usage_flag) = N'NO')
      )
  )
  INSERT INTO #fm_resolved(filament_id, printer_id, mounted_by, mounted_at, unmounted_at, unmounted_by, remaining_weight, status)
  SELECT DISTINCT filament_id, printer_id, mounted_by, mounted_at, unmounted_at, unmounted_by, remaining_weight, status
  FROM joined;

  -- Track ALL staged filaments (so we can delete rows for ineligible ones too)
  INSERT INTO #all_staged_filaments(filament_id)
  SELECT DISTINCT f.id
  FROM dbo.stg_filament_excel_data s
  JOIN dbo.filaments f
    ON f.serial_number = LTRIM(RTRIM(CAST(s.filament_id AS NVARCHAR(200))))
  WHERE s.filament_id IS NOT NULL;

  /* -------- 2) MERGE into dbo.filament_mounting -------- */
  MERGE dbo.filament_mounting AS tgt
  USING #fm_resolved AS src
    ON tgt.filament_id = src.filament_id
  WHEN MATCHED THEN
    UPDATE SET
      tgt.printer_id       = src.printer_id,
      tgt.mounted_by       = src.mounted_by,
      tgt.mounted_at       = COALESCE(src.mounted_at, tgt.mounted_at),
      tgt.unmounted_at     = src.unmounted_at,
      tgt.unmounted_by     = src.unmounted_by,
      tgt.remaining_weight = src.remaining_weight,
      tgt.status           = src.status
  WHEN NOT MATCHED THEN
    INSERT (filament_id, printer_id, mounted_by, mounted_at, unmounted_at, unmounted_by, remaining_weight, status)
    VALUES (src.filament_id, src.printer_id, src.mounted_by, src.mounted_at, src.unmounted_at, src.unmounted_by, src.remaining_weight, src.status)
  -- IMPORTANT: delete rows for filaments from the current staging set that are no longer eligible
  WHEN NOT MATCHED BY SOURCE
       AND tgt.filament_id IN (SELECT filament_id FROM #all_staged_filaments)
    THEN DELETE;

  COMMIT TRAN;
END TRY
BEGIN CATCH
  IF @@TRANCOUNT > 0 ROLLBACK TRAN;
  THROW;
END CATCH;