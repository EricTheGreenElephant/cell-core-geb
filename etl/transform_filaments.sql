/* etl/transform_filaments.sql */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
  BEGIN TRAN;

  DECLARE @CutoffDate date = '2025-07-17';


  /* ---- 0) Preconditions / helpers ---- */
  -- DECLARE @fallback_user_id INT = (SELECT TOP 1 id FROM dbo.users ORDER BY id);
  -- IF @fallback_user_id IS NULL
  -- BEGIN
  --   RAISERROR('No users present; seed users before loading filaments.', 16, 1);
  --   ROLLBACK TRAN;
  --   RETURN;
  -- END
  DECLARE @dept_id INT = (SELECT TOP 1 id FROM dbo.departments ORDER BY id);
  IF @dept_id IS NULL
  BEGIN
    RAISERROR('No departments present; seed departments before loading filaments.', 16, 1);
    ROLLBACK TRAN; 
    RETURN;
  END

  IF NOT EXISTS (SELECT 1 FROM dbo.users WHERE user_principal_name = N'legacy-import@system')
  BEGIN
    INSERT dbo.users (department_id, azure_ad_object_id, user_principal_name, display_name, is_active)
    VALUES (@dept_id, NEWID(), N'legacy-import@system', N'Legacy Import (System)', 0);
  END

DECLARE @fallback_user_id INT =
  (SELECT TOP 1 id FROM dbo.users WHERE user_principal_name = N'legacy-import@system');

IF @fallback_user_id IS NULL 
BEGIN
  RAISERROR('Failed to create/find Legacy Import user.', 16, 1);
  ROLLBACK TRAN;
  RETURN;
