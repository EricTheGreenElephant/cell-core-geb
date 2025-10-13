BEGIN TRY
  BEGIN TRAN;

  /* =======================
     0) Preconditions / Setup
     ======================= */

  DECLARE @fallback_user_id INT = (SELECT TOP 1 id FROM dbo.users ORDER BY id);
  IF @fallback_user_id IS NULL
    THROW 60010, 'No users present; seed users before loading product_harvest.', 1;

  /* Ensure 'Unassigned' storage location exists (for legacy lids/seals) */
  IF NOT EXISTS (SELECT 1 FROM dbo.storage_locations WHERE location_name = 'Unassigned')
  BEGIN
    INSERT dbo.storage_locations(location_name, location_type, description, is_active)
    VALUES ('Unassigned', 'Virtual', 'Fallback for legacy imports', 1);
  END
  DECLARE @unassigned_loc_id INT = (SELECT TOP 1 id FROM dbo.storage_locations WHERE location_name = 'Unassigned');

  /* Ensure a LEGACY product type + SKU for placeholder product_requests */
  IF NOT EXISTS (SELECT 1 FROM dbo.product_types WHERE name = 'LEGACY_TYPE')
  BEGIN
    INSERT dbo.product_types(name, is_active) VALUES ('LEGACY_TYPE', 1);
  END
  DECLARE @legacy_type_id INT = (SELECT id FROM dbo.product_types WHERE name = 'LEGACY_TYPE');

  IF NOT EXISTS (SELECT 1 FROM dbo.product_skus WHERE sku = 'LEGACY_SKU')
  BEGIN
    INSERT dbo.product_skus(product_type_id, sku, name, is_serialized, is_bundle, pack_qty, is_active)
    VALUES (@legacy_type_id, 'LEGACY_SKU', 'Legacy Placeholder SKU', 1, 0, 1, 1);
  END
  DECLARE @legacy_sku_id INT = (SELECT id FROM dbo.product_skus WHERE sku = 'LEGACY_SKU');

  /* Ensure a single LEGACY product_request to satisfy NOT NULL FK */
  IF NOT EXISTS (SELECT 1 FROM dbo.product_requests WHERE lot_number = 'LEGACY_LOT' AND sku_id = @legacy_sku_id)
  BEGIN
    INSERT dbo.product_requests(requested_by, sku_id, lot_number, status, notes)
    VALUES (@fallback_user_id, @legacy_sku_id, 'LEGACY_LOT', 'Pending', 'Auto-created for legacy harvest import');
  END
  DECLARE @legacy_request_id INT = (
      SELECT TOP 1 id FROM dbo.product_requests
      WHERE lot_number = 'LEGACY_LOT' AND sku_id = @legacy_sku_id
      ORDER BY id
  );

  /* Ensure LEGACY lid & seal rows (NOT NULL FKs) */
  IF NOT EXISTS (SELECT 1 FROM dbo.lids WHERE serial_number = 'LEGACY-LID')
  BEGIN
    INSERT dbo.lids(serial_number, quantity, location_id, received_at, received_by, qc_result)
    VALUES ('LEGACY-LID', 0, @unassigned_loc_id, SYSUTCDATETIME(), @fallback_user_id, 'PASS');
  END
  IF NOT EXISTS (SELECT 1 FROM dbo.seals WHERE serial_number = 'LEGACY-SEAL')
  BEGIN
    INSERT dbo.seals(serial_number, quantity, location_id, received_at, received_by, qc_result)
    VALUES ('LEGACY-SEAL', 0, @unassigned_loc_id, SYSUTCDATETIME(), @fallback_user_id, 'PASS');
  END

  DECLARE @legacy_lid_id  INT = (SELECT id FROM dbo.lids  WHERE serial_number = 'LEGACY-LID');
  DECLARE @legacy_seal_id INT = (SELECT id FROM dbo.seals WHERE serial_number = 'LEGACY-SEAL');

  /* Legacy operator mapping table is optional; create if missing */
  IF OBJECT_ID('dbo.legacy_name_to_user','U') IS NULL
  BEGIN
    CREATE TABLE dbo.legacy_name_to_user(
      legacy_name NVARCHAR(200) PRIMARY KEY,
      user_id     INT NOT NULL CONSTRAINT fk_legacy_map_user_ph REFERENCES dbo.users(id)
    );
  END

  /* =======================
     1) Source rows (>= 2025-07-17)
     ======================= */

  IF OBJECT_ID('tempdb..#harvest_src','U') IS NOT NULL DROP TABLE #harvest_src;
  CREATE TABLE #harvest_src(
    product_rownum     BIGINT IDENTITY(1,1) PRIMARY KEY, -- just for debugging
    product_id_ext     NVARCHAR(100) NULL,               -- stg.product_id (external)
    filament_serial    NVARCHAR(200) NOT NULL,
    print_date         DATETIME2     NOT NULL,
    operator_legacy    NVARCHAR(200) NULL
  );

  ;WITH raw AS (
    SELECT
      /* External id (if present) for traceability; not stored in target table */
      NULLIF(LTRIM(RTRIM(CAST(s.product_id AS NVARCHAR(100)))),'') AS product_id_ext,
      NULLIF(LTRIM(RTRIM(CAST(s.filament_id AS NVARCHAR(200)))),'') AS filament_serial,
      /* robust parse of date_harvest */
      COALESCE(
        TRY_CONVERT(datetime2, s.date_harvest, 101),
        TRY_CONVERT(datetime2, s.date_harvest, 103),
        TRY_CONVERT(datetime2, s.date_harvest, 104),
        TRY_CONVERT(datetime2, s.date_harvest, 105),
        CASE WHEN TRY_CONVERT(float, s.date_harvest) IS NOT NULL
             THEN DATEADD(day, CAST(TRY_CONVERT(float, s.date_harvest) AS int) - 2, '1899-12-30') END,
        TRY_CONVERT(datetime2, s.date_harvest)
      ) AS print_date,
      NULLIF(LTRIM(RTRIM(CAST(s.operator_harvest AS NVARCHAR(200)))),'') AS operator_legacy
    FROM dbo.stg_excel_data s
  )
  INSERT INTO #harvest_src(product_id_ext, filament_serial, print_date, operator_legacy)
  SELECT
    r.product_id_ext,
    r.filament_serial,
    r.print_date,
    r.operator_legacy
  FROM raw r
  WHERE r.filament_serial IS NOT NULL
    AND r.print_date  IS NOT NULL
    AND r.print_date >= '2025-07-17T00:00:00'  -- filter scope
  ;

  /* =======================
     2) Resolve all foreign keys
     ======================= */

  IF OBJECT_ID('tempdb..#harvest_resolved','U') IS NOT NULL DROP TABLE #harvest_resolved;
  CREATE TABLE #harvest_resolved(
    filament_mounting_id INT NOT NULL,
    request_id           INT NOT NULL,
    lid_id               INT NOT NULL,
    seal_id              INT NOT NULL,
    printed_by           INT NOT NULL,
    print_date           DATETIME2 NOT NULL,

    /* optional debug columns (not inserted into target) */
    product_id_ext       NVARCHAR(100) NULL
  );

  ;WITH src AS (
    SELECT hs.product_id_ext,
           hs.filament_serial,
           hs.print_date,
           hs.operator_legacy
    FROM #harvest_src hs
  ),
  f_join AS (
    SELECT
      s.product_id_ext,
      s.print_date,
      s.operator_legacy,
      f.id AS filament_id
    FROM src s
    JOIN dbo.filaments f
      ON f.serial_number = s.filament_serial
  ),
  fm_join AS (
    SELECT
      fj.product_id_ext,
      fj.print_date,
      fj.operator_legacy,
      fm.id AS filament_mounting_id
    FROM f_join fj
    JOIN dbo.filament_mounting fm
      ON fm.filament_id = fj.filament_id
  ),
  user_join AS (
    SELECT
      fmj.product_id_ext,
      fmj.print_date,
      fmj.filament_mounting_id,
      COALESCE(map.user_id,
               u.id,
               @fallback_user_id) AS printed_by
    FROM fm_join fmj
    LEFT JOIN dbo.legacy_name_to_user map
      ON map.legacy_name = fmj.operator_legacy
    LEFT JOIN dbo.users u
      ON u.display_name COLLATE Latin1_General_CI_AI
       = fmj.operator_legacy COLLATE Latin1_General_CI_AI
  )
  INSERT INTO #harvest_resolved(filament_mounting_id, request_id, lid_id, seal_id, printed_by, print_date, product_id_ext)
  SELECT
    uj.filament_mounting_id,
    @legacy_request_id      AS request_id,
    @legacy_lid_id          AS lid_id,
    @legacy_seal_id         AS seal_id,
    uj.printed_by,
    uj.print_date,
    uj.product_id_ext
  FROM user_join uj;

  /* =======================
     3) MERGE into dbo.product_harvest
        - Idempotent on (filament_mounting_id, print_date)
     ======================= */

  MERGE dbo.product_harvest AS tgt
  USING (
    SELECT DISTINCT
      filament_mounting_id,
      request_id,
      lid_id,
      seal_id,
      printed_by,
      print_date
    FROM #harvest_resolved
  ) AS src
  ON  tgt.filament_mounting_id = src.filament_mounting_id
  AND tgt.print_date           = src.print_date
  WHEN MATCHED THEN
    UPDATE SET
      tgt.request_id           = src.request_id,
      tgt.lid_id               = src.lid_id,
      tgt.seal_id              = src.seal_id,
      tgt.printed_by           = src.printed_by
  WHEN NOT MATCHED THEN
    INSERT (request_id, lid_id, seal_id, filament_mounting_id, printed_by, print_date)
    VALUES (src.request_id, src.lid_id, src.seal_id, src.filament_mounting_id, src.printed_by, src.print_date);

  /* =======================
     4) Optional sanity checks (print counts)
     ======================= */
  DECLARE @imported INT = (
    SELECT COUNT(*) FROM dbo.product_harvest
    WHERE print_date >= '2025-07-17T00:00:00'
  );
  PRINT CONCAT('[product_harvest] rows >= 2025-07-17 now: ', @imported);

  COMMIT TRAN;
END TRY
BEGIN CATCH
  IF @@TRANCOUNT > 0 ROLLBACK TRAN;
  THROW;
END CATCH;