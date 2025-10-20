/* ===========================================================
   Transform staging → dbo.product_tracking
   KISS Edition (No etl_harvest_map)
   =========================================================== */

BEGIN TRY
  BEGIN TRAN;

  /* -------- 0) Preconditions -------- */
  DECLARE @unassigned_loc_id INT = (
      SELECT TOP 1 id FROM dbo.storage_locations WHERE location_name = N'Unassigned'
  );
  IF @unassigned_loc_id IS NULL
  BEGIN
      INSERT INTO dbo.storage_locations (location_name, location_type, description, is_active)
      VALUES (N'Unassigned', N'Virtual', N'Auto-created fallback', 1);
      SET @unassigned_loc_id = SCOPE_IDENTITY();
  END;

  /* -------- 1) Stage valid products (your working logic) -------- */
  IF OBJECT_ID('tempdb..#src_tracking','U') IS NOT NULL DROP TABLE #src_tracking;
  CREATE TABLE #src_tracking (
      product_id BIGINT,
      harvest_id INT,
      product_type_id INT,
      sku_id INT,
      current_status_id INT NULL,
      previous_stage_id INT NULL,
      current_stage_id INT,
      location_id INT,
      last_updated_at DATETIME2
  );

  ;WITH ValidProducts AS (
      SELECT DISTINCT
          TRY_CAST(sed.product_id AS BIGINT) AS product_id_bigint
      FROM dbo.stg_excel_data sed
      WHERE sed.product_id IS NOT NULL
        AND TRY_CAST(sed.product_id AS BIGINT) IS NOT NULL
        AND sed.filament_id IS NOT NULL
        AND TRY_CAST(sed.filament_id AS BIGINT) IS NOT NULL
        AND sed.status_quality_check IS NOT NULL
        AND LTRIM(RTRIM(sed.product)) IN (N'10K', N'6K')
  ),
  ProductDetails AS (
      SELECT
          TRY_CAST(sed.product_id  AS BIGINT)      AS product_id_bigint,
          TRY_CAST(sed.filament_id AS BIGINT)      AS filament_id_bigint,
          pt.id                                   AS product_type_id,
          (SELECT MIN(ps.id)
           FROM dbo.product_skus ps
           WHERE ps.product_type_id = pt.id)      AS sku_id,
          CASE
              WHEN UPPER(LTRIM(RTRIM(sed.status_quality_check))) = 'FAIL'
                  THEN (SELECT id FROM dbo.product_statuses WHERE status_name = N'Waste')
              WHEN UPPER(LTRIM(RTRIM(sed.status_quality_check))) = 'PASS'
                   AND UPPER(LTRIM(RTRIM(ISNULL(sed.second_rate_goods, '')))) = 'YES'
                  THEN (SELECT id FROM dbo.product_statuses WHERE status_name = N'B-Ware')
              WHEN UPPER(LTRIM(RTRIM(sed.status_quality_check))) = 'PASS'
                   AND UPPER(LTRIM(RTRIM(ISNULL(sed.second_rate_goods, '')))) = 'NO'
                  THEN (SELECT id FROM dbo.product_statuses WHERE status_name = N'A-Ware')
              ELSE NULL
          END                                     AS current_status_id,
          NULL                                    AS previous_stage_id,
          CASE UPPER(LTRIM(RTRIM(ISNULL(sed.prozess_step, ''))))
              WHEN 'SOLD'             THEN 12
              WHEN 'SALES'            THEN 8
              WHEN 'NOT USABLE'       THEN 10
              WHEN 'INTERNAL'         THEN 13
              WHEN 'IN TREATMENT'     THEN 5
              WHEN 'INTERIM STORAGE'  THEN 4
              ELSE 1
          END                                     AS current_stage_id,
          COALESCE(sl.id, @unassigned_loc_id)     AS location_id,
          SYSUTCDATETIME()                        AS last_updated_at,
          LTRIM(RTRIM(sed.printer))               AS printer,
          TRY_CONVERT(DATETIME2, sed.date_harvest) AS date_harvest_dt,
          LTRIM(RTRIM(sed.operator_harvest))      AS operator_harvest
      FROM dbo.stg_excel_data sed
      JOIN dbo.product_types pt
        ON pt.name = LTRIM(RTRIM(sed.product))
      LEFT JOIN dbo.storage_locations sl
        ON sl.location_name = LTRIM(RTRIM(sed.storage))
      WHERE sed.product_id IS NOT NULL
        AND TRY_CAST(sed.product_id AS BIGINT) IS NOT NULL
        AND sed.filament_id IS NOT NULL
        AND TRY_CAST(sed.filament_id AS BIGINT) IS NOT NULL
        AND sed.status_quality_check IS NOT NULL
        AND LTRIM(RTRIM(sed.product)) IN (N'10K', N'6K')
  )
  INSERT INTO #src_tracking (product_id, harvest_id, product_type_id, sku_id,
                             current_status_id, previous_stage_id, current_stage_id,
                             location_id, last_updated_at)
  SELECT
      pd.product_id_bigint,
      h.id AS harvest_id,
      pd.product_type_id,
      pd.sku_id,
      pd.current_status_id,
      pd.previous_stage_id,
      pd.current_stage_id,
      pd.location_id,
      pd.last_updated_at
  FROM ProductDetails pd
  /* Match each product_id to its harvest using natural keys */
  INNER JOIN dbo.filaments f
    ON f.filament_id = pd.filament_id_bigint
  INNER JOIN dbo.printers p
    ON p.name = pd.printer
  INNER JOIN dbo.filament_mounting fm
    ON fm.filament_tracking_id = f.id
   AND fm.printer_id = p.id
  LEFT JOIN dbo.users u
    ON u.display_name = pd.operator_harvest
  INNER JOIN dbo.product_harvest h
    ON h.filament_mounting_id = fm.id
   AND h.printed_by = COALESCE(u.id, (SELECT TOP 1 id FROM dbo.users ORDER BY id))
   AND h.print_date = pd.date_harvest_dt;

  /* -------- 2) Insert idempotently into product_tracking -------- */
  INSERT INTO dbo.product_tracking
      (harvest_id, product_id, product_type_id, sku_id,
       current_status_id, previous_stage_id, current_stage_id,
       location_id, last_updated_at)
  SELECT
      s.harvest_id, s.product_id, s.product_type_id, s.sku_id,
      s.current_status_id, s.previous_stage_id, s.current_stage_id,
      s.location_id, s.last_updated_at
  FROM #src_tracking s
  WHERE NOT EXISTS (
      SELECT 1
      FROM dbo.product_tracking t
      WHERE t.product_id = s.product_id
         OR t.harvest_id = s.harvest_id
  );

  COMMIT TRAN;
  PRINT '[TRANSFORMED] product_tracking';
END TRY
BEGIN CATCH
  IF XACT_STATE() <> 0 ROLLBACK TRAN;
  DECLARE @msg NVARCHAR(4000) = ERROR_MESSAGE();
  DECLARE @num INT = ERROR_NUMBER();
  DECLARE @state INT = ERROR_STATE();
  DECLARE @sev INT = ERROR_SEVERITY();
  RAISERROR('[transform_product_tracking] %s (num=%d, state=%d, sev=%d)',
            @sev, 1, @msg, @num, @state, @sev);
END CATCH;
