-- /* ===========================================================
--    etl/transform_product_tracking.sql

--    Backbone (your working chain):
--      stg_excel_data (ValidProducts)

--    Writes:
--      dbo.product_tracking  (MERGE by product_id)
--    =========================================================== */

SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
  BEGIN TRAN;

  DECLARE @unassigned_loc_id INT = (SELECT TOP 1 id FROM dbo.storage_locations WHERE location_name = N'Unassigned');
  IF @unassigned_loc_id IS NULL
  BEGIN
    INSERT dbo.storage_locations(location_name, location_type, description, is_active)
    VALUES (N'Unassigned', N'Virtual', N'Fallback for product tracking', 1);
    SET @unassigned_loc_id = SCOPE_IDENTITY();
  END

  IF OBJECT_ID('tempdb..#src','U') IS NOT NULL DROP TABLE #src;
  CREATE TABLE #src(
    product_id_bigint  BIGINT NOT NULL PRIMARY KEY,
    harvest_id         INT    NOT NULL,
    product_type_id    INT    NOT NULL,
    sku_id             INT    NOT NULL,
    current_status_id  INT    NULL,
    previous_stage_id  INT    NULL,
    current_stage_id   INT    NOT NULL,
    location_id        INT    NULL,
    last_updated_at    DATETIME2 NOT NULL
  );

  INSERT INTO #src(product_id_bigint, harvest_id, product_type_id, sku_id,
                   current_status_id, previous_stage_id, current_stage_id,
                   location_id, last_updated_at)
  SELECT
      v.product_id_bigint,
      m.harvest_id,
      v.product_type_id,
      v.sku_id,
      v.current_status_id,
      NULL,
      v.current_stage_id,
      COALESCE(sl.id, @unassigned_loc_id),
      SYSUTCDATETIME()
  FROM dbo.vw_unified_legacy_prints v
  JOIN dbo.etl_harvest_map m
    ON m.product_id_bigint = v.product_id_bigint
  LEFT JOIN dbo.storage_locations sl
    ON sl.location_name = v.storage_name;

  IF OBJECT_ID('tempdb..#out','U') IS NOT NULL DROP TABLE #out;
  CREATE TABLE #out(action NVARCHAR(10));

  MERGE dbo.product_tracking AS tgt
  USING #src AS src
     ON tgt.product_id = src.product_id_bigint
  WHEN MATCHED THEN
    UPDATE SET
      tgt.harvest_id        = src.harvest_id,
      tgt.product_type_id   = src.product_type_id,
      tgt.sku_id            = src.sku_id,
      tgt.current_status_id = src.current_status_id,
      tgt.current_stage_id  = src.current_stage_id,
      tgt.location_id       = src.location_id,
      tgt.last_updated_at   = src.last_updated_at
  WHEN NOT MATCHED BY TARGET THEN
    INSERT (harvest_id, product_id, product_type_id, sku_id, current_status_id,
            previous_stage_id, current_stage_id, location_id, last_updated_at)
    VALUES (src.harvest_id, src.product_id_bigint, src.product_type_id, src.sku_id,
            src.current_status_id, src.previous_stage_id, src.current_stage_id,
            src.location_id, src.last_updated_at)
  OUTPUT $action INTO #out(action);

  COMMIT TRAN;
  PRINT '[product_tracking_from_unified] done.';
END TRY
BEGIN CATCH
  IF XACT_STATE() <> 0 ROLLBACK TRAN;
  DECLARE @msg NVARCHAR(4000) = ERROR_MESSAGE();
  RAISERROR('[product_tracking_from_unified] %s', 16, 1, @msg);
END CATCH;
