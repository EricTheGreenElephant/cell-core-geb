BEGIN TRY
  BEGIN TRAN;

  /* ---------- 0) Basics from existing data ---------- */

  -- Unknown rows (idempotent)
  IF NOT EXISTS (SELECT 1 FROM dbo.lifecycle_stages WHERE name = 'Unknown')
    INSERT dbo.lifecycle_stages(name, is_active) VALUES('Unknown',1);

  IF NOT EXISTS (SELECT 1 FROM dbo.product_statuses WHERE name = 'Unknown')
    INSERT dbo.product_statuses(name, is_active) VALUES('Unknown',1);

  IF NOT EXISTS (SELECT 1 FROM dbo.storage_locations WHERE name = 'Unknown')
    INSERT dbo.storage_locations(name, is_active) VALUES('Unknown',1);

  DECLARE @unknown_stage_id    INT = (SELECT TOP 1 id FROM dbo.lifecycle_stages   WHERE name='Unknown');
  DECLARE @unknown_status_id   INT = (SELECT TOP 1 id FROM dbo.product_statuses   WHERE name='Unknown');
  DECLARE @unknown_location_id INT = (SELECT TOP 1 id FROM dbo.storage_locations  WHERE name='Unknown');

  -- Default product type
  IF NOT EXISTS (SELECT 1 FROM dbo.product_types WHERE name='Default')
    INSERT dbo.product_types(name, is_active) VALUES ('Default',1);

  DECLARE @default_type_id INT = (SELECT TOP 1 id FROM dbo.product_types WHERE name='Default');

  /* ---------- 1) Upsert lookups from staging ---------- */

  -- lifecycle_stages from prozess_step
  MERGE dbo.lifecycle_stages AS tgt
  USING (
    SELECT DISTINCT NULLIF(LTRIM(RTRIM(prozess_step)),'') AS name
    FROM dbo.stg_excel_data
  ) AS src
    ON tgt.name = src.name
  WHEN NOT MATCHED AND src.name IS NOT NULL
    THEN INSERT (name, is_active) VALUES (src.name, 1);

  -- product_statuses (prefer QM status; fallback to QC)
  MERGE dbo.product_statuses AS tgt
  USING (
    SELECT DISTINCT
      COALESCE(NULLIF(LTRIM(RTRIM(status_qm_clearance)),''),
               NULLIF(LTRIM(RTRIM(status_quality_check)),''),
               'Unknown') AS name
    FROM dbo.stg_excel_data
  ) AS src
    ON tgt.name = src.name
  WHEN NOT MATCHED THEN
    INSERT (name, is_active) VALUES (src.name, 1);

  -- storage_locations
  MERGE dbo.storage_locations AS tgt
  USING (
    SELECT DISTINCT NULLIF(LTRIM(RTRIM(storage)),'') AS name
    FROM dbo.stg_excel_data
  ) AS src
    ON tgt.name = src.name
  WHEN NOT MATCHED AND src.name IS NOT NULL
    THEN INSERT (name, is_active) VALUES (src.name, 1);

  -- SKUs from Excel product name (adjust if you have a mapping table!)
  MERGE dbo.product_skus AS tgt
  USING (
    SELECT DISTINCT NULLIF(LTRIM(RTRIM(product)),'') AS name
    FROM dbo.stg_excel_data
    WHERE product IS NOT NULL
  ) AS src
    ON tgt.name = src.name
  WHEN NOT MATCHED THEN
    INSERT (name, product_type_id, is_active) VALUES (src.name, @default_type_id, 1);

  -- Make sure any NULL sku.product_type_id is set
  UPDATE s SET product_type_id = COALESCE(s.product_type_id, @default_type_id)
  FROM dbo.product_skus s;

  /* ---------- 2) Resolve FKs for rows we plan to insert ---------- */

  ;WITH base AS (
    SELECT
      sd.*,
      -- source values normalized
      NULLIF(LTRIM(RTRIM(product_id)),'') AS tracking_id_src,
      NULLIF(LTRIM(RTRIM(product)),'')    AS product_name,
      NULLIF(LTRIM(RTRIM(prozess_step)),'') AS stage_name,
      NULLIF(LTRIM(RTRIM(storage)),'')      AS location_name,
      COALESCE(
        NULLIF(LTRIM(RTRIM(status_qm_clearance)),''),
        NULLIF(LTRIM(RTRIM(status_quality_check)),''),
        'Unknown'
      ) AS status_name
    FROM dbo.stg_excel_data sd
  ),
  k AS (
    SELECT
      b.tracking_id_src,
      sku.id                              AS sku_id,
      COALESCE(pt.id, @default_type_id)   AS product_type_id,
      COALESCE(ls.id, @unknown_stage_id)  AS current_stage_id,
      COALESCE(ps.id, @unknown_status_id) AS current_status_id,
      COALESCE(loc.id,@unknown_location_id) AS location_id
    FROM base b
    LEFT JOIN dbo.product_skus      sku ON sku.name = b.product_name
    LEFT JOIN dbo.product_types     pt  ON pt.id   = sku.product_type_id
    LEFT JOIN dbo.lifecycle_stages  ls  ON ls.name = b.stage_name
    LEFT JOIN dbo.product_statuses  ps  ON ps.name = b.status_name
    LEFT JOIN dbo.storage_locations loc ON loc.name = b.location_name
    WHERE b.tracking_id_src IS NOT NULL
  )

  /* ---------- 3) Create one product_harvest per tracking (only for ones not already in tracking) ---------- */

  -- Backfill user / request placeholders that satisfy NOT NULL FKs
  DECLARE @any_user_id INT = (SELECT TOP 1 id FROM dbo.users ORDER BY id); -- use an existing user
  IF @any_user_id IS NULL
    THROW 50001, 'No rows in dbo.users; cannot create product_harvest placeholders.', 1;

  IF NOT EXISTS (SELECT 1 FROM dbo.lids WHERE name='UNKNOWN')  INSERT dbo.lids(name,is_active) VALUES('UNKNOWN',1);
  IF NOT EXISTS (SELECT 1 FROM dbo.seals WHERE name='UNKNOWN') INSERT dbo.seals(name,is_active) VALUES('UNKNOWN',1);
  IF NOT EXISTS (SELECT 1 FROM dbo.filament_mounting WHERE name='UNKNOWN') INSERT dbo.filament_mounting(name,is_active) VALUES('UNKNOWN',1);

  DECLARE @unknown_lid_id INT = (SELECT TOP 1 id FROM dbo.lids WHERE name='UNKNOWN');
  DECLARE @unknown_seal_id INT = (SELECT TOP 1 id FROM dbo.seals WHERE name='UNKNOWN');
  DECLARE @unknown_fm_id   INT = (SELECT TOP 1 id FROM dbo.filament_mounting WHERE name='UNKNOWN');

  IF NOT EXISTS (SELECT 1 FROM dbo.product_requests WHERE notes='Backfill Request')
  BEGIN
    INSERT dbo.product_requests(requested_by, sku_id, lot_number, status, notes)
    VALUES (@any_user_id, (SELECT TOP 1 id FROM dbo.product_skus ORDER BY id), 'BACKFILL', 'Fulfilled', 'Backfill Request');
  END
  DECLARE @backfill_request_id INT = (SELECT TOP 1 id FROM dbo.product_requests WHERE notes='Backfill Request' ORDER BY id);

  -- Build list of tracking_ids we still need to insert
  IF OBJECT_ID('tempdb..#new_tracking','U') IS NOT NULL DROP TABLE #new_tracking;
  SELECT DISTINCT k.tracking_id_src
  INTO #new_tracking
  FROM k
  LEFT JOIN dbo.product_tracking t ON t.tracking_id = k.tracking_id_src
  WHERE t.id IS NULL;   -- only new ones

  -- Create harvest rows for those (MERGE to be idempotent if you rerun)
  IF OBJECT_ID('tempdb..#map_track_to_harvest','U') IS NOT NULL DROP TABLE #map_track_to_harvest;
  CREATE TABLE #map_track_to_harvest (tracking_id NVARCHAR(50) NOT NULL, harvest_id INT NOT NULL);

  MERGE dbo.product_harvest AS tgt
  USING (
    SELECT nt.tracking_id_src, @backfill_request_id AS request_id
    FROM #new_tracking nt
    JOIN k ON k.tracking_id_src = nt.tracking_id_src
  ) AS src
    ON 1 = 0  -- always insert to make 1:1 harvest per tracking (idempotency handled via product_tracking check)
  WHEN NOT MATCHED THEN
    INSERT (request_id, lid_id, seal_id, filament_mounting_id, printed_by, print_date)
    VALUES (src.request_id, @unknown_lid_id, @unknown_seal_id, @unknown_fm_id, @any_user_id, NULL)
  OUTPUT src.tracking_id_src, inserted.id INTO #map_track_to_harvest(tracking_id, harvest_id);

  /* ---------- 4) Insert into product_tracking ---------- */

  INSERT INTO dbo.product_tracking
      (harvest_id, tracking_id, product_type_id, sku_id, current_status_id, previous_stage_id, current_stage_id, location_id)
  SELECT
      m.harvest_id,
      k.tracking_id_src,
      k.product_type_id,
      k.sku_id,
      k.current_status_id,
      NULL AS previous_stage_id,
      k.current_stage_id,
      k.location_id
  FROM #map_track_to_harvest m
  JOIN k ON k.tracking_id_src = m.tracking_id
  LEFT JOIN dbo.product_tracking t ON t.tracking_id = k.tracking_id_src
  WHERE t.id IS NULL;  -- safety

  COMMIT TRAN;
END TRY
BEGIN CATCH
  IF @@TRANCOUNT > 0 ROLLBACK TRAN;
  THROW;
END CATCH;