END


  /* Ensure Unassigned exists (used as location fallback) */
  IF NOT EXISTS (SELECT 1 FROM dbo.storage_locations WHERE location_name = N'Unassigned')
  BEGIN
    INSERT dbo.storage_locations(location_name, location_type, description, is_active)
    VALUES (N'Unassigned', N'Virtual', N'Fallback for missing shelf', 1);
  END
  DECLARE @unassigned_loc_id INT =
    (SELECT TOP 1 id FROM dbo.storage_locations WHERE location_name = N'Unassigned');

  /* Optional legacy name → user mapping (works even if mapping table doesn't exist) */
  IF OBJECT_ID('tempdb..#legacy_map','U') IS NOT NULL DROP TABLE #legacy_map;
  CREATE TABLE #legacy_map(legacy_name NVARCHAR(200) PRIMARY KEY, user_id INT NOT NULL);
  IF OBJECT_ID('dbo.legacy_name_to_user','U') IS NOT NULL
  BEGIN
    INSERT INTO #legacy_map(legacy_name, user_id)
    SELECT legacy_name, user_id FROM dbo.legacy_name_to_user;
  END

  /* ---- 1) Ensure shelves from staging exist in storage_locations ---- */
  ;WITH shelves AS (
    SELECT DISTINCT NULLIF(LTRIM(RTRIM(CAST(shelf AS NVARCHAR(200)))),'') AS location_name
    FROM dbo.stg_filament_excel_data
  )
  INSERT INTO dbo.storage_locations(location_name, location_type, description, is_active)
  SELECT s.location_name, N'Shelf', N'Imported from legacy filaments', 1
  FROM shelves s
  WHERE s.location_name IS NOT NULL
    AND NOT EXISTS (
      SELECT 1 FROM dbo.storage_locations x WHERE x.location_name = s.location_name
    );

  /* ---- 2) Build normalized source rows into a temp table ---- */
  IF OBJECT_ID('tempdb..#fil_src','U') IS NOT NULL DROP TABLE #fil_src;
  CREATE TABLE #fil_src (
    filament_id   BIGINT        NOT NULL,     -- canonical unique key
    serial_number NVARCHAR(100) NOT NULL,     -- can duplicate
    lot_number    NVARCHAR(100) NOT NULL,
    location_id   INT           NOT NULL,
    weight_grams  DECIMAL(10,2) NOT NULL,
    received_at   DATETIME2     NOT NULL,
    received_by   INT           NOT NULL,
    qc_result     NVARCHAR(10)  NOT NULL CHECK (qc_result IN (N'PASS', N'FAIL'))
  );

  -- ;WITH base AS (
  --   SELECT
  --     filament_id_raw = NULLIF(LTRIM(RTRIM(CAST(filament_id AS NVARCHAR(200)))),''),
  --     filament_raw    = NULLIF(LTRIM(RTRIM(CAST(filament    AS NVARCHAR(200)))),''),
  --     shelf_name      = NULLIF(LTRIM(RTRIM(CAST(shelf       AS NVARCHAR(200)))),''),
  --     weight_grams    = TRY_CONVERT(DECIMAL(10,2), REPLACE(CAST(weight_fl AS NVARCHAR(100)), ',', '.')),
  --     received_at     = COALESCE(TRY_CONVERT(datetime2, vsc_date, 104), TRY_CONVERT(datetime2, vsc_date)),
  --     operator_legacy = NULLIF(LTRIM(RTRIM(CAST(vsc_operator AS NVARCHAR(200)))),''),
  --     vs_check        = COALESCE(CAST(vs_check AS NVARCHAR(100)),'')
  --   FROM dbo.stg_filament_excel_data
  -- ),
  -- norm AS (
  --   SELECT
  --     -- Robust parse for business ID: plain → remove commas → scientific to DECIMAL → BIGINT
  --     filament_id = COALESCE(
  --       TRY_CONVERT(BIGINT, filament_id_raw),
  --       TRY_CONVERT(BIGINT, REPLACE(filament_id_raw, ',', '')),
  --       TRY_CONVERT(BIGINT, CONVERT(DECIMAL(38,0), TRY_CONVERT(float, filament_id_raw)))
  --     ),
  --     serial_number = LEFT(filament_raw, 100),
  --     lot_number    = LEFT(CASE WHEN CHARINDEX('-', filament_raw) > 0
  --                               THEN LEFT(filament_raw, CHARINDEX('-', filament_raw) - 1)
  --                               ELSE filament_raw END, 100),
  --     location_id   = COALESCE(loc.id, @unassigned_loc_id),
  --     weight_grams  = COALESCE(b.weight_grams, 0.00),
  --     received_at   = COALESCE(b.received_at, SYSUTCDATETIME()),
  --     received_by   = COALESCE(lm.user_id, u.id, @fallback_user_id),
  --     qc_result     = CASE
  --                       WHEN UPPER(LTRIM(RTRIM(b.vs_check))) IN
  --                            (N'FAIL', N'FAILED', N'NO', N'NEIN', N'N', N'FALSE', N'0', N'REJECT', N'REJECTED') THEN N'FAIL'
  --                       WHEN UPPER(LTRIM(RTRIM(b.vs_check))) IN
  --                            (N'OK', N'PASS', N'PASSED', N'GOOD', N'ACCEPT', N'ACCEPTED', N'JA', N'YES', N'Y', N'TRUE', N'1') THEN N'PASS'
  --                       ELSE N'PASS'
  --                     END
  --   FROM base b
  --   LEFT JOIN dbo.storage_locations loc ON loc.location_name = b.shelf_name
  --   LEFT JOIN #legacy_map lm            ON lm.legacy_name = b.operator_legacy
  --   LEFT JOIN dbo.users u
  --     ON u.display_name COLLATE Latin1_General_CI_AI
  --      = b.operator_legacy COLLATE Latin1_General_CI_AI
  --   WHERE b.filament_raw IS NOT NULL
  --     AND (
  --           TRY_CONVERT(BIGINT, filament_id_raw) IS NOT NULL OR
  --           TRY_CONVERT(BIGINT, REPLACE(filament_id_raw, ',', '')) IS NOT NULL OR
  --           TRY_CONVERT(BIGINT, CONVERT(DECIMAL(38,0), TRY_CONVERT(float, filament_id_raw))) IS NOT NULL
  --         )
  -- )
  -- INSERT INTO #fil_src (filament_id, serial_number, lot_number, location_id, weight_grams, received_at, received_by, qc_result)
  -- SELECT DISTINCT filament_id, serial_number, lot_number, location_id, weight_grams, received_at, received_by, qc_result
  -- FROM norm;


  ;WITH
  /* ---------- A) Filaments used in products after cutoff ---------- */
  UsedAfterCutoff AS (
    SELECT DISTINCT
      filament_id = TRY_CONVERT(BIGINT, sed.filament_id)
    FROM dbo.stg_excel_data sed
    WHERE sed.filament_id IS NOT NULL
      AND TRY_CONVERT(BIGINT, sed.filament_id) IS NOT NULL
      AND TRY_CONVERT(date, sed.date_harvest) >= @CutoffDate
  ),

  /* ---------- B) Filaments received/checked after cutoff (new inventory, not yet used) ---------- */
  ReceivedAfterCutoff AS (
    SELECT DISTINCT
      filament_id = COALESCE(
        TRY_CONVERT(BIGINT, NULLIF(LTRIM(RTRIM(CAST(fe.filament_id AS NVARCHAR(200)))),'')),
        TRY_CONVERT(BIGINT, REPLACE(NULLIF(LTRIM(RTRIM(CAST(fe.filament_id AS NVARCHAR(200)))),''), ',', '')),
        TRY_CONVERT(BIGINT, CONVERT(DECIMAL(38,0), TRY_CONVERT(float, NULLIF(LTRIM(RTRIM(CAST(fe.filament_id AS NVARCHAR(200)))),''))))
      )
    FROM dbo.stg_filament_excel_data fe
    WHERE
      COALESCE(
        TRY_CONVERT(date, fe.vsc_date, 104),  -- dd.mm.yyyy
        TRY_CONVERT(date, fe.vsc_date, 105),  -- dd-mm-yyyy
        TRY_CONVERT(date, fe.vsc_date, 101),  -- mm/dd/yyyy
        TRY_CONVERT(date, fe.vsc_date, 103),  -- dd/mm/yyyy
        CASE WHEN TRY_CONVERT(float, fe.vsc_date) IS NOT NULL
             THEN CONVERT(date, DATEADD(day, CAST(TRY_CONVERT(float, fe.vsc_date) AS int) - 2, '1899-12-30'))
        END,
        TRY_CONVERT(date, fe.vsc_date)
      ) >= @CutoffDate
  ),

  EligibleFilaments AS (
    SELECT filament_id FROM UsedAfterCutoff
    UNION
    SELECT filament_id FROM ReceivedAfterCutoff
  ),

  base AS (
    SELECT
      filament_id_raw = NULLIF(LTRIM(RTRIM(CAST(filament_id AS NVARCHAR(200)))),''),
      filament_raw    = NULLIF(LTRIM(RTRIM(CAST(filament    AS NVARCHAR(200)))),''),
      shelf_name      = NULLIF(LTRIM(RTRIM(CAST(shelf       AS NVARCHAR(200)))),''),
      weight_grams    = TRY_CONVERT(DECIMAL(10,2), REPLACE(CAST(weight_fl AS NVARCHAR(100)), ',', '.')),
      received_at     = COALESCE(TRY_CONVERT(datetime2, vsc_date, 104), TRY_CONVERT(datetime2, vsc_date)),
      operator_legacy = NULLIF(LTRIM(RTRIM(CAST(vsc_operator AS NVARCHAR(200)))),''),
      vs_check        = COALESCE(CAST(vs_check AS NVARCHAR(100)),'')
    FROM dbo.stg_filament_excel_data
  ),

  norm AS (
    SELECT
      filament_id = COALESCE(
        TRY_CONVERT(BIGINT, filament_id_raw),
        TRY_CONVERT(BIGINT, REPLACE(filament_id_raw, ',', '')),
        TRY_CONVERT(BIGINT, CONVERT(DECIMAL(38,0), TRY_CONVERT(float, filament_id_raw)))
      ),
      serial_number = LEFT(filament_raw, 100),
      lot_number    = LEFT(CASE WHEN CHARINDEX('-', filament_raw) > 0
                                THEN LEFT(filament_raw, CHARINDEX('-', filament_raw) - 1)
                                ELSE filament_raw END, 100),
      location_id   = COALESCE(loc.id, @unassigned_loc_id),
      weight_grams  = COALESCE(b.weight_grams, 0.00),
      received_at   = COALESCE(b.received_at, SYSUTCDATETIME()),
      received_by   = COALESCE(lm.user_id, u.id, @fallback_user_id),
      qc_result     = CASE
                        WHEN UPPER(LTRIM(RTRIM(b.vs_check))) IN
                             (N'FAIL', N'FAILED', N'NO', N'NEIN', N'N', N'FALSE', N'0', N'REJECT', N'REJECTED') THEN N'FAIL'
                        WHEN UPPER(LTRIM(RTRIM(b.vs_check))) IN
                             (N'OK', N'PASS', N'PASSED', N'GOOD', N'ACCEPT', N'ACCEPTED', N'JA', N'YES', N'Y', N'TRUE', N'1') THEN N'PASS'
                        ELSE N'PASS'
                      END
    FROM base b
    LEFT JOIN dbo.storage_locations loc ON loc.location_name = b.shelf_name
    LEFT JOIN #legacy_map lm            ON lm.legacy_name = b.operator_legacy
    LEFT JOIN dbo.users u
      ON u.display_name COLLATE Latin1_General_CI_AI
       = b.operator_legacy COLLATE Latin1_General_CI_AI
    WHERE b.filament_raw IS NOT NULL
      AND (
            TRY_CONVERT(BIGINT, filament_id_raw) IS NOT NULL OR
            TRY_CONVERT(BIGINT, REPLACE(filament_id_raw, ',', '')) IS NOT NULL OR
            TRY_CONVERT(BIGINT, CONVERT(DECIMAL(38,0), TRY_CONVERT(float, filament_id_raw))) IS NOT NULL
          )
  )

  INSERT INTO #fil_src (filament_id, serial_number, lot_number, location_id, weight_grams, received_at, received_by, qc_result)
  SELECT DISTINCT
    n.filament_id,
    n.serial_number,
    n.lot_number,
    n.location_id,
    n.weight_grams,
    n.received_at,
    n.received_by,
    n.qc_result
  FROM norm n
  JOIN EligibleFilaments e
    ON e.filament_id = n.filament_id;


  /* ---- 3) UPSERT by filament_id (canonical). serial_number may duplicate. ---- */

  -- UPDATE existing rows (match on filament_id)
  UPDATE tgt
  SET
    tgt.serial_number = src.serial_number,  -- allowed to change/duplicate
    tgt.lot_number    = src.lot_number,
    tgt.location_id   = src.location_id,
    tgt.weight_grams  = src.weight_grams,
    tgt.received_at   = src.received_at,
    tgt.received_by   = src.received_by,
    tgt.qc_result     = src.qc_result
  FROM dbo.filaments AS tgt
  JOIN #fil_src     AS src
    ON tgt.filament_id = src.filament_id;

  -- INSERT new rows (where filament_id not present)
  INSERT INTO dbo.filaments
    (filament_id, serial_number, lot_number, location_id, weight_grams, received_at, received_by, qc_result)
  SELECT
    s.filament_id, s.serial_number, s.lot_number, s.location_id,
    s.weight_grams, s.received_at, s.received_by, s.qc_result
  FROM #fil_src s
  WHERE NOT EXISTS (SELECT 1 FROM dbo.filaments t WHERE t.filament_id = s.filament_id);

  COMMIT TRAN;

  DECLARE @total INT = (SELECT COUNT(*) FROM dbo.filaments);
  PRINT '[filaments] upsert complete.';
  PRINT '[filaments] current row count: ' + CONVERT(varchar(20), @total);

END TRY
BEGIN CATCH
  IF @@TRANCOUNT > 0 ROLLBACK TRAN;
  DECLARE @msg NVARCHAR(4000) = ERROR_MESSAGE();
  RAISERROR('Filament transform failed: %s', 16, 1, @msg);
END CATCH;
