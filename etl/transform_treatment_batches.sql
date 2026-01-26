-- /* ===========================================================
--    etl/transform_treatment_batches.sql  (NVARCHAR-key; "YES" only)

--    Builds:
--      - dbo.treatment_batches
--      - dbo.treatment_batch_products

--    Staging:
--      - dbo.stg_treatment_excel_data (treatment_id, in_treatment)
--      - dbo.stg_excel_data           (transfer_id, product_id)

--    Rules:
--      - Create one batch per distinct treatment_id where TRIM(UPPER(in_treatment)) = 'YES'.
--        sent_by = user id 1 (fallback to first user), sent_at = SYSUTCDATETIME()
--        received_at = NULL, notes = NULL, status = 'Shipped'
--      - For each treatment, add products with transfer_id equal to that treatment_id (both normalized to NVARCHAR).
--        Resolve product_tracking_id via product_id (BIGINT) → product_tracking(product_id)
--        surface_treat = 1, sterilize = 1

--    Idempotence:
--      - Uses dbo.etl_treatment_map2 (treatment_key NVARCHAR(100) PK, batch_id UNIQUE)
--        to prevent duplicate batches across runs.
--    =========================================================== */

-- SET NOCOUNT ON;
-- SET XACT_ABORT ON;

-- BEGIN TRY
--   BEGIN TRAN;

--   DECLARE @CutoffDate date = '2025-07-17';

--   /* ---------- 0) Helper map table (NVARCHAR key) ---------- */
--   IF OBJECT_ID('dbo.etl_treatment_map2','U') IS NULL
--   BEGIN
--     CREATE TABLE dbo.etl_treatment_map2 (
--       treatment_key NVARCHAR(100) NOT NULL PRIMARY KEY,
--       batch_id      INT           NOT NULL UNIQUE,
--       CONSTRAINT fk_etl_treat2_batch
--         FOREIGN KEY (batch_id) REFERENCES dbo.treatment_batches(id)
--     );
--   END

--   /* ---------- 1) Resolve sender (prefer id=1) ---------- */
--   DECLARE @sent_by INT = (SELECT id FROM dbo.users WHERE id = 1);
--   IF @sent_by IS NULL
--   BEGIN
--     SET @sent_by = (SELECT TOP (1) id FROM dbo.users WITH (READPAST) ORDER BY id);
--     IF @sent_by IS NULL
--       RAISERROR('No users present; seed dbo.users before treatment batches.', 16, 1);
--   END

--   /* ---------- 2) Stage distinct treatment keys with in_treatment='YES' ---------- */
--   IF OBJECT_ID('tempdb..#treat','U') IS NOT NULL DROP TABLE #treat;
--   CREATE TABLE #treat(
--     treatment_key NVARCHAR(100) NOT NULL PRIMARY KEY
--   );

--   ;WITH base AS (
--     SELECT
--       key_txt = UPPER(LTRIM(RTRIM(REPLACE(REPLACE(CONVERT(NVARCHAR(100), t.treatment_id), CHAR(160), ' '), CHAR(9), ' ')))),
--       flag    = UPPER(LTRIM(RTRIM(REPLACE(REPLACE(CONVERT(NVARCHAR(50),  t.in_treatment), CHAR(160), ' '), CHAR(9), ' '))))
--     FROM dbo.stg_treatment_excel_data t
--   )
--   INSERT INTO #treat(treatment_key)
--   SELECT DISTINCT b.key_txt
--   FROM base b
--   WHERE b.key_txt IS NOT NULL AND b.key_txt <> N''
--     AND b.flag = N'YES';

--   /* Early exit if nothing to do */
--   IF NOT EXISTS (SELECT 1 FROM #treat)
--   BEGIN
--     PRINT '[treatment_batches] No in_treatment = YES rows found in staging.';
--     COMMIT TRAN;
--     RETURN;
--   END

--   /* ---------- 3) Load existing mappings for those keys ---------- */
--   IF OBJECT_ID('tempdb..#map','U') IS NOT NULL DROP TABLE #map;
--   CREATE TABLE #map(
--     treatment_key NVARCHAR(100) NOT NULL PRIMARY KEY,
--     batch_id      INT           NULL
--   );

--   INSERT INTO #map(treatment_key, batch_id)
--   SELECT t.treatment_key, m.batch_id
--   FROM #treat t
--   LEFT JOIN dbo.etl_treatment_map2 m ON m.treatment_key = t.treatment_key;

