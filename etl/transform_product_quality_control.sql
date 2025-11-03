/* ===========================================================
   etl/transform_product_quality_control.sql

   Source: dbo.stg_excel_data
   Target: dbo.product_quality_control

   Rules (from you):
     - inspected_by:   map stg.operator_quality_check → users.display_name; fallback to user id 1
     - inspected_at:   stg.date_of_quality_check
     - weight_grams:   stg.weight_check_g
     - pressure_drop:  stg.pressure_drop_check_mbar
     - visual_pass:    stg.visual_check → 'FAIL' => 0; else 1
     - inspection_result:
         if status_quality_check IS NULL or 'FAIL':
             if second_rate_goods='NO'  => 'Waste'
             if second_rate_goods='YES' => 'B-Ware'
         if status_quality_check='PASS':
             if second_rate_goods='YES' => 'B-Ware'
             else                       => 'Passed'
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

  /* ---------- 0) Fallback user ---------- */
  DECLARE @fallback_user_id INT =
    (SELECT TOP (1) id FROM dbo.users WITH (READPAST) ORDER BY id);
  IF @fallback_user_id IS NULL
    RAISERROR('No users present; seed dbo.users before product_quality_control.', 16, 1);

  /* ---------- 1) Stage normalized rows ---------- */
  IF OBJECT_ID('tempdb..#src_qc','U') IS NOT NULL DROP TABLE #src_qc;
  CREATE TABLE #src_qc(
    product_tracking_id INT        NOT NULL,
    inspected_by        INT        NOT NULL,
    inspected_at        DATETIME2  NOT NULL,
    weight_grams        DECIMAL(6,2)  NOT NULL,
    pressure_drop       DECIMAL(6,3)  NOT NULL,
    visual_pass         BIT        NOT NULL,
    inspection_result   NVARCHAR(20) NOT NULL,
    notes               NVARCHAR(255) NULL,
    PRIMARY KEY(product_tracking_id, inspected_at)
  );

  ;WITH Raw AS (
    SELECT
      TRY_CAST(sed.product_id AS BIGINT)                        AS product_id_bigint,
      LTRIM(RTRIM(CAST(sed.operater_quality_check AS NVARCHAR(200)))) AS operator_name,
      /* robust-ish date parse; try a few formats + Excel serial */
      COALESCE(
        TRY_CONVERT(DATETIME2, sed.date_of_quality_check, 104),  -- dd.mm.yyyy
        TRY_CONVERT(DATETIME2, sed.date_of_quality_check, 105),  -- dd-mm-yyyy
        TRY_CONVERT(DATETIME2, sed.date_of_quality_check, 101),  -- mm/dd/yyyy
        TRY_CONVERT(DATETIME2, sed.date_of_quality_check, 103),  -- dd/mm/yyyy
        CASE WHEN TRY_CONVERT(float, sed.date_of_quality_check) IS NOT NULL
             THEN DATEADD(day, CAST(TRY_CONVERT(float, sed.date_of_quality_check) AS int) - 2, '1899-12-30')
        END,
        TRY_CONVERT(DATETIME2, sed.date_of_quality_check)
      )                                                          AS inspected_at_dt,
      /* decimals may come with comma → dot */
      TRY_CONVERT(DECIMAL(6,2), REPLACE(CAST(sed.weight_check_g AS NVARCHAR(50)), ',', '.'))       AS weight_grams_dec,
      TRY_CONVERT(DECIMAL(6,3), REPLACE(CAST(sed.pressure_drop_check_mbar AS NVARCHAR(50)), ',', '.')) AS pressure_drop_dec,
      UPPER(LTRIM(RTRIM(CAST(sed.visual_check AS NVARCHAR(50)))))          AS visual_chk,
      UPPER(LTRIM(RTRIM(CAST(sed.status_quality_check AS NVARCHAR(50)))))  AS status_qc,
      UPPER(LTRIM(RTRIM(CAST(ISNULL(sed.second_rate_goods,'') AS NVARCHAR(50))))) AS second_rate,
      CAST(sed.comment AS NVARCHAR(255))                                   AS notes
    FROM dbo.stg_excel_data sed
    WHERE sed.product_id IS NOT NULL
      AND TRY_CAST(sed.product_id AS BIGINT) IS NOT NULL
      AND sed.date_of_quality_check IS NOT NULL
      AND sed.weight_check_g IS NOT NULL
      AND sed.pressure_drop_check_mbar IS NOT NULL
      AND LTRIM(RTRIM(sed.product)) IN (N'10K', N'6K')  -- keep same scope
  ),
  Mapped AS (
    SELECT
      t.id AS product_tracking_id,
      COALESCE(u.id, @fallback_user_id)                    AS inspected_by,
      r.inspected_at_dt                                    AS inspected_at,
      COALESCE(r.weight_grams_dec, 0.00)                   AS weight_grams,
      COALESCE(r.pressure_drop_dec, 0.000)                 AS pressure_drop,
      CASE WHEN r.visual_chk = 'FAIL' THEN CAST(0 AS BIT) ELSE CAST(1 AS BIT) END AS visual_pass,
      CASE
        WHEN r.status_qc IS NULL OR r.status_qc = 'FAIL' THEN
          CASE
            WHEN r.second_rate = 'NO'  THEN N'Waste'
            WHEN r.second_rate = 'YES' THEN N'B-Ware'
            ELSE N'Waste'  -- conservative default if FAIL but second_rate unknown
          END
        WHEN r.status_qc = 'PASS' THEN
          CASE
            WHEN r.second_rate = 'YES' THEN N'B-Ware'
            ELSE N'Passed'
          END
        ELSE N'Passed'
      END AS inspection_result,
      r.notes
    FROM Raw r
    /* product_tracking link via legacy product_id */
    INNER JOIN dbo.product_tracking t
      ON t.product_id = r.product_id_bigint
    LEFT JOIN dbo.users u
      ON u.display_name = r.operator_name
    WHERE r.inspected_at_dt IS NOT NULL
      AND r.weight_grams_dec  IS NOT NULL
      AND r.pressure_drop_dec IS NOT NULL
  )
  INSERT INTO #src_qc(product_tracking_id, inspected_by, inspected_at, weight_grams, pressure_drop, visual_pass, inspection_result, notes)
  SELECT
    m.product_tracking_id,
    m.inspected_by,
    m.inspected_at,
    m.weight_grams,
    m.pressure_drop,
    m.visual_pass,
    m.inspection_result,
    m.notes
  FROM Mapped m;

  /* ---------- 2) Upsert into dbo.product_quality_control ---------- */
  IF OBJECT_ID('tempdb..#merge_outcome','U') IS NOT NULL DROP TABLE #merge_outcome;
  CREATE TABLE #merge_outcome(action NVARCHAR(10) NOT NULL);

  MERGE dbo.product_quality_control AS tgt
  USING #src_qc AS src
     ON tgt.product_tracking_id = src.product_tracking_id
    AND tgt.inspected_at        = src.inspected_at
  WHEN MATCHED THEN
    UPDATE SET
      tgt.inspected_by      = src.inspected_by,
      tgt.weight_grams      = src.weight_grams,
      tgt.pressure_drop     = src.pressure_drop,
      tgt.visual_pass       = src.visual_pass,
      tgt.inspection_result = src.inspection_result,
      tgt.notes             = src.notes
  WHEN NOT MATCHED BY TARGET THEN
    INSERT (product_tracking_id, inspected_by, inspected_at, weight_grams, pressure_drop, visual_pass, inspection_result, notes)
    VALUES (src.product_tracking_id, src.inspected_by, src.inspected_at, src.weight_grams, src.pressure_drop, src.visual_pass, src.inspection_result, src.notes)
  OUTPUT $action INTO #merge_outcome(action);

  DECLARE @ins INT = (SELECT COUNT(*) FROM #merge_outcome WHERE action = 'INSERT');
  DECLARE @upd INT = (SELECT COUNT(*) FROM #merge_outcome WHERE action = 'UPDATE');

  COMMIT TRAN;

  PRINT CONCAT('[product_quality_control] Upsert complete. Inserted=', @ins, ', Updated=', @upd);

END TRY
BEGIN CATCH
  IF XACT_STATE() <> 0 ROLLBACK TRAN;
  DECLARE @msg NVARCHAR(4000) = ERROR_MESSAGE();
  RAISERROR('[transform_product_quality_control] %s', 16, 1, @msg);
END CATCH;
