/* ===========================================================
   db/postseed/920_update_discarded_waste.sql

   Rules enforced:
   1) If v_product_status.location_name = 'Waste' then
        - product_tracking.current_stage_id  = lifecycle_stages('Discarded Product')
        - product_tracking.current_status_id = product_statuses('Waste')

   2) If product_tracking.current_stage = 'Discarded Product' then
        - product_tracking.current_status_id = product_statuses('Waste')
        - product_tracking.location_id       = storage_locations('Waste')

   3) If product_tracking.current_stage IN
        ('In Treatment / Shipped; Pending Return', 'Shipped to Customer')
        - product_tracking.location_id       = storage_locations('Offsite')

   Notes:
   - Creates missing 'Waste' / 'Offsite' storage locations if needed.
   - No GO statements; idempotent updates only.
   =========================================================== */

SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
  BEGIN TRAN;

  /* ---------- Resolve target IDs ---------- */
  DECLARE @stage_discarded INT =
    (SELECT TOP 1 id FROM dbo.lifecycle_stages
     WHERE stage_name = N'Discarded Product' OR stage_code = N'DISCARDED_PRODUCT');
  IF @stage_discarded IS NULL
    RAISERROR('Lifecycle stage "Discarded Product" not found.', 16, 1);

  DECLARE @status_waste INT =
    (SELECT TOP 1 id FROM dbo.product_statuses WHERE status_name = N'Waste');
  IF @status_waste IS NULL
    RAISERROR('Product status "Waste" not found.', 16, 1);

  DECLARE @loc_waste INT =
    (SELECT TOP 1 id FROM dbo.storage_locations WHERE location_name = N'Waste');
  IF @loc_waste IS NULL
  BEGIN
    INSERT dbo.storage_locations(location_name, location_type, description, is_active)
    VALUES (N'Waste', N'Virtual', N'Auto-created for discarded products', 1);
    SET @loc_waste = SCOPE_IDENTITY();
  END

  DECLARE @loc_offsite INT =
    (SELECT TOP 1 id FROM dbo.storage_locations WHERE location_name = N'Offsite');
  IF @loc_offsite IS NULL
  BEGIN
    INSERT dbo.storage_locations(location_name, location_type, description, is_active)
    VALUES (N'Offsite', N'Virtual', N'Auto-created for offsite handling', 1);
    SET @loc_offsite = SCOPE_IDENTITY();
  END

  /* ---------- Rule 1: VIEW says location is 'Waste' -> force Discarded + Waste ---------- */
  UPDATE pt
  SET
      pt.current_stage_id  = @stage_discarded,
      pt.current_status_id = @status_waste,
      pt.last_updated_at   = SYSUTCDATETIME()
  FROM dbo.product_tracking pt
  JOIN dbo.v_product_status v
    ON v.id = pt.id
  WHERE v.location_name = N'Waste'
    AND (pt.current_stage_id  IS NULL OR pt.current_stage_id  <> @stage_discarded
      OR pt.current_status_id IS NULL OR pt.current_status_id <> @status_waste);

  /* ---------- Rule 2: If stage is Discarded -> set status & location to Waste ---------- */
  UPDATE pt
  SET
      pt.current_status_id = @status_waste,
      pt.location_id       = @loc_waste,
      pt.last_updated_at   = SYSUTCDATETIME()
  FROM dbo.product_tracking pt
  JOIN dbo.lifecycle_stages ls
    ON ls.id = pt.current_stage_id
  WHERE (ls.stage_name = N'Discarded Product' OR ls.stage_code = N'DISCARDED_PRODUCT')
    AND (pt.current_status_id IS NULL OR pt.current_status_id <> @status_waste
      OR pt.location_id       IS NULL OR pt.location_id       <> @loc_waste);

  /* ---------- Rule 3: If stage is shipped (to treatment or customer) -> location Offsite ---------- */
  UPDATE pt
  SET
      pt.location_id     = @loc_offsite,
      pt.last_updated_at = SYSUTCDATETIME()
  FROM dbo.product_tracking pt
  JOIN dbo.lifecycle_stages ls
    ON ls.id = pt.current_stage_id
  WHERE ls.stage_name IN (N'In Treatment / Shipped; Pending Return', N'Shipped to Customer')
    AND (pt.location_id IS NULL OR pt.location_id <> @loc_offsite);

  COMMIT TRAN;

  PRINT '[postseed/update_discarded_waste] updates applied.';

END TRY
BEGIN CATCH
  IF XACT_STATE() <> 0 ROLLBACK TRAN;
  DECLARE @msg NVARCHAR(4000) = ERROR_MESSAGE();
  RAISERROR('[postseed/update_discarded_waste] %s', 16, 1, @msg);
END CATCH;