--   /* ---------- 4) Insert missing batches via MERGE; capture ids ---------- */
--   IF OBJECT_ID('tempdb..#new_batches','U') IS NOT NULL DROP TABLE #new_batches;
--   CREATE TABLE #new_batches(
--     treatment_key NVARCHAR(100) NOT NULL PRIMARY KEY,
--     batch_id      INT           NOT NULL
--   );

--   MERGE dbo.treatment_batches AS tgt
--   USING (
--     SELECT treatment_key FROM #map WHERE batch_id IS NULL
--   ) AS src
--   ON 1 = 0  -- force INSERT for all src rows
--   WHEN NOT MATCHED THEN
--     INSERT (sent_by, sent_at, received_at, notes, status)
--     VALUES (@sent_by, SYSUTCDATETIME(), NULL, NULL, N'Shipped')
--   OUTPUT src.treatment_key, inserted.id
--   INTO #new_batches(treatment_key, batch_id);

--   /* Persist new mappings (skip if concurrent writer already did) */
--   INSERT INTO dbo.etl_treatment_map2(treatment_key, batch_id)
--   SELECT nb.treatment_key, nb.batch_id
--   FROM #new_batches nb
--   WHERE NOT EXISTS (SELECT 1 FROM dbo.etl_treatment_map2 m WHERE m.treatment_key = nb.treatment_key)
--     AND NOT EXISTS (SELECT 1 FROM dbo.etl_treatment_map2 m WHERE m.batch_id      = nb.batch_id);

--   /* Refresh #map with newly created batch ids */
--   UPDATE m
--     SET m.batch_id = COALESCE(m.batch_id, nb.batch_id)
--   FROM #map m
--   LEFT JOIN #new_batches nb
--     ON nb.treatment_key = m.treatment_key;

--   /* ---------- 5) Stage products per treatment key ---------- */
--   IF OBJECT_ID('tempdb..#prod','U') IS NOT NULL DROP TABLE #prod;
--   CREATE TABLE #prod(
--     treatment_key        NVARCHAR(100) NOT NULL,
--     product_tracking_id  INT           NOT NULL,
--     PRIMARY KEY (treatment_key, product_tracking_id)
--   );

