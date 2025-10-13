BEGIN TRY
  BEGIN TRAN;

  /* 0) Preconditions / helpers */
  DECLARE @fallback_user_id INT = (SELECT TOP 1 id FROM dbo.users ORDER BY id);
  IF @fallback_user_id IS NULL
    RAISERROR('No users present; seed users before loading product_quality_control.', 16, 1);

  /* 1) Build source from staging, normalize, and resolve product_id via product_tracking */
  IF OBJECT_ID('tempdb..#qc_src','U') IS NOT NULL DROP TABLE #qc_src;
  CREATE TABLE #qc_src(
    product_tracking_id INT         NOT NULL,  -- product_tracking.id
    print_date          DATETIME2   NOT NULL,  -- ph.print_date (for scoping/debug)
    inspected_at        DATETIME2   NOT NULL,
    inspected_by_id     INT         NOT NULL,
    weight_grams        DECIMAL(6,2)    NULL,
    pressure_drop       DECIMAL(6,3)    NULL,
    visual_pass_bit     BIT         NOT NULL,
    inspection_result   NVARCHAR(20) NOT NULL,  -- CHECK (Passed, B-Ware, Waste, Quarantine)
    notes               NVARCHAR(255)  NULL
  );

  ;WITH sx AS (
    SELECT
      /* Normalize tracking id to text (avoid scientific notation) */
      COALESCE(
        CONVERT(nvarchar(50), TRY_CONVERT(decimal(38,0), s.product_id)),
        NULLIF(LTRIM(RTRIM(CAST(s.product_id AS nvarchar(50)))),'')
      ) AS tracking_id_clean,

      /* Robust parse for dates */
      COALESCE(
        TRY_CONVERT(datetime2, s.date_harvest, 101),
        TRY_CONVERT(datetime2, s.date_harvest, 103),
        TRY_CONVERT(datetime2, s.date_harvest, 104),
        TRY_CONVERT(datetime2, s.date_harvest, 105),
        CASE WHEN TRY_CONVERT(float, s.date_harvest) IS NOT NULL
             THEN DATEADD(day, CAST(TRY_CONVERT(float, s.date_harvest) AS int) - 2, '1899-12-30') END,
        TRY_CONVERT(datetime2, s.date_harvest)
      ) AS print_dt,

      COALESCE(
        TRY_CONVERT(datetime2, s.date_of_quality_check, 101),
        TRY_CONVERT(datetime2, s.date_of_quality_check, 103),
        TRY_CONVERT(datetime2, s.date_of_quality_check, 104),
        TRY_CONVERT(datetime2, s.date_of_quality_check, 105),
        CASE WHEN TRY_CONVERT(float, s.date_of_quality_check) IS NOT NULL
             THEN DATEADD(day, CAST(TRY_CONVERT(float, s.date_of_quality_check) AS int) - 2, '1899-12-30') END,
        TRY_CONVERT(datetime2, s.date_of_quality_check)
      ) AS inspected_at,

      NULLIF(LTRIM(RTRIM(CAST(s.operater_quality_check AS nvarchar(200)))),'') AS inspector_legacy,

      /* Numbers that may contain commas */
      TRY_CONVERT(decimal(6,2), REPLACE(CAST(s.weight_check_g AS nvarchar(100)), ',', '.')) AS weight_grams,
      TRY_CONVERT(decimal(6,3), REPLACE(CAST(s.pressure_drop_check_mbar AS nvarchar(100)), ',', '.')) AS pressure_drop,

      UPPER(LTRIM(RTRIM(CAST(s.visual_check AS nvarchar(50))))) AS visual_check_norm,
      UPPER(LTRIM(RTRIM(CAST(s.status_quality_check AS nvarchar(50))))) AS status_qc_norm,
      UPPER(LTRIM(RTRIM(CAST(s.second_rate_goods AS nvarchar(50)))))     AS second_rate_norm,

      NULLIF(LTRIM(RTRIM(CAST(s.comment AS nvarchar(255)))),'') AS notes
    FROM dbo.stg_excel_data s
  ),
  scoped AS (
    /* Only rows where we can identify a product (tracking id) and in date window */
    SELECT *
    FROM sx
    WHERE tracking_id_clean IS NOT NULL
      AND print_dt >= '2025-07-17T00:00:00'
  ),
  j_track AS (
    /* Resolve to product_tracking via tracking_id */
    SELECT
      pt.id     AS product_tracking_id,
      ph.print_date,
      sc.inspected_at,
      sc.inspector_legacy,
      sc.weight_grams,
      sc.pressure_drop,
      sc.visual_check_norm,
      sc.status_qc_norm,
      sc.second_rate_norm,
      sc.notes
    FROM scoped sc
    JOIN dbo.product_tracking pt
      ON pt.tracking_id = sc.tracking_id_clean
    JOIN dbo.product_harvest ph
      ON ph.id = pt.harvest_id
  ),
  j_user AS (
    /* Map legacy inspector name to users.id; fallback to @fallback_user_id */
    SELECT
      jt.product_tracking_id,
      jt.print_date,
      jt.inspected_at,
      COALESCE(u.id, @fallback_user_id) AS inspected_by_id,
      jt.weight_grams,
      jt.pressure_drop,

      /* visual_check -> BIT */
      CASE
        WHEN jt.visual_check_norm IN (N'PASS', N'OK', N'PASSED', N'YES', N'Y', N'TRUE', N'1')
          THEN CAST(1 AS bit)
        WHEN jt.visual_check_norm IN (N'FAIL', N'FAILED', N'NO', N'N', N'FALSE', N'0', N'REJECT')
          THEN CAST(0 AS bit)
        ELSE CAST(0 AS bit) -- default to 0 to satisfy NOT NULL
      END AS visual_pass_bit,

      /* inspection_result per rule:
         FAIL -> Waste
         PASS + YES -> B-Ware
         PASS + NO  -> Passed
      */
      CASE
        WHEN jt.status_qc_norm = N'FAIL' THEN N'Waste'
        WHEN jt.status_qc_norm = N'PASS'
             AND jt.second_rate_norm = N'YES' THEN N'B-Ware'
        WHEN jt.status_qc_norm = N'PASS'
             AND jt.second_rate_norm = N'NO' THEN N'Passed'
        ELSE N'Passed'  -- conservative default to meet CHECK constraint
      END AS inspection_result,
      jt.notes
    FROM j_track jt
    LEFT JOIN dbo.users u
      ON u.display_name COLLATE Latin1_General_CI_AI
       = jt.inspector_legacy COLLATE Latin1_General_CI_AI
  )
  INSERT INTO #qc_src
    (product_tracking_id, print_date, inspected_at, inspected_by_id,
     weight_grams, pressure_drop, visual_pass_bit, inspection_result, notes)
  SELECT
    j.product_tracking_id, j.print_date, COALESCE(j.inspected_at, j.print_date), j.inspected_by_id,
    j.weight_grams, j.pressure_drop, j.visual_pass_bit, j.inspection_result, j.notes
  FROM j_user j;

  DECLARE @staged INT;
  SELECT @staged = COUNT(*) FROM #qc_src;
  PRINT CONCAT('[pqc] staged rows: ', @staged);

  /* 2) Idempotency: delete any existing QC rows for the scoped products */
  DELETE pqc
  FROM dbo.product_quality_control pqc
  JOIN #qc_src s ON s.product_tracking_id = pqc.product_id;

  DECLARE @deleted INT = @@ROWCOUNT;
  PRINT CONCAT('[pqc] deleted existing rows for scope: ', @deleted);

  /* 3) Insert into target */
  INSERT INTO dbo.product_quality_control
    (product_id, inspected_by, inspected_at, weight_grams, pressure_drop, visual_pass, inspection_result, notes)
  SELECT
    s.product_tracking_id,
    s.inspected_by_id,
    s.inspected_at,
    s.weight_grams,
    s.pressure_drop,
    s.visual_pass_bit,
    s.inspection_result,
    s.notes
  FROM #qc_src s;

  DECLARE @inserted INT = @@ROWCOUNT;
  PRINT CONCAT('[pqc] inserted rows: ', @inserted);

  /* 4) Sanity for the window */
  DECLARE @cnt INT = (
    SELECT COUNT(*)
    FROM dbo.product_quality_control pqc
    JOIN dbo.product_tracking pt ON pt.id = pqc.product_id
    JOIN dbo.product_harvest ph ON ph.id = pt.harvest_id
    WHERE CAST(ph.print_date AS date) >= '2025-07-17'
  );
  PRINT CONCAT('[pqc] total rows on/after 2025-07-17: ', @cnt);

  COMMIT TRAN;
END TRY
BEGIN CATCH
  IF @@TRANCOUNT > 0 ROLLBACK TRAN;

  DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
  RAISERROR('product_quality_control load failed: %s', 16, 1, @msg);
END CATCH;