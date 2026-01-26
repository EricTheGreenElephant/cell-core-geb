/* ===========================================================
   transform_etl_harvest_map.sql
   Purpose: Populate/refresh a 1:1 map product_id -> harvest_id
            using ONLY (operator_harvest -> users.display_name) and date_harvest.

   Rules:
   - For each product_id (10K/6K + your required filters), take the EARLIEST staging row.
   - Try to match an existing product_harvest by:
       product_harvest.printed_by = users.id(operator_harvest trimmed, fallback to any user)
       AND product_harvest.print_date = staging.date_harvest
     (No filament / printer / mounting involved.)
   - If a matching harvest is found and is not yet used by another product in the map: reuse it.
   - If the matching harvest is already used: CLONE that harvest row (duplicate values)
     so the new product_id gets its own unique harvest_id.
   - If NO matching harvest exists: (by design) SKIP mapping for that product_id
     and print diagnostics (we don't fabricate a new harvest because that would
     need a mounting id; your product_harvest transform should have created all
     real harvests already).

   Idempotent and safe to re-run.
   =========================================================== */

BEGIN TRY
  BEGIN TRAN;

  DECLARE @CutoffDate date = '2025-07-17';

  IF OBJECT_ID('dbo.etl_harvest_map','U') IS NULL
    THROW 50301, 'etl_harvest_map missing; create it in migrations first.', 1;

  /* --- pick earliest qualifying staging row per product --- */
  IF OBJECT_ID('tempdb..#pick') IS NOT NULL DROP TABLE #pick;
  ;WITH Valid AS (
    SELECT
      TRY_CAST(product_id  AS BIGINT)                  AS product_id_bigint,
      TRY_CAST(filament_id AS BIGINT)                  AS filament_id_bigint, -- validated per global rule
      TRY_CONVERT(DATETIME2, date_harvest)             AS print_date_dt,
      LTRIM(RTRIM(operator_harvest))                   AS operator_trim,
      LTRIM(RTRIM(product))                            AS product_trim
    FROM dbo.stg_excel_data
    WHERE product IN (N'10K', N'6K', N'CS MINI')
      AND status_quality_check IS NOT NULL
      AND product      IS NOT NULL
      AND printer      IS NOT NULL         
      AND date_harvest IS NOT NULL
      AND TRY_CAST(product_id  AS BIGINT) IS NOT NULL
      AND TRY_CAST(filament_id AS BIGINT) IS NOT NULL
      AND TRY_CONVERT(date, date_harvest) >= @CutoffDate
  ),
  Ranked AS (
    SELECT v.*,
           ROW_NUMBER() OVER (PARTITION BY v.product_id_bigint ORDER BY v.print_date_dt ASC) AS rn
    FROM Valid v
  )
  SELECT *
  INTO #pick
  FROM Ranked
  WHERE rn = 1;

  DECLARE @n_products INT = (SELECT COUNT(*) FROM #pick);
  PRINT CONCAT('[etl_harvest_map] qualified products (earliest per id): ', @n_products);

  IF @n_products = 0
  BEGIN
    COMMIT TRAN;
    PRINT '[etl_harvest_map] done (no qualifying products).';
    RETURN;
  END

  /* --- resolve operator to printed_by user id (trimmed) --- */
  IF OBJECT_ID('tempdb..#pick_u') IS NOT NULL DROP TABLE #pick_u;
  DECLARE @fallback_user_id INT = (SELECT TOP(1) id FROM dbo.users ORDER BY id);
  IF @fallback_user_id IS NULL
    THROW 50302, 'No users present; seed users first.', 1;

  SELECT
    p.*,
    COALESCE(u.id, @fallback_user_id) AS printed_by_id
  INTO #pick_u
  FROM #pick p
  LEFT JOIN dbo.users u
    ON u.display_name = p.operator_trim;

  /* --- match existing harvests by (printed_by, print_date) ONLY --- */
  IF OBJECT_ID('tempdb..#matches') IS NOT NULL DROP TABLE #matches;
  SELECT
    pu.product_id_bigint,
    h.id AS harvest_id
  INTO #matches
  FROM #pick_u pu
  JOIN dbo.product_harvest h
    ON h.printed_by = pu.printed_by_id
   AND h.print_date = pu.print_date_dt;

  DECLARE @n_matched INT = (SELECT COUNT(*) FROM #matches);
  PRINT CONCAT('[etl_harvest_map] products with a (printed_by, print_date) harvest: ', @n_matched);

  /* --- (A) Reuse free matches: map if harvest_id not yet used in the map --- */
  MERGE dbo.etl_harvest_map AS tgt
  USING (
    SELECT m.product_id_bigint, m.harvest_id
    FROM #matches m
    WHERE NOT EXISTS (SELECT 1 FROM dbo.etl_harvest_map mm WHERE mm.harvest_id = m.harvest_id)
  ) AS src(product_id_bigint, harvest_id)
  ON tgt.product_id_bigint = src.product_id_bigint
  WHEN NOT MATCHED THEN
    INSERT (product_id_bigint, harvest_id) VALUES (src.product_id_bigint, src.harvest_id);

  DECLARE @n_reused INT = @@ROWCOUNT;
  PRINT CONCAT('[etl_harvest_map] reused free harvests mapped: ', @n_reused);

  /* --- (B) Clone when the matching harvest is already used by someone else --- */
  IF OBJECT_ID('tempdb..#need_clone') IS NOT NULL DROP TABLE #need_clone;
  SELECT
    pu.product_id_bigint,
    m.harvest_id AS base_harvest_id
  INTO #need_clone
  FROM #matches m
  JOIN #pick_u pu
    ON pu.product_id_bigint = m.product_id_bigint
  WHERE NOT EXISTS (SELECT 1 FROM dbo.etl_harvest_map map WHERE map.product_id_bigint = m.product_id_bigint) -- not mapped yet
    AND EXISTS (SELECT 1 FROM dbo.etl_harvest_map map2 WHERE map2.harvest_id      = m.harvest_id);          -- but harvest already used

  DECLARE @n_need_clone INT = (SELECT COUNT(*) FROM #need_clone);
  PRINT CONCAT('[etl_harvest_map] products needing CLONE harvest: ', @n_need_clone);

  IF @n_need_clone > 0
  BEGIN
    IF OBJECT_ID('tempdb..#cloned') IS NOT NULL DROP TABLE #cloned;
    CREATE TABLE #cloned(product_id_bigint BIGINT NOT NULL, harvest_id INT NOT NULL);

    INSERT INTO dbo.product_harvest (request_id, lid_id, seal_id, filament_mounting_id, printed_by, print_date)
    OUTPUT nc.product_id_bigint, inserted.id INTO #cloned(product_id_bigint, harvest_id)
    SELECT
      h.request_id,
      h.lid_id,
      h.seal_id,
      /* we copy the original row as-is; we are NOT using mounting to decide anything */
      h.filament_mounting_id,
      h.printed_by,
      h.print_date
    FROM #need_clone nc
    JOIN dbo.product_harvest h ON h.id = nc.base_harvest_id;

    MERGE dbo.etl_harvest_map AS tgt
    USING #cloned AS src
      ON tgt.product_id_bigint = src.product_id_bigint
    WHEN NOT MATCHED THEN
      INSERT (product_id_bigint, harvest_id) VALUES (src.product_id_bigint, src.harvest_id);

    PRINT CONCAT('[etl_harvest_map] cloned harvests created & mapped: ', @@ROWCOUNT);
  END

  /* --- (C) Report products that still lack a harvest match (operator+date) --- */
  IF OBJECT_ID('tempdb..#unmapped') IS NOT NULL DROP TABLE #unmapped;
  SELECT pu.product_id_bigint, pu.operator_trim, pu.print_date_dt
  INTO #unmapped
  FROM #pick_u pu
  LEFT JOIN dbo.etl_harvest_map mm ON mm.product_id_bigint = pu.product_id_bigint
  WHERE mm.product_id_bigint IS NULL;

  DECLARE @n_unmapped INT = (SELECT COUNT(*) FROM #unmapped);
  PRINT CONCAT('[etl_harvest_map] products still UNMAPPED (no operator+date harvest found): ', @n_unmapped);

  COMMIT TRAN;
  PRINT '[TRANSFORMED] etl_harvest_map done';
END TRY
BEGIN CATCH
  IF XACT_STATE() <> 0 ROLLBACK TRAN;
  DECLARE @msg NVARCHAR(4000) = ERROR_MESSAGE();
  RAISERROR('[transform_etl_harvest_map] %s', 16, 1, @msg);
END CATCH;
