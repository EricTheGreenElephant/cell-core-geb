/* etl/transform_product_quality_control.sql */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
  BEGIN TRAN;

  /* ---------- 0) Preconditions ---------- */
  DECLARE @fallback_user_id INT = (SELECT TOP 1 id FROM dbo.users ORDER BY id);
  IF @fallback_user_id IS NULL
    THROW 62010, 'Seed users first.', 1;

  /* ---------- 1) Stage scoped rows from Excel ---------- */
  IF OBJECT_ID('tempdb..#qc_src','U') IS NOT NULL DROP TABLE #qc_src;
  CREATE TABLE #qc_src(
    product_tracking_id INT           NOT NULL,  -- FK to product_tracking.id
    inspected_at        DATETIME2     NOT NULL,
    inspected_by        INT           NOT NULL,
    weight_grams        DECIMAL(6,2)  NOT NULL,
    pressure_drop       DECIMAL(6,3)  NOT NULL,
    visual_pass         BIT           NOT NULL,
    inspection_result   NVARCHAR(20)  NOT NULL,
    notes               NVARCHAR(255) NULL
  );

  IF OBJECT_ID('tempdb..#scoped','U') IS NOT NULL DROP TABLE #scoped;
  CREATE TABLE #scoped(
    pid              BIGINT        NOT NULL,   -- business ID from Excel (product_id)
    inspected_at     DATETIME2     NOT NULL,
    inspector_legacy NVARCHAR(200) NULL,
    weight_grams     DECIMAL(6,2)  NULL,
    pressure_drop    DECIMAL(6,3)  NULL,
    visual_norm      NVARCHAR(50)  NULL,
    status_norm      NVARCHAR(50)  NULL,
    second_rate_norm NVARCHAR(50)  NULL,
    notes            NVARCHAR(255) NULL
  );

  ;WITH raw AS (
    SELECT
      /* robust parse of external product id (Excel) */
      COALESCE(
        TRY_CONVERT(BIGINT, NULLIF(LTRIM(RTRIM(CAST(s.product_id AS NVARCHAR(200)))),'') ),
        TRY_CONVERT(BIGINT, REPLACE(NULLIF(LTRIM(RTRIM(CAST(s.product_id AS NVARCHAR(200)))),''), ',', '')),
        TRY_CONVERT(BIGINT, CONVERT(DECIMAL(38,0), TRY_CONVERT(float, NULLIF(LTRIM(RTRIM(CAST(s.product_id AS NVARCHAR(200)))),''))))
      ) AS pid,
      /* QC date */
      COALESCE(
        TRY_CONVERT(datetime2, s.date_of_quality_check, 101),
        TRY_CONVERT(datetime2, s.date_of_quality_check, 103),
        TRY_CONVERT(datetime2, s.date_of_quality_check, 104),
        TRY_CONVERT(datetime2, s.date_of_quality_check, 105),
        CASE WHEN TRY_CONVERT(float, s.date_of_quality_check) IS NOT NULL
             THEN DATEADD(day, CAST(TRY_CONVERT(float, s.date_of_quality_check) AS int) - 2, '1899-12-30') END,
        TRY_CONVERT(datetime2, s.date_of_quality_check)
      ) AS inspected_at,
      NULLIF(LTRIM(RTRIM(CAST(s.operater_quality_check AS NVARCHAR(200)))),'') AS inspector_legacy,
      TRY_CONVERT(DECIMAL(6,2), REPLACE(CAST(s.weight_check_g AS NVARCHAR(100)), ',', '.'))          AS weight_grams,
      TRY_CONVERT(DECIMAL(6,3), REPLACE(CAST(s.pressure_drop_check_mbar AS NVARCHAR(100)), ',', '.')) AS pressure_drop,
      UPPER(LTRIM(RTRIM(CAST(s.visual_check AS NVARCHAR(50)))))          AS visual_norm,
      UPPER(LTRIM(RTRIM(CAST(s.status_quality_check AS NVARCHAR(50)))))  AS status_norm,
      UPPER(LTRIM(RTRIM(CAST(s.second_rate_goods AS NVARCHAR(50)))))     AS second_rate_norm,
      NULLIF(LTRIM(RTRIM(CAST(s.comment AS NVARCHAR(255)))),'')          AS notes
    FROM dbo.stg_excel_data s
  )
  INSERT INTO #scoped(pid, inspected_at, inspector_legacy, weight_grams, pressure_drop, visual_norm, status_norm, second_rate_norm, notes)
  SELECT r.pid, r.inspected_at, r.inspector_legacy, r.weight_grams, r.pressure_drop,
         r.visual_norm, r.status_norm, r.second_rate_norm, r.notes
  FROM raw r
  WHERE r.pid IS NOT NULL
    AND r.inspected_at IS NOT NULL;

  /* ---------- 2) Detect business-ID column on product_tracking ---------- */
  DECLARE @join_col sysname;
  IF EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID(N'dbo.product_tracking') AND name = N'product_id')
    SET @join_col = N'product_id';
  ELSE IF EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID(N'dbo.product_tracking') AND name = N'tracking_id')
    SET @join_col = N'tracking_id';
  ELSE
    THROW 62020, 'product_tracking has neither product_id nor tracking_id. Add a BIGINT business-id column.', 1;

  /* ---------- 3) Resolve product_tracking_id + inspector; enforce NOT NULL numerics ---------- */
  DECLARE @sql NVARCHAR(MAX) = N'
    ;WITH j_pt AS (
      SELECT
        pt.id AS product_tracking_id,
        sc.inspected_at,
        sc.inspector_legacy,
        sc.weight_grams,
        sc.pressure_drop,
        sc.visual_norm,
        sc.status_norm,
        sc.second_rate_norm,
        sc.notes
      FROM #scoped sc
      JOIN dbo.product_tracking pt
        ON pt.' + QUOTENAME(@join_col) + N' = sc.pid
    ),
    j_user AS (
      SELECT
        j.product_tracking_id,
        j.inspected_at,
        COALESCE(u.id, @fallback_user_id) AS inspected_by,
        COALESCE(j.weight_grams,  0.00)  AS weight_grams,   -- enforce NOT NULL
        COALESCE(j.pressure_drop, 0.000) AS pressure_drop,  -- enforce NOT NULL
        CASE
          WHEN j.visual_norm IN (N''PASS'',N''OK'',N''PASSED'',N''YES'',N''Y'',N''TRUE'',N''1'') THEN CAST(1 AS bit)
          WHEN j.visual_norm IN (N''FAIL'',N''FAILED'',N''NO'',N''N'',N''FALSE'',N''0'',N''REJECT'') THEN CAST(0 AS bit)
          ELSE CAST(0 AS bit)
        END AS visual_pass,
        CASE
          WHEN j.status_norm = N''FAIL'' THEN N''Waste''
          WHEN j.status_norm = N''PASS'' AND j.second_rate_norm = N''YES'' THEN N''B-Ware''
          WHEN j.status_norm = N''PASS'' AND j.second_rate_norm = N''NO''  THEN N''Passed''
          ELSE N''Passed''
        END AS inspection_result,
        j.notes
      FROM j_pt j
      LEFT JOIN dbo.users u
        ON u.display_name COLLATE Latin1_General_CI_AI
         = j.inspector_legacy COLLATE Latin1_General_CI_AI
    )
    INSERT INTO #qc_src(product_tracking_id, inspected_at, inspected_by, weight_grams, pressure_drop, visual_pass, inspection_result, notes)
    SELECT product_tracking_id, inspected_at, inspected_by, weight_grams, pressure_drop, visual_pass, inspection_result, notes
    FROM j_user;
  ';
  EXEC sys.sp_executesql @sql, N'@fallback_user_id INT', @fallback_user_id=@fallback_user_id;

  /* ---------- 4) Idempotent load into target ---------- */
  -- Delete existing QC rows for the staged products
  DELETE pqc
  FROM dbo.product_quality_control pqc
  JOIN #qc_src s ON s.product_tracking_id = pqc.product_tracking_id;

  -- Insert fresh rows
  INSERT INTO dbo.product_quality_control
    (product_tracking_id, inspected_by, inspected_at, weight_grams, pressure_drop, visual_pass, inspection_result, notes)
  SELECT product_tracking_id, inspected_by, inspected_at, weight_grams, pressure_drop, visual_pass, inspection_result, notes
  FROM #qc_src;

  COMMIT TRAN;

  DECLARE @ins INT = @@ROWCOUNT;
  PRINT CONCAT('[pqc] upserted rows: ', @ins);

END TRY
BEGIN CATCH
  IF @@TRANCOUNT > 0 ROLLBACK TRAN;
  DECLARE @msg NVARCHAR(4000) = ERROR_MESSAGE();
  RAISERROR('product_quality_control transform failed: %s', 16, 1, @msg);
END CATCH;
