BEGIN TRY
  BEGIN TRAN;

  /* -------- 0) Preconditions / fallbacks -------- */
  DECLARE @fallback_user_id INT = (SELECT TOP 1 id FROM dbo.users ORDER BY id);
  IF @fallback_user_id IS NULL
    THROW 50020, 'No users present; seed users before loading filament_mounting.', 1;

  IF NOT EXISTS (SELECT 1 FROM dbo.storage_locations WHERE location_name = 'Unassigned')
  BEGIN
    INSERT dbo.storage_locations(location_name, location_type, description, is_active)
    VALUES ('Unassigned', 'Virtual', 'Fallback for missing shelf', 1);
  END
  DECLARE @unassigned_loc_id INT = (SELECT TOP 1 id FROM dbo.storage_locations WHERE location_name = 'Unassigned');

  IF NOT EXISTS (SELECT 1 FROM dbo.printers WHERE name = 'UNASSIGNED')
  BEGIN
    INSERT dbo.printers(name, location_id, status, is_active)
    VALUES ('UNASSIGNED', @unassigned_loc_id, 'Inactive', 1);
  END
  DECLARE @unassigned_printer_id INT = (SELECT TOP 1 id FROM dbo.printers WHERE name = 'UNASSIGNED');

  /* -------- 1) Temp tables -------- */
  IF OBJECT_ID('tempdb..#all_staged_filaments','U') IS NOT NULL DROP TABLE #all_staged_filaments;
  IF OBJECT_ID('tempdb..#fm_resolved','U') IS NOT NULL DROP TABLE #fm_resolved;
  IF OBJECT_ID('tempdb..#fallback_printer','U') IS NOT NULL DROP TABLE #fallback_printer;

  CREATE TABLE #all_staged_filaments (filament_id INT PRIMARY KEY);

  CREATE TABLE #fm_resolved (
    filament_id       INT           NOT NULL PRIMARY KEY,
    printer_id        INT           NOT NULL,
    mounted_by        INT           NOT NULL,
    mounted_at        DATETIME2     NOT NULL,
    unmounted_at      DATETIME2     NULL,
    unmounted_by      INT           NULL,
    remaining_weight  DECIMAL(10,2) NOT NULL,
    status            NVARCHAR(50)  NOT NULL
  );

  /* -------- 2) Fallback printer per filament from stg_excel_data -------- */
  ;WITH se_base AS (
    SELECT
      NULLIF(LTRIM(RTRIM(CAST(s.filament_id AS NVARCHAR(200)))),'') AS filament_serial,
      NULLIF(LTRIM(RTRIM(CAST(s.printer     AS NVARCHAR(200)))),'') AS printer_name,
      COALESCE(
        TRY_CONVERT(datetime2, s.date_harvest, 101),
        TRY_CONVERT(datetime2, s.date_harvest, 103),
        TRY_CONVERT(datetime2, s.date_harvest, 104),
        TRY_CONVERT(datetime2, s.date_harvest, 105),
        CASE WHEN TRY_CONVERT(float, s.date_harvest) IS NOT NULL
             THEN DATEADD(day, CAST(TRY_CONVERT(float, s.date_harvest) AS int) - 2, '1899-12-30') END,
        TRY_CONVERT(datetime2, s.date_harvest)
      ) AS harvest_dt
    FROM dbo.stg_excel_data s
  ),
  se_ranked AS (
    SELECT
      fb.filament_serial,
      fb.printer_name,
      fb.harvest_dt,
      ROW_NUMBER() OVER (PARTITION BY fb.filament_serial ORDER BY fb.harvest_dt DESC) AS rn
    FROM se_base fb
    WHERE fb.filament_serial IS NOT NULL
      AND fb.printer_name IS NOT NULL
      AND fb.printer_name <> ''
  )
  SELECT
    r.filament_serial,
    r.printer_name AS fallback_printer_name
  INTO #fallback_printer
  FROM se_ranked r
  WHERE r.rn = 1;

  /* -------- 3) Resolve rows from stg_filament_excel_data -------- */
  ;WITH fe_base AS (
    SELECT
      NULLIF(LTRIM(RTRIM(CAST(s.filament_id AS NVARCHAR(200)))),'') AS filament_serial,
      NULLIF(LTRIM(RTRIM(CAST(s.printer_fi AS NVARCHAR(200)))),'')  AS printer_name_fe,
      NULLIF(LTRIM(RTRIM(CAST(s.[usage] AS NVARCHAR(50)))),'')      AS usage_flag,
      TRY_CONVERT(decimal(10,2), REPLACE(CAST(s.weight_fl AS NVARCHAR(100)), ',', '.')) AS weight_grams,
      COALESCE(TRY_CONVERT(datetime2, s.use_date, 104), TRY_CONVERT(datetime2, s.use_date)) AS use_dt
    FROM dbo.stg_filament_excel_data s
  ),
  fe_ranked AS (
    SELECT
      b.*,
      ROW_NUMBER() OVER (PARTITION BY b.filament_serial ORDER BY b.use_dt DESC) AS rn_latest
    FROM fe_base b
    WHERE b.filament_serial IS NOT NULL
      AND NOT (
        (b.printer_name_fe IS NULL OR b.printer_name_fe = '')
        AND (b.usage_flag IS NULL OR b.usage_flag = '' OR UPPER(b.usage_flag) = N'NO')
      )
  ),
  fe_latest AS (
    SELECT
      r.filament_serial,
      r.printer_name_fe,
      r.usage_flag,
      r.weight_grams,
      r.use_dt
    FROM fe_ranked r
    WHERE r.rn_latest = 1
  ),
  joined AS (
    SELECT
      f.id AS filament_id,

      /* Printer hierarchy:
         1) printer_fi (filament sheet)
         2) fallback printer from stg_excel_data
         3) UNASSIGNED
      */
      COALESCE(p_fe_norm.id, p_fb_norm.id, @unassigned_printer_id) AS printer_id,

      @fallback_user_id AS mounted_by,
      COALESCE(fl.use_dt, SYSUTCDATETIME()) AS mounted_at,
      CAST(NULL AS DATETIME2) AS unmounted_at,
      CAST(NULL AS INT)       AS unmounted_by,
      COALESCE(fl.weight_grams, 0.00) AS remaining_weight,

      /* Status (from filament sheet only):
         - In Use: printer_fi not empty
         - Unmounted: printer_fi empty AND usage <> 'NO'
         - Else: In Use
      */
      CASE
        WHEN (fl.printer_name_fe IS NOT NULL AND fl.printer_name_fe <> '')
          THEN N'In Use'
        WHEN ((fl.printer_name_fe IS NULL OR fl.printer_name_fe = '')
              AND UPPER(COALESCE(fl.usage_flag,'')) <> N'NO')
          THEN N'Unmounted'
        ELSE N'In Use'
      END AS status
    FROM fe_latest fl
    JOIN dbo.filaments f
      ON f.serial_number = fl.filament_serial
    LEFT JOIN #fallback_printer fp
      ON fp.filament_serial = fl.filament_serial
    LEFT JOIN dbo.printers p_fe_norm
      ON UPPER(REPLACE(p_fe_norm.name, ' ', '')) COLLATE Latin1_General_CI_AI
       = UPPER(REPLACE(fl.printer_name_fe, ' ', '')) COLLATE Latin1_General_CI_AI
    LEFT JOIN dbo.printers p_fb_norm
      ON UPPER(REPLACE(p_fb_norm.name, ' ', '')) COLLATE Latin1_General_CI_AI
       = UPPER(REPLACE(fp.fallback_printer_name, ' ', '')) COLLATE Latin1_General_CI_AI
  )
  INSERT INTO #fm_resolved(filament_id, printer_id, mounted_by, mounted_at, unmounted_at, unmounted_by, remaining_weight, status)
  SELECT DISTINCT filament_id, printer_id, mounted_by, mounted_at, unmounted_at, unmounted_by, remaining_weight, status
  FROM joined;

  /* Track ALL staged filaments (for delete logic) */
  INSERT INTO #all_staged_filaments(filament_id)
  SELECT DISTINCT f.id
  FROM dbo.stg_filament_excel_data s
  JOIN dbo.filaments f
    ON f.serial_number = LTRIM(RTRIM(CAST(s.filament_id AS NVARCHAR(200))))
  WHERE s.filament_id IS NOT NULL;

  /* -------- 4) MERGE into dbo.filament_mounting -------- */
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
  WHEN NOT MATCHED BY SOURCE
       AND tgt.filament_id IN (SELECT filament_id FROM #all_staged_filaments)
    THEN DELETE;

  COMMIT TRAN;
END TRY
BEGIN CATCH
  IF @@TRANCOUNT > 0 ROLLBACK TRAN;
  THROW;
END CATCH;