--   ;WITH x AS (
--     SELECT
--       transfer_key = UPPER(LTRIM(RTRIM(REPLACE(REPLACE(CONVERT(NVARCHAR(100), s.transfer_id), CHAR(160), ' '), CHAR(9), ' ')))),
--       product_id_bigint = TRY_CONVERT(BIGINT, s.product_id)
--     FROM dbo.stg_excel_data s
--     WHERE s.transfer_id IS NOT NULL
--       AND s.product_id  IS NOT NULL
--       AND TRY_CONVERT(date, s.date_harvest) >= @CutoffDate
--   )
--   INSERT INTO #prod(treatment_key, product_tracking_id)
--   SELECT DISTINCT
--       x.transfer_key,
--       pt.id  -- product_tracking_id
--   FROM x
--   JOIN dbo.product_tracking pt
--     ON pt.product_id = x.product_id_bigint
--   WHERE x.transfer_key IN (SELECT treatment_key FROM #map);

--   /* ---------- 6) Insert missing treatment_batch_products ---------- */
--   INSERT INTO dbo.treatment_batch_products (batch_id, product_tracking_id, surface_treat, sterilize)
--   SELECT
--       m.batch_id,
--       p.product_tracking_id,
--       CAST(1 AS BIT) AS surface_treat,
--       CAST(1 AS BIT) AS sterilize
--   FROM #prod p
--   JOIN #map m
--     ON m.treatment_key = p.treatment_key
--   WHERE m.batch_id IS NOT NULL
--     AND NOT EXISTS (
--       SELECT 1
--       FROM dbo.treatment_batch_products tbp
--       WHERE tbp.product_tracking_id = p.product_tracking_id
--     );

--   COMMIT TRAN;

--   DECLARE @newb INT = (SELECT COUNT(*) FROM #new_batches);
--   PRINT CONCAT('[treatment_batches] New batches inserted: ', @newb);
--   PRINT     '[treatment_batch_products] Insert complete (idempotent).';

-- END TRY
-- BEGIN CATCH
--   IF XACT_STATE() <> 0 ROLLBACK TRAN;
--   DECLARE @msg NVARCHAR(4000) = ERROR_MESSAGE();
--   RAISERROR('[transform_treatment_batches] %s', 16, 1, @msg);
-- END CATCH;


/* ===========================================================
   etl/transform_treatment_batches.sql  (NVARCHAR-key; rule-aligned)

   Builds:
     - dbo.treatment_batches
     - dbo.treatment_batch_products

   Staging:
     - dbo.stg_treatment_excel_data (treatment_id, in_treatment, run_date, operator)
     - dbo.stg_excel_data           (transfer_id, product_id, date_harvest, date_of_visual_check_incoming_goods)

   Key changes vs prior version:
     - Apply cutoff using stg_treatment_excel_data.run_date for treatment selection
     - Only include treatment_ids that exist in stg_excel_data.transfer_id (also cutoff-scoped)
     - sent_at comes from run_date
     - received_at derived only for AT GEB batches from stg_excel_data.date_of_visual_check_incoming_goods
     - status derived from in_treatment
     - ignore in_treatment = NO
   =========================================================== */

SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
  BEGIN TRAN;

  DECLARE @CutoffDate date = '2025-07-17';

  /* ---------- 0) Helper map table (NVARCHAR key) ---------- */
  IF OBJECT_ID('dbo.etl_treatment_map2','U') IS NULL
  BEGIN
    CREATE TABLE dbo.etl_treatment_map2 (
      treatment_key NVARCHAR(100) NOT NULL PRIMARY KEY,
      batch_id      INT           NOT NULL UNIQUE,
      CONSTRAINT fk_etl_treat2_batch
        FOREIGN KEY (batch_id) REFERENCES dbo.treatment_batches(id)
    );
  END

  /* ---------- 1) Resolve sender (legacy/system user) ---------- */
  DECLARE @sent_by INT = (SELECT id FROM dbo.users WHERE user_principal_name = N'legacy-import@system');
  IF @sent_by IS NULL
  BEGIN
    -- fallback to first user if legacy-import@system not present
    SET @sent_by = (SELECT TOP (1) id FROM dbo.users WITH (READPAST) ORDER BY id);
    IF @sent_by IS NULL
      RAISERROR('No users present; seed dbo.users before treatment batches.', 16, 1);
  END

  /* ---------- 2) Stage eligible treatments (cutoff + must exist in stg_excel_data.transfer_id) ---------- */
  IF OBJECT_ID('tempdb..#treat','U') IS NOT NULL DROP TABLE #treat;
  CREATE TABLE #treat(
    treatment_key NVARCHAR(100) NOT NULL PRIMARY KEY,
    sent_at       DATETIME2     NOT NULL,
    status        NVARCHAR(50)  NOT NULL,
    notes         NVARCHAR(255) NULL
  );

  ;WITH T AS (
    SELECT
      treatment_key = UPPER(LTRIM(RTRIM(REPLACE(REPLACE(CONVERT(NVARCHAR(100), t.treatment_id), CHAR(160), ' '), CHAR(9), ' ')))),
      in_treat      = UPPER(LTRIM(RTRIM(REPLACE(REPLACE(CONVERT(NVARCHAR(50),  t.in_treatment), CHAR(160), ' '), CHAR(9), ' ')))),
      operator_name = LTRIM(RTRIM(CONVERT(NVARCHAR(200), t.[operator]))), -- if your column name differs, adjust here
      sent_at_dt    = COALESCE(
                      TRY_CONVERT(DATETIME2, t.run_date, 104),
                      TRY_CONVERT(DATETIME2, t.run_date, 105),
                      TRY_CONVERT(DATETIME2, t.run_date, 101),
                      TRY_CONVERT(DATETIME2, t.run_date, 103),
                      CASE WHEN TRY_CONVERT(float, t.run_date) IS NOT NULL
                           THEN DATEADD(day, CAST(TRY_CONVERT(float, t.run_date) AS int) - 2, '1899-12-30')
                      END,
                      TRY_CONVERT(DATETIME2, t.run_date)
                    )
    FROM dbo.stg_treatment_excel_data t
  ),
  Xfer AS (
    /* transfer_id keys that exist in product staging (also cutoff-scoped) */
    SELECT DISTINCT
      transfer_key = UPPER(LTRIM(RTRIM(REPLACE(REPLACE(CONVERT(NVARCHAR(100), s.transfer_id), CHAR(160), ' '), CHAR(9), ' '))))
    FROM dbo.stg_excel_data s
    WHERE s.transfer_id IS NOT NULL
      AND TRY_CONVERT(date, s.date_harvest) >= @CutoffDate
  )
  INSERT INTO #treat(treatment_key, sent_at, status, notes)
  SELECT DISTINCT
    t.treatment_key,
    t.sent_at_dt,
    CASE
      WHEN t.in_treat = N'AT GEB' THEN N'Inspected'
      WHEN t.in_treat IN (N'AT BBF', N'YES') THEN N'Shipped'
      ELSE NULL
    END AS status,
    LEFT(CONCAT(N'LegacyTreatmentID=', t.treatment_key,
                CASE WHEN NULLIF(t.operator_name, N'') IS NOT NULL THEN CONCAT(N'; Operator=', t.operator_name) ELSE N'' END),
         255) AS notes
  FROM T t
  INNER JOIN Xfer x
    ON x.transfer_key = t.treatment_key
  WHERE t.treatment_key IS NOT NULL AND t.treatment_key <> N''
    AND t.sent_at_dt IS NOT NULL
    AND TRY_CONVERT(date, t.sent_at_dt) >= @CutoffDate
    AND t.in_treat <> N'NO'
    AND (
      t.in_treat IN (N'AT GEB', N'AT BBF', N'YES')
    );

  /* Early exit if nothing to do */
  IF NOT EXISTS (SELECT 1 FROM #treat)
  BEGIN
    PRINT '[treatment_batches] No eligible treatments found (cutoff + transfer match + status rules).';
    COMMIT TRAN;
    RETURN;
  END

  /* ---------- 3) Load existing mappings ---------- */
  IF OBJECT_ID('tempdb..#map','U') IS NOT NULL DROP TABLE #map;
  CREATE TABLE #map(
    treatment_key NVARCHAR(100) NOT NULL PRIMARY KEY,
    batch_id      INT           NULL
  );

  INSERT INTO #map(treatment_key, batch_id)
  SELECT t.treatment_key, m.batch_id
  FROM #treat t
  LEFT JOIN dbo.etl_treatment_map2 m ON m.treatment_key = t.treatment_key;

  /* ---------- 4) Insert missing batches; capture ids ---------- */
  IF OBJECT_ID('tempdb..#new_batches','U') IS NOT NULL DROP TABLE #new_batches;
  CREATE TABLE #new_batches(
    treatment_key NVARCHAR(100) NOT NULL PRIMARY KEY,
    batch_id      INT           NOT NULL
  );

  MERGE dbo.treatment_batches AS tgt
  USING (
    SELECT t.treatment_key, t.sent_at, t.status, t.notes
    FROM #treat t
    JOIN #map  m ON m.treatment_key = t.treatment_key
    WHERE m.batch_id IS NULL
  ) AS src
  ON 1 = 0
  WHEN NOT MATCHED THEN
    INSERT (sent_by, sent_at, received_at, notes, status)
    VALUES (
      @sent_by,
      src.sent_at,
      NULL,          -- received_at is handled below (only for AT GEB)
      src.notes,
      src.status
    )
  OUTPUT src.treatment_key, inserted.id
  INTO #new_batches(treatment_key, batch_id);

  /* Persist new mappings */
  INSERT INTO dbo.etl_treatment_map2(treatment_key, batch_id)
  SELECT nb.treatment_key, nb.batch_id
  FROM #new_batches nb
  WHERE NOT EXISTS (SELECT 1 FROM dbo.etl_treatment_map2 m WHERE m.treatment_key = nb.treatment_key);

  /* Refresh #map with new ids */
  UPDATE m
    SET m.batch_id = COALESCE(m.batch_id, nb.batch_id)
  FROM #map m
  LEFT JOIN #new_batches nb
    ON nb.treatment_key = m.treatment_key;

  /* ---------- 4b) Set received_at for AT GEB batches ---------- */
  ;WITH recv AS (
    SELECT
      treatment_key = UPPER(LTRIM(RTRIM(REPLACE(REPLACE(CONVERT(NVARCHAR(100), s.transfer_id), CHAR(160), ' '), CHAR(9), ' ')))),
      received_at_dt = MIN(
        COALESCE(
          TRY_CONVERT(DATETIME2, s.date_of_visual_check_incoming_goods, 104),
          TRY_CONVERT(DATETIME2, s.date_of_visual_check_incoming_goods, 105),
          TRY_CONVERT(DATETIME2, s.date_of_visual_check_incoming_goods, 101),
          TRY_CONVERT(DATETIME2, s.date_of_visual_check_incoming_goods, 103),
          CASE WHEN TRY_CONVERT(float, s.date_of_visual_check_incoming_goods) IS NOT NULL
               THEN DATEADD(day, CAST(TRY_CONVERT(float, s.date_of_visual_check_incoming_goods) AS int) - 2, '1899-12-30')
          END,
          TRY_CONVERT(DATETIME2, s.date_of_visual_check_incoming_goods)
        )
      )
    FROM dbo.stg_excel_data s
    WHERE s.transfer_id IS NOT NULL
      AND TRY_CONVERT(date, s.date_harvest) >= @CutoffDate
      AND s.date_of_visual_check_incoming_goods IS NOT NULL
    GROUP BY UPPER(LTRIM(RTRIM(REPLACE(REPLACE(CONVERT(NVARCHAR(100), s.transfer_id), CHAR(160), ' '), CHAR(9), ' '))))
  )
  UPDATE tb
    SET tb.received_at = r.received_at_dt
  FROM dbo.treatment_batches tb
  JOIN #map m
    ON m.batch_id = tb.id
  JOIN #treat t
    ON t.treatment_key = m.treatment_key
  JOIN recv r
    ON r.treatment_key = t.treatment_key
  WHERE t.status = N'Inspected'
    AND r.received_at_dt IS NOT NULL;

  /* ---------- 5) Stage products per treatment key ---------- */
  IF OBJECT_ID('tempdb..#prod','U') IS NOT NULL DROP TABLE #prod;
  CREATE TABLE #prod(
    treatment_key        NVARCHAR(100) NOT NULL,
    product_tracking_id  INT           NOT NULL,
    PRIMARY KEY (treatment_key, product_tracking_id)
  );

  ;WITH x AS (
    SELECT
      transfer_key = UPPER(LTRIM(RTRIM(REPLACE(REPLACE(CONVERT(NVARCHAR(100), s.transfer_id), CHAR(160), ' '), CHAR(9), ' ')))),
      product_id_bigint = TRY_CONVERT(BIGINT, s.product_id)
    FROM dbo.stg_excel_data s
    WHERE s.transfer_id IS NOT NULL
      AND s.product_id  IS NOT NULL
      AND TRY_CONVERT(date, s.date_harvest) >= @CutoffDate
  )
  INSERT INTO #prod(treatment_key, product_tracking_id)
  SELECT DISTINCT
      x.transfer_key,
      pt.id
  FROM x
  JOIN dbo.product_tracking pt
    ON pt.product_id = x.product_id_bigint
  WHERE x.transfer_key IN (SELECT treatment_key FROM #map);

  /* ---------- 6) Insert missing treatment_batch_products ---------- */
  INSERT INTO dbo.treatment_batch_products (batch_id, product_tracking_id, surface_treat, sterilize)
  SELECT
      m.batch_id,
      p.product_tracking_id,
      CAST(1 AS BIT) AS surface_treat,   -- default assumption: treatment implies both
      CAST(1 AS BIT) AS sterilize
  FROM #prod p
  JOIN #map m
    ON m.treatment_key = p.treatment_key
  WHERE m.batch_id IS NOT NULL
    AND NOT EXISTS (
      SELECT 1
      FROM dbo.treatment_batch_products tbp
      WHERE tbp.product_tracking_id = p.product_tracking_id
    );

  COMMIT TRAN;

  DECLARE @newb INT = (SELECT COUNT(*) FROM #new_batches);
  PRINT CONCAT('[treatment_batches] New batches inserted: ', @newb);
  PRINT     '[treatment_batch_products] Insert complete (idempotent).';

END TRY
BEGIN CATCH
  IF XACT_STATE() <> 0 ROLLBACK TRAN;
  DECLARE @msg NVARCHAR(4000) = ERROR_MESSAGE();
  RAISERROR('[transform_treatment_batches] %s', 16, 1, @msg);
END CATCH;
