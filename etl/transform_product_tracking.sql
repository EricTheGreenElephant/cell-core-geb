BEGIN TRY
  BEGIN TRAN;

  /* 0) Preconditions (fail fast) */
  IF NOT EXISTS (SELECT 1 FROM dbo.lifecycle_stages WHERE id = 4)
    RAISERROR('Lifecycle stage id=4 missing.', 16, 1);

  IF NOT EXISTS (SELECT 1 FROM dbo.product_skus WHERE id = 1)
    RAISERROR('Expected SKU id=1 missing.', 16, 1);
  IF NOT EXISTS (SELECT 1 FROM dbo.product_skus WHERE id = 2)
    RAISERROR('Expected SKU id=2 missing.', 16, 1);

  DECLARE @status_a INT = (SELECT TOP 1 id FROM dbo.product_statuses WHERE status_name = N'A-Ware');
  DECLARE @status_b INT = (SELECT TOP 1 id FROM dbo.product_statuses WHERE status_name = N'B-Ware');

  IF @status_a IS NULL OR @status_b IS NULL
    RAISERROR('Expected product_statuses A-Ware / B-Ware missing.', 16, 1);

  DECLARE @fixed_current_stage_id INT = 4;   -- QMTreatmentApproval
  DECLARE @fixed_location_id     INT = 23;   -- Unassigned

  /* 1) Delete any existing target rows in the window (simplifies idempotency) */
  DELETE pt
  FROM dbo.product_tracking pt
  JOIN dbo.product_harvest ph ON ph.id = pt.harvest_id
  WHERE CAST(ph.print_date AS date) >= '2025-07-17';

  PRINT CONCAT('[product_tracking] deleted rows in window: ', @@ROWCOUNT);

  /* 2) Build mapped source rows and insert */
  ;WITH src AS (
    SELECT
      NULLIF(LTRIM(RTRIM(CAST(sx.filament_id AS nvarchar(200)))),'') AS filament_serial,
      COALESCE(
        TRY_CONVERT(datetime2, sx.date_harvest, 101),
        TRY_CONVERT(datetime2, sx.date_harvest, 103),
        TRY_CONVERT(datetime2, sx.date_harvest, 104),
        TRY_CONVERT(datetime2, sx.date_harvest, 105),
        CASE WHEN TRY_CONVERT(float, sx.date_harvest) IS NOT NULL
             THEN DATEADD(day, CAST(TRY_CONVERT(float, sx.date_harvest) AS int) - 2, '1899-12-30') END,
        TRY_CONVERT(datetime2, sx.date_harvest)
      ) AS print_dt,

      /* tracking_id as clean NVARCHAR (avoid scientific notation in any client) */
      COALESCE(
        CONVERT(nvarchar(50), TRY_CONVERT(decimal(38,0), sx.product_id)),
        NULLIF(LTRIM(RTRIM(CAST(sx.product_id AS nvarchar(50)))),'')
      ) AS tracking_id_clean,

      /* normalize product & second_rate flag */
      UPPER(REPLACE(REPLACE(REPLACE(REPLACE(LTRIM(RTRIM(CAST(sx.product AS nvarchar(100)))), NCHAR(160), N''), CHAR(13), ''), CHAR(10), ''), CHAR(9), '')) AS product_norm,
      UPPER(LTRIM(RTRIM(CAST(sx.second_rate_goods AS nvarchar(50))))) AS second_rate_norm
    FROM dbo.stg_excel_data sx
  ),
  scoped AS (
    SELECT *
    FROM src
    WHERE filament_serial IS NOT NULL
      AND tracking_id_clean IS NOT NULL
      AND print_dt >= '2025-07-17T00:00:00'
  ),
  j_filament AS (
    SELECT s.*, f.id AS filament_id
    FROM scoped s
    JOIN dbo.filaments f
      ON f.serial_number = s.filament_serial
  ),
  j_mount AS (
    SELECT jf.*, fm.id AS filament_mounting_id
    FROM j_filament jf
    JOIN dbo.filament_mounting fm
      ON fm.filament_id = jf.filament_id
  ),
  j_harvest AS (
    SELECT
      jm.tracking_id_clean,
      jm.product_norm,
      jm.second_rate_norm,
      ph.id AS harvest_id,
      ph.print_date
    FROM j_mount jm
    JOIN dbo.product_harvest ph
      ON ph.filament_mounting_id = jm.filament_mounting_id
     AND CAST(ph.print_date AS date) = CAST(jm.print_dt AS date)
  ),
  mapped AS (
    SELECT
      jh.harvest_id,
      jh.tracking_id_clean AS tracking_id,
      CASE WHEN jh.product_norm = N'10K' THEN 1
           WHEN jh.product_norm = N'6K'  THEN 2
           ELSE 1 END AS product_type_id,
      CASE WHEN jh.product_norm = N'10K' THEN 1
           WHEN jh.product_norm = N'6K'  THEN 2
           ELSE 1 END AS sku_id,
      CASE
        WHEN jh.second_rate_norm = N'NO'  THEN @status_a
        WHEN jh.second_rate_norm = N'YES' THEN @status_b
        ELSE NULL
      END AS current_status_id,
      @fixed_current_stage_id AS current_stage_id,
      @fixed_location_id      AS location_id,
      GETDATE()               AS last_updated_at
    FROM j_harvest jh
  )
  INSERT INTO dbo.product_tracking
    (harvest_id, tracking_id, product_type_id, sku_id, current_status_id,
     previous_stage_id, current_stage_id, location_id, last_updated_at)
  SELECT
    m.harvest_id,
    m.tracking_id,
    m.product_type_id,
    m.sku_id,
    m.current_status_id,
    NULL AS previous_stage_id,
    m.current_stage_id,
    m.location_id,
    m.last_updated_at
  FROM mapped m;

  PRINT CONCAT('[product_tracking] inserted rows: ', @@ROWCOUNT);

  /* 3) Post-insert sanity */
  DECLARE @cnt INT = (
    SELECT COUNT(*)
    FROM dbo.product_tracking t
    JOIN dbo.product_harvest ph ON ph.id = t.harvest_id
    WHERE CAST(ph.print_date AS date) >= '2025-07-17'
  );
  PRINT CONCAT('[product_tracking] rows on/after 2025-07-17: ', @cnt);

  COMMIT TRAN;
END TRY
BEGIN CATCH
  IF @@TRANCOUNT > 0 ROLLBACK TRAN;

  DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
  RAISERROR('product_tracking load failed: %s', 16, 1, @msg);
END CATCH;