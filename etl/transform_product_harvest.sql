/* ===========================================================
   etl/transform_product_harvest_from_unified.sql (fixed)
   - Uses vw_unified_legacy_prints (with harvest_seq)
   - Ensures Unassigned + LEGACY_LID/SEAL + legacy requests (10K/6K)
   - MERGE inserts product_harvest by NK:
       (filament_mounting_id, printed_by, print_date)
     and captures mapping via OUTPUT (legal with MERGE)
   - Backfills etl_harvest_map safely (skip conflicts)
   =========================================================== */

SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
  BEGIN TRAN;

  /* -------- 0) Preconditions / helpers -------- */
  DECLARE @fallback_user_id INT = (SELECT TOP 1 id FROM dbo.users ORDER BY id);
  IF @fallback_user_id IS NULL
    RAISERROR('Seed users before product_harvest.', 16, 1);

  DECLARE @unassigned_loc_id INT = (SELECT TOP 1 id FROM dbo.storage_locations WHERE location_name = N'Unassigned');
  IF @unassigned_loc_id IS NULL
  BEGIN
    INSERT dbo.storage_locations(location_name, location_type, description, is_active)
    VALUES (N'Unassigned', N'Virtual', N'Auto-created', 1);
    SET @unassigned_loc_id = SCOPE_IDENTITY();
  END

  DECLARE @legacy_lid_id INT = (SELECT id FROM dbo.lids WHERE serial_number = N'LEGACY_LID');
  IF @legacy_lid_id IS NULL
  BEGIN
    INSERT dbo.lids (serial_number, quantity, location_id, received_by, qc_result)
    VALUES (N'LEGACY_LID', 0, @unassigned_loc_id, @fallback_user_id, N'PASS');
    SET @legacy_lid_id = SCOPE_IDENTITY();
  END

  DECLARE @legacy_seal_id INT = (SELECT id FROM dbo.seals WHERE serial_number = N'LEGACY_SEAL');
  IF @legacy_seal_id IS NULL
  BEGIN
    INSERT dbo.seals (serial_number, quantity, location_id, received_by, qc_result)
    VALUES (N'LEGACY_SEAL', 0, @unassigned_loc_id, @fallback_user_id, N'PASS');
    SET @legacy_seal_id = SCOPE_IDENTITY();
  END

  DECLARE @pt_10k INT = (SELECT id FROM dbo.product_types WHERE name = N'10K');
  DECLARE @pt_6k  INT = (SELECT id FROM dbo.product_types WHERE name = N'6K');

  DECLARE @sku_10k INT = (SELECT MIN(id) FROM dbo.product_skus WHERE product_type_id = @pt_10k);
  DECLARE @sku_6k  INT = (SELECT MIN(id) FROM dbo.product_skus WHERE product_type_id = @pt_6k);

  DECLARE @req_10k INT = (SELECT id FROM dbo.product_requests WHERE notes = N'LEGACY_REQUEST_10K' AND sku_id = @sku_10k);
  IF @pt_10k IS NOT NULL AND @sku_10k IS NOT NULL AND @req_10k IS NULL
  BEGIN
    INSERT dbo.product_requests (requested_by, sku_id, lot_number, status, notes)
    VALUES (@fallback_user_id, @sku_10k, N'LEGACY_LOT', N'Fulfilled', N'LEGACY_REQUEST_10K');
    SET @req_10k = SCOPE_IDENTITY();
  END

  DECLARE @req_6k INT = (SELECT id FROM dbo.product_requests WHERE notes = N'LEGACY_REQUEST_6K' AND sku_id = @sku_6k);
  IF @pt_6k IS NOT NULL AND @sku_6k IS NOT NULL AND @req_6k IS NULL
  BEGIN
    INSERT dbo.product_requests (requested_by, sku_id, lot_number, status, notes)
    VALUES (@fallback_user_id, @sku_6k, N'LEGACY_LOT', N'Fulfilled', N'LEGACY_REQUEST_6K');
    SET @req_6k = SCOPE_IDENTITY();
  END

  /* -------- 1) Stage unified rows in sequence -------- */
  IF OBJECT_ID('tempdb..#U','U') IS NOT NULL DROP TABLE #U;
  CREATE TABLE #U(
    harvest_seq         INT        NOT NULL PRIMARY KEY,
    product_id_bigint   BIGINT     NOT NULL,
    filament_mounting_id INT       NOT NULL,
    printed_by_id       INT        NOT NULL,
    print_date_dt       DATETIME2  NOT NULL,
    product_name        NVARCHAR(100) NOT NULL
  );

  INSERT INTO #U(harvest_seq, product_id_bigint, filament_mounting_id, printed_by_id, print_date_dt, product_name)
  SELECT harvest_seq, product_id_bigint, filament_mounting_id, printed_by_id, print_date_dt, product_name
  FROM dbo.vw_unified_legacy_prints;

  /* Precompute request_id per row (avoid CASE inside MERGE VALUES) */
  IF OBJECT_ID('tempdb..#toins','U') IS NOT NULL DROP TABLE #toins;
  CREATE TABLE #toins(
    harvest_seq          INT        NOT NULL PRIMARY KEY,
    product_id_bigint    BIGINT     NOT NULL,
    filament_mounting_id INT        NOT NULL,
    printed_by_id        INT        NOT NULL,
    print_date_dt        DATETIME2  NOT NULL,
    request_id           INT        NULL
  );

  INSERT INTO #toins(harvest_seq, product_id_bigint, filament_mounting_id, printed_by_id, print_date_dt, request_id)
  SELECT
    u.harvest_seq,
    u.product_id_bigint,
    u.filament_mounting_id,
    u.printed_by_id,
    u.print_date_dt,
    CASE WHEN u.product_name = N'10K' THEN @req_10k
         WHEN u.product_name = N'6K'  THEN @req_6k
         ELSE @req_10k END
  FROM #U u
  ORDER BY u.harvest_seq;

  /* -------- 2) Insert missing product_harvest via MERGE, capture mapping -------- */
  IF OBJECT_ID('tempdb..#map','U') IS NOT NULL DROP TABLE #map;
  CREATE TABLE #map(
    product_id_bigint BIGINT NOT NULL PRIMARY KEY,
    harvest_id        INT    NOT NULL UNIQUE
  );

  MERGE dbo.product_harvest AS tgt
  USING #toins AS src
     ON tgt.filament_mounting_id = src.filament_mounting_id
    AND tgt.printed_by           = src.printed_by_id
    AND tgt.print_date           = src.print_date_dt
  WHEN NOT MATCHED THEN
    INSERT (request_id, lid_id, seal_id, filament_mounting_id, printed_by, print_date)
    VALUES (COALESCE(src.request_id, (SELECT TOP 1 id FROM dbo.product_requests ORDER BY id)),
            @legacy_lid_id, @legacy_seal_id,
            src.filament_mounting_id, src.printed_by_id, src.print_date_dt)
  OUTPUT inserted.id, src.product_id_bigint
    INTO #map(harvest_id, product_id_bigint);

  /* Also map existing harvests (those that matched, i.e., not inserted) */
  INSERT INTO #map(product_id_bigint, harvest_id)
  SELECT t.product_id_bigint, h.id
  FROM #toins t
  JOIN dbo.product_harvest h
    ON h.filament_mounting_id = t.filament_mounting_id
   AND h.printed_by           = t.printed_by_id
   AND h.print_date           = t.print_date_dt
  WHERE NOT EXISTS (SELECT 1 FROM #map m WHERE m.product_id_bigint = t.product_id_bigint);

  /* -------- 3) Backfill etl_harvest_map (skip conflicts on either key) -------- */
  INSERT INTO dbo.etl_harvest_map(product_id_bigint, harvest_id)
  SELECT m.product_id_bigint, m.harvest_id
  FROM #map m
  WHERE NOT EXISTS (SELECT 1 FROM dbo.etl_harvest_map x WHERE x.product_id_bigint = m.product_id_bigint)
    AND NOT EXISTS (SELECT 1 FROM dbo.etl_harvest_map x WHERE x.harvest_id        = m.harvest_id);

  COMMIT TRAN;

  PRINT '[product_harvest_from_unified] complete.';
END TRY
BEGIN CATCH
  IF XACT_STATE() <> 0 ROLLBACK TRAN;
  DECLARE @msg NVARCHAR(4000) = ERROR_MESSAGE();
  RAISERROR('[product_harvest_from_unified] %s', 16, 1, @msg);
END CATCH;

