/* ===========================================================
   etl/transform_filament_acclimatization.sql

   Goal:
     Add/maintain rows in dbo.filament_acclimatization for filaments
     currently in the "AIR LOCK" location in staging.

   Rules:
     - Source table: dbo.stg_filament_excel_data
     - Only rows where shelf == "AIR LOCK" (case- and space-tolerant)
     - Resolve filament_tracking_id via filaments.filament_id (business key)
     - moved_by = user id 1 (fallback to first user if id 1 missing)
     - moved_at = current UTC time
     - status   = 'Acclimatizing'
     - One row per filament (unique on filament_tracking_id); idempotent

   Notes:
     - ready_at is a computed column (moved_at + 2 days), so no need to set it.
   =========================================================== */

SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
  BEGIN TRAN;

  /* ---------- 0) Resolve moved_by (prefer id = 1) ---------- */
  DECLARE @moved_by INT = (SELECT id FROM dbo.users WHERE id = 1);
  IF @moved_by IS NULL
  BEGIN
    SET @moved_by = (SELECT TOP (1) id FROM dbo.users WITH (READPAST) ORDER BY id);
    IF @moved_by IS NULL
      RAISERROR('No users present; seed dbo.users before filament_acclimatization.', 16, 1);
  END

  /* ---------- 1) Stage qualifying filaments from staging ---------- */
  IF OBJECT_ID('tempdb..#src_accl','U') IS NOT NULL DROP TABLE #src_accl;
  CREATE TABLE #src_accl(
    filament_tracking_id INT PRIMARY KEY
  );

  ;WITH Base AS (
    SELECT
      -- Robust numeric parse for filament_id (handles commas/scientific)
      filament_id_bigint = COALESCE(
        TRY_CONVERT(BIGINT, fe.filament_id),
        TRY_CONVERT(BIGINT, REPLACE(CONVERT(NVARCHAR(100), fe.filament_id), ',', '')),
        TRY_CONVERT(BIGINT, CONVERT(DECIMAL(38,0), TRY_CONVERT(float, fe.filament_id)))
      ),
      shelf_norm = UPPER(LTRIM(RTRIM(CONVERT(NVARCHAR(200), fe.shelf))))
    FROM dbo.stg_filament_excel_data fe
  ),
  AirLock AS (
    SELECT DISTINCT filament_id_bigint
    FROM Base
    WHERE filament_id_bigint IS NOT NULL
      AND shelf_norm = N'AIR LOCK'
  )
  INSERT INTO #src_accl(filament_tracking_id)
  SELECT f.id
  FROM AirLock a
  JOIN dbo.filaments f
    ON f.filament_id = a.filament_id_bigint;

  /* ---------- 2) Upsert into dbo.filament_acclimatization ---------- */
  IF OBJECT_ID('tempdb..#merge_outcome','U') IS NOT NULL DROP TABLE #merge_outcome;
  CREATE TABLE #merge_outcome(action NVARCHAR(10) NOT NULL);

  MERGE dbo.filament_acclimatization AS tgt
  USING #src_accl AS src
     ON tgt.filament_tracking_id = src.filament_tracking_id
  WHEN MATCHED THEN
    -- No changes by default to preserve original moved_at; uncomment if you want to refresh
    -- UPDATE SET
    --   tgt.moved_by = @moved_by,
    --   tgt.moved_at = SYSUTCDATETIME(),
    --   tgt.status   = N'Acclimatizing'
    UPDATE SET filament_tracking_id = tgt.filament_tracking_id  -- no-op to satisfy MERGE syntax
  WHEN NOT MATCHED BY TARGET THEN
    INSERT (filament_tracking_id, moved_by, moved_at, status)
    VALUES (src.filament_tracking_id, @moved_by, SYSUTCDATETIME(), N'Acclimatizing')
  OUTPUT $action INTO #merge_outcome(action);

  DECLARE @ins INT = (SELECT COUNT(*) FROM #merge_outcome WHERE action = 'INSERT');
  DECLARE @upd INT = (SELECT COUNT(*) FROM #merge_outcome WHERE action = 'UPDATE');

  COMMIT TRAN;

  PRINT CONCAT('[filament_acclimatization] Upsert complete. Inserted=', @ins, ', Updated=', @upd);

END TRY
BEGIN CATCH
  IF XACT_STATE() <> 0 ROLLBACK TRAN;
  DECLARE @msg NVARCHAR(4000) = ERROR_MESSAGE();
  RAISERROR('[transform_filament_acclimatization] %s', 16, 1, @msg);
END CATCH;
