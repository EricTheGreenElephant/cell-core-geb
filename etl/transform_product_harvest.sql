/* ===========================================================
   Transform legacy rows into dbo.product_harvest
   - Creates/ensures legacy rows (Unassigned location, legacy lid/seal, legacy requests)
   - Ensures all referenced storage locations exist
   - Filters staging to valid/typed rows (10K/6K; required cols; numeric ids)
   - Resolves filament_mounting via (printer, filament_id)
   - Maps operator_harvest -> users (fallback to first user)
   - Inserts product_harvest rows idempotently using a natural key:
       (filament_mounting_id, printed_by, print_date)
   - Ignores staging rows already represented by an identical harvest row.
   =========================================================== */

BEGIN TRY
  BEGIN TRAN;

  /* -------- 0) Preconditions & helpers -------- */
  DECLARE @fallback_user_id INT = (
    SELECT TOP (1) id FROM dbo.users WITH (READPAST) ORDER BY id
  );
  IF @fallback_user_id IS NULL
    THROW 50010, 'No users present; seed users before loading product_harvest.', 1;

  /* Ensure Unassigned location exists */
  DECLARE @unassigned_loc_id INT;
  SELECT @unassigned_loc_id = id FROM dbo.storage_locations WHERE location_name = N'Unassigned';
  IF @unassigned_loc_id IS NULL
  BEGIN
    INSERT INTO dbo.storage_locations (location_name, location_type, description, is_active)
    VALUES (N'Unassigned', N'Virtual', N'Auto-created for missing legacy storage', 1);
    SET @unassigned_loc_id = SCOPE_IDENTITY();
  END

  /* Ensure legacy LID/SEAL rows exist (used as placeholders) */
  DECLARE @legacy_lid_id INT, @legacy_seal_id INT;
  SELECT @legacy_lid_id = id FROM dbo.lids WHERE serial_number = N'LEGACY_LID';
  IF @legacy_lid_id IS NULL
  BEGIN
    INSERT INTO dbo.lids (serial_number, quantity, location_id, received_by, qc_result)
    VALUES (N'LEGACY_LID', 0, @unassigned_loc_id, @fallback_user_id, N'PASS');
    SET @legacy_lid_id = SCOPE_IDENTITY();
  END

  SELECT @legacy_seal_id = id FROM dbo.seals WHERE serial_number = N'LEGACY_SEAL';
  IF @legacy_seal_id IS NULL
  BEGIN
    INSERT INTO dbo.seals (serial_number, quantity, location_id, received_by, qc_result)
    VALUES (N'LEGACY_SEAL', 0, @unassigned_loc_id, @fallback_user_id, N'PASS');
    SET @legacy_seal_id = SCOPE_IDENTITY();
  END

  /* Ensure product_types exist for 10K/6K and capture ids */
  DECLARE @pt_10k INT, @pt_6k INT;
  SELECT @pt_10k = id FROM dbo.product_types WHERE name = N'10K';
  SELECT @pt_6k  = id FROM dbo.product_types WHERE name = N'6K';

  /* Build or re-use a single legacy request per product type (FULFILLED & neutral lot) */
  DECLARE @legacy_req_10k INT, @legacy_req_6k INT;

  IF @pt_10k IS NOT NULL
  BEGIN
    /* Pick a default sku for this product type (lowest id) */
    DECLARE @sku_10k INT = (
      SELECT MIN(id) FROM dbo.product_skus WHERE product_type_id = @pt_10k
    );
    IF @sku_10k IS NULL
      SET @sku_10k = 1; /* last-resort fallback */

    SELECT @legacy_req_10k = id
    FROM dbo.product_requests
    WHERE notes = N'LEGACY_REQUEST_10K' AND sku_id = @sku_10k;

    IF @legacy_req_10k IS NULL
    BEGIN
      INSERT INTO dbo.product_requests (requested_by, sku_id, lot_number, status, notes)
      VALUES (@fallback_user_id, @sku_10k, N'LEGACY_LOT', N'Fulfilled', N'LEGACY_REQUEST_10K');
      SET @legacy_req_10k = SCOPE_IDENTITY();
    END
  END

  IF @pt_6k IS NOT NULL
  BEGIN
    DECLARE @sku_6k INT = (
      SELECT MIN(id) FROM dbo.product_skus WHERE product_type_id = @pt_6k
    );
    IF @sku_6k IS NULL
      SET @sku_6k = 2; /* last-resort fallback */

    SELECT @legacy_req_6k = id
    FROM dbo.product_requests
    WHERE notes = N'LEGACY_REQUEST_6K' AND sku_id = @sku_6k;

    IF @legacy_req_6k IS NULL
    BEGIN
      INSERT INTO dbo.product_requests (requested_by, sku_id, lot_number, status, notes)
      VALUES (@fallback_user_id, @sku_6k, N'LEGACY_LOT', N'Fulfilled', N'LEGACY_REQUEST_6K');
      SET @legacy_req_6k = SCOPE_IDENTITY();
    END
  END

  /* -------- 1) Prep: insert any missing storage locations referenced by staging -------- */
  ;WITH ValidStage AS (
    SELECT
      sed.*,
      TRY_CAST(sed.product_id  AS BIGINT) AS product_id_bigint,
      TRY_CAST(sed.filament_id AS BIGINT) AS filament_id_bigint
    FROM dbo.stg_excel_data sed
    WHERE
      sed.product IN (N'10K', N'6K')
      AND sed.status_quality_check IS NOT NULL
      AND sed.product      IS NOT NULL
      AND sed.printer      IS NOT NULL
      AND sed.date_harvest IS NOT NULL
      AND TRY_CAST(sed.product_id  AS BIGINT) IS NOT NULL
      AND TRY_CAST(sed.filament_id AS BIGINT) IS NOT NULL
  )
  INSERT INTO dbo.storage_locations (location_name, location_type, description, is_active)
  SELECT DISTINCT
      v.storage, NULL, N'Auto-imported from legacy staging', 1
  FROM ValidStage v
  LEFT JOIN dbo.storage_locations sl
    ON sl.location_name = v.storage
  WHERE v.storage IS NOT NULL
    AND sl.id IS NULL;

  /* -------- 2) Build source rows with all resolved FKs we need -------- */
  IF OBJECT_ID('tempdb..#src_harvest') IS NOT NULL DROP TABLE #src_harvest;
  CREATE TABLE #src_harvest(
      product_id_bigint BIGINT NOT NULL,
      filament_mounting_id INT NOT NULL,
      printed_by INT NOT NULL,
      print_date DATETIME2 NOT NULL,
      req_id INT NOT NULL,
      lid_id INT NOT NULL,
      seal_id INT NOT NULL
  );

  ;WITH ValidStage AS (
    SELECT
      sed.*,
      TRY_CAST(sed.product_id  AS BIGINT) AS product_id_bigint,
      TRY_CAST(sed.filament_id AS BIGINT) AS filament_id_bigint,
      TRY_CONVERT(DATETIME2, sed.date_harvest) AS print_date_dt
    FROM dbo.stg_excel_data sed
    WHERE
      sed.product IN (N'10K', N'6K')
      AND sed.status_quality_check IS NOT NULL
      AND sed.product      IS NOT NULL
      AND sed.printer      IS NOT NULL
      AND sed.date_harvest IS NOT NULL
      AND TRY_CAST(sed.product_id  AS BIGINT) IS NOT NULL
      AND TRY_CAST(sed.filament_id AS BIGINT) IS NOT NULL
  )
  INSERT INTO #src_harvest (product_id_bigint, filament_mounting_id, printed_by, print_date, req_id, lid_id, seal_id)
  SELECT
      v.product_id_bigint,
      fm.id AS filament_mounting_id,
      COALESCE(u.id, @fallback_user_id) AS printed_by,
      v.print_date_dt,
      CASE WHEN v.product = N'10K' THEN ISNULL(@legacy_req_10k, ISNULL(@legacy_req_6k, 1))
           WHEN v.product = N'6K'  THEN ISNULL(@legacy_req_6k,  ISNULL(@legacy_req_10k, 1))
           ELSE ISNULL(@legacy_req_10k, 1) END AS req_id,
      @legacy_lid_id,
      @legacy_seal_id
  FROM ValidStage v
  /* resolve filament row by external filament_id */
  INNER JOIN dbo.filaments f
    ON f.filament_id = v.filament_id_bigint
  /* resolve printer by name */
  INNER JOIN dbo.printers p
    ON p.name = v.printer
  /* resolve mounted spool on that printer */
  INNER JOIN dbo.filament_mounting fm
    ON fm.filament_tracking_id = f.id
   AND fm.printer_id = p.id
  /* operator -> user (fallback later) */
  LEFT JOIN dbo.users u
    ON u.display_name = v.operator_harvest;

  /* -------- 3) Insert product_harvest idempotently using a natural key -------- */
  /* Natural key: (filament_mounting_id, printed_by, print_date) */
  /* Avoid duplicates on reruns. */
  INSERT INTO dbo.product_harvest (request_id, lid_id, seal_id, filament_mounting_id, printed_by, print_date)
  SELECT s.req_id, s.lid_id, s.seal_id, s.filament_mounting_id, s.printed_by, s.print_date
  FROM #src_harvest s
  WHERE NOT EXISTS (
    SELECT 1
    FROM dbo.product_harvest h
    WHERE h.filament_mounting_id = s.filament_mounting_id
      AND h.printed_by          = s.printed_by
      AND h.print_date          = s.print_date
  );

  COMMIT TRAN;
  PRINT '[TRANSFORMED] product_harvest';
END TRY
BEGIN CATCH
  IF XACT_STATE() <> 0 ROLLBACK TRAN;

  DECLARE @msg NVARCHAR(4000) = ERROR_MESSAGE();
  DECLARE @num INT = ERROR_NUMBER();
  DECLARE @state INT = ERROR_STATE();
  DECLARE @sev INT = ERROR_SEVERITY();
  RAISERROR('[transform_product_harvest] %s (num=%d, state=%d, sev=%d)', @sev, 1, @msg, @num, @state, @sev);
END CATCH;
