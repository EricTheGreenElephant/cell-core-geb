/* ===========================================================
   etl/transform_post_treatment_inspections.sql

   Source: dbo.stg_excel_data
   Target: dbo.post_treatment_inspections

   Rules:
     - product_tracking_id: join dbo.product_tracking via stg.product_id (BIGINT) like other transforms
     - inspected_by:   map stg.operator_visual_check_incoming_goods → users.display_name; fallback to first user id
     - inspected_at:   stg.date_of_visual_check_incoming_goods (robust date parse)
     - visual_pass:    stg.visual_check_1 = 'PASS' => 1 else 0
     - surface_treated: stg.surface_treatment = 'PASS' => 1 else 0
     - sterilized:     stg.sterilization = 'PASS' => 1 else 0
     - qc_result:      if visual_check_1 = 'PASS' then 'Passed' else 'B-Ware'
     - notes:          stg.comment

   Matching key (idempotence):
     MERGE on (product_tracking_id, inspected_at)

   Preconditions:
     - product_tracking already populated (joins by product_id BIGINT)
     - users table has at least one row (fallback)
   =========================================================== */

SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
  BEGIN TRAN;

  DECLARE @CutoffDate date = '2025-07-17';

  /* ---------- 0) Fallback user ---------- */
  DECLARE @fallback_user_id INT =
    (SELECT TOP (1) id FROM dbo.users WITH (READPAST) ORDER BY id);
  IF @fallback_user_id IS NULL
    RAISERROR('No users present; seed dbo.users before post_treatment_inspections.', 16, 1);

  /* ---------- 1) Stage normalized rows ---------- */
  IF OBJECT_ID('tempdb..#src_pti','U') IS NOT NULL DROP TABLE #src_pti;
  CREATE TABLE #src_pti(
    product_tracking_id INT         NOT NULL,
    inspected_by        INT         NOT NULL,
    inspected_at        DATETIME2   NOT NULL,
    visual_pass         BIT         NOT NULL,
    surface_treated     BIT         NOT NULL,
    sterilized          BIT         NOT NULL,
    qc_result           NVARCHAR(20) NOT NULL,
    notes               NVARCHAR(255) NULL,
    PRIMARY KEY(product_tracking_id, inspected_at)
  );

  ;WITH Raw AS (
    SELECT
      TRY_CAST(sed.product_id AS BIGINT) AS product_id_bigint,
      LTRIM(RTRIM(CAST(sed.operator_visual_check_incoming_goods AS NVARCHAR(200)))) AS operator_name,

      /* robust-ish date parse; try a few formats + Excel serial */
      COALESCE(
        TRY_CONVERT(DATETIME2, sed.date_of_visual_check_incoming_goods, 104),  -- dd.mm.yyyy
        TRY_CONVERT(DATETIME2, sed.date_of_visual_check_incoming_goods, 105),  -- dd-mm-yyyy
        TRY_CONVERT(DATETIME2, sed.date_of_visual_check_incoming_goods, 101),  -- mm/dd/yyyy
        TRY_CONVERT(DATETIME2, sed.date_of_visual_check_incoming_goods, 103),  -- dd/mm/yyyy
        CASE WHEN TRY_CONVERT(float, sed.date_of_visual_check_incoming_goods) IS NOT NULL
             THEN DATEADD(day, CAST(TRY_CONVERT(float, sed.date_of_visual_check_incoming_goods) AS int) - 2, '1899-12-30')
        END,
        TRY_CONVERT(DATETIME2, sed.date_of_visual_check_incoming_goods)
      ) AS inspected_at_dt,

      UPPER(LTRIM(RTRIM(CAST(sed.visual_check_1    AS NVARCHAR(50))))) AS visual_chk_1,
      UPPER(LTRIM(RTRIM(CAST(sed.surface_treatment AS NVARCHAR(50))))) AS surface_treat,
      UPPER(LTRIM(RTRIM(CAST(sed.sterilization     AS NVARCHAR(50))))) AS sterilization_chk,

      CAST(sed.comment AS NVARCHAR(255)) AS notes
    FROM dbo.stg_excel_data sed
    WHERE sed.product_id IS NOT NULL
      AND TRY_CAST(sed.product_id AS BIGINT) IS NOT NULL
      AND sed.date_of_visual_check_incoming_goods IS NOT NULL
      AND LTRIM(RTRIM(sed.product)) IN (N'10K', N'6K', N'CS MINI')
      AND TRY_CONVERT(date, sed.date_harvest) >= @CutoffDate
  ),
  Mapped AS (
    SELECT
      t.id AS product_tracking_id,
      COALESCE(u.id, @fallback_user_id) AS inspected_by,
      r.inspected_at_dt AS inspected_at,

      CASE WHEN r.visual_chk_1 = 'PASS' THEN CAST(1 AS BIT) ELSE CAST(0 AS BIT) END AS visual_pass,
      CASE WHEN r.surface_treat = 'YES' THEN CAST(1 AS BIT) ELSE CAST(0 AS BIT) END AS surface_treated,
      CASE WHEN r.sterilization_chk = 'YES' THEN CAST(1 AS BIT) ELSE CAST(0 AS BIT) END AS sterilized,

      CASE WHEN r.visual_chk_1 = 'PASS' THEN N'Passed' ELSE N'B-Ware' END AS qc_result,

      r.notes
    FROM Raw r
    INNER JOIN dbo.product_tracking t
      ON t.product_id = r.product_id_bigint
    LEFT JOIN dbo.users u
      ON u.display_name = r.operator_name
    WHERE r.inspected_at_dt IS NOT NULL
  )
  INSERT INTO #src_pti(
    product_tracking_id, inspected_by, inspected_at,
    visual_pass, surface_treated, sterilized,
    qc_result, notes
  )
  SELECT
    m.product_tracking_id,
    m.inspected_by,
    m.inspected_at,
    m.visual_pass,
    m.surface_treated,
    m.sterilized,
    m.qc_result,
    m.notes
  FROM Mapped m;

  /* ---------- 2) Upsert into dbo.post_treatment_inspections ---------- */
  IF OBJECT_ID('tempdb..#merge_outcome','U') IS NOT NULL DROP TABLE #merge_outcome;
  CREATE TABLE #merge_outcome(action NVARCHAR(10) NOT NULL);

  MERGE dbo.post_treatment_inspections AS tgt
  USING #src_pti AS src
     ON tgt.product_tracking_id = src.product_tracking_id
    AND tgt.inspected_at        = src.inspected_at
  WHEN MATCHED THEN
    UPDATE SET
      tgt.inspected_by    = src.inspected_by,
      tgt.visual_pass     = src.visual_pass,
      tgt.surface_treated = src.surface_treated,
      tgt.sterilized      = src.sterilized,
      tgt.qc_result       = src.qc_result,
      tgt.notes           = src.notes
  WHEN NOT MATCHED BY TARGET THEN
    INSERT (
      product_tracking_id, inspected_by, inspected_at,
      visual_pass, surface_treated, sterilized,
      qc_result, notes
    )
    VALUES (
      src.product_tracking_id, src.inspected_by, src.inspected_at,
      src.visual_pass, src.surface_treated, src.sterilized,
      src.qc_result, src.notes
    )
  OUTPUT $action INTO #merge_outcome(action);

  DECLARE @ins INT = (SELECT COUNT(*) FROM #merge_outcome WHERE action = 'INSERT');
  DECLARE @upd INT = (SELECT COUNT(*) FROM #merge_outcome WHERE action = 'UPDATE');

  COMMIT TRAN;

  PRINT CONCAT('[post_treatment_inspections] Upsert complete. Inserted=', @ins, ', Updated=', @upd);

END TRY
BEGIN CATCH
  IF XACT_STATE() <> 0 ROLLBACK TRAN;
  DECLARE @msg NVARCHAR(4000) = ERROR_MESSAGE();
  RAISERROR('[transform_post_treatment_inspections] %s', 16, 1, @msg);
END CATCH;
