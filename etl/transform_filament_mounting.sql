/* ===========================================================
   transform_filament_mounting.sql

   Upsert filament_mounting using:
     - stg_excel_data (pairs actually used in prints)
     - stg_filament_excel_data (inventory; include filaments with no prints)

   Base selection is your working query (UsedPairs / InvPairs / Pairs).

   Rules:
     - Include only inventory rows where usage <> 'NO' (NULL allowed).
     - Status:
         'In Use'     when printer_fi present (non-empty)
         'Unmounted'  otherwise
     - remaining_weight from weight_fl (coalesced to 0.00 to satisfy NOT NULL)
     - mounted_by:
         prefer users.display_name = 'Unassigned'
         else fallback to first users.id
     - mounted_at: SYSUTCDATETIME()
     - If status = 'Unmounted', set BOTH unmounted_at and unmounted_by:
         - On INSERT: set immediately
         - On UPDATE: set when first transitioning to Unmounted (only if NULL)

   This file does not create tables.
   =========================================================== */

BEGIN TRY
  BEGIN TRAN;

  /* ---------- Resolve mounted_by (Unassigned → fallback) ---------- */
  DECLARE @mounted_by INT =
    (SELECT TOP (1) id FROM dbo.users WHERE display_name = N'Unassigned' ORDER BY id);

  IF @mounted_by IS NULL
  BEGIN
    SET @mounted_by = (SELECT TOP (1) id FROM dbo.users WITH (READPAST) ORDER BY id);
    IF @mounted_by IS NULL
      THROW 58100, 'No users present; seed dbo.users before mounting.', 1;
  END

  /* ---------- Stage source rows (based on your working query) ---------- */
  DROP TABLE IF EXISTS #src;
  CREATE TABLE #src(
    filament_tracking_id INT NOT NULL,
    printer_id           INT NOT NULL,
    remaining_weight     DECIMAL(10,2) NOT NULL,
    status               NVARCHAR(50)  NOT NULL
  );

  ;WITH UsedPairs AS (
      SELECT DISTINCT
          TRY_CAST(sed.filament_id AS BIGINT) AS filament_id_bigint,
          LTRIM(RTRIM(sed.printer))           AS printer_name
      FROM dbo.stg_excel_data sed
      WHERE sed.filament_id IS NOT NULL
        AND TRY_CAST(sed.filament_id AS BIGINT) IS NOT NULL
        AND sed.printer IS NOT NULL
        AND LTRIM(RTRIM(sed.printer)) <> N''
  ),
  InvPairs AS (
      SELECT DISTINCT
          TRY_CAST(fe.filament_id AS BIGINT)  AS filament_id_bigint,
          LTRIM(RTRIM(fe.printer_fi))         AS printer_name,
          fe.usage,
          fe.weight_fl,
          fe.printer_fi
      FROM dbo.stg_filament_excel_data fe
      WHERE fe.filament_id IS NOT NULL
        AND TRY_CAST(fe.filament_id AS BIGINT) IS NOT NULL
        AND (fe.usage IS NULL OR UPPER(LTRIM(RTRIM(fe.usage))) <> N'NO')
        AND fe.printer_fi IS NOT NULL
        AND LTRIM(RTRIM(fe.printer_fi)) <> N''
  ),
  Pairs AS (
      SELECT up.filament_id_bigint, up.printer_name
      FROM UsedPairs up
      UNION
      SELECT ip.filament_id_bigint, ip.printer_name
      FROM InvPairs ip
  ),
  Base AS (
      SELECT
          pr.filament_id_bigint                   AS filament_id_bigint,
          f.id                                    AS filament_tracking_id,
          pr.printer_name,
          p.id                                    AS printer_id,
          -- pull usage/weight/status from inventory table when available
          ip.usage,
          TRY_CAST(ip.weight_fl AS DECIMAL(10,2)) AS remaining_weight_raw,
          CASE
              WHEN ip.printer_fi IS NOT NULL AND LTRIM(RTRIM(ip.printer_fi)) <> N''
                  THEN N'In Use'
              ELSE N'Unmounted'
          END                                     AS status_calc
      FROM Pairs pr
      JOIN dbo.filaments f
        ON f.filament_id = pr.filament_id_bigint
      JOIN dbo.printers p
        ON p.name = pr.printer_name
      LEFT JOIN InvPairs ip
        ON ip.filament_id_bigint = pr.filament_id_bigint
       AND ip.printer_name       = pr.printer_name
  )
  INSERT INTO #src(filament_tracking_id, printer_id, remaining_weight, status)
  SELECT
    b.filament_tracking_id,
    b.printer_id,
    COALESCE(b.remaining_weight_raw, CONVERT(DECIMAL(10,2), 0.00)) AS remaining_weight,
    b.status_calc
  FROM Base b;

  /* ---------- Upsert into dbo.filament_mounting ---------- */
  DROP TABLE IF EXISTS #merge_outcome;
  CREATE TABLE #merge_outcome(action NVARCHAR(10) NOT NULL);

  MERGE dbo.filament_mounting AS tgt
  USING #src AS src
     ON tgt.filament_tracking_id = src.filament_tracking_id
    AND tgt.printer_id           = src.printer_id
  WHEN MATCHED THEN
    UPDATE SET
      tgt.remaining_weight = src.remaining_weight,
      tgt.status           = src.status,
      tgt.unmounted_at     = CASE
                               WHEN src.status = N'Unmounted'
                                    AND tgt.unmounted_at IS NULL
                                 THEN SYSUTCDATETIME()
                               ELSE tgt.unmounted_at
                             END,
      tgt.unmounted_by     = CASE
                               WHEN src.status = N'Unmounted'
                                    AND tgt.unmounted_by IS NULL
                                 THEN @mounted_by
                               ELSE tgt.unmounted_by
                             END
  WHEN NOT MATCHED BY TARGET THEN
    INSERT (
      filament_tracking_id,
      printer_id,
      mounted_by,
      mounted_at,
      unmounted_at,
      unmounted_by,
      remaining_weight,
      status
    )
    VALUES (
      src.filament_tracking_id,
      src.printer_id,
      @mounted_by,
      SYSUTCDATETIME(),
      CASE WHEN src.status = N'Unmounted' THEN SYSUTCDATETIME() ELSE NULL END,
      CASE WHEN src.status = N'Unmounted' THEN @mounted_by       ELSE NULL END,
      src.remaining_weight,
      src.status
    )
  OUTPUT $action INTO #merge_outcome(action);

  /* ---------- Summary ---------- */
  DECLARE @ins INT = (SELECT COUNT(*) FROM #merge_outcome WHERE action = 'INSERT');
  DECLARE @upd INT = (SELECT COUNT(*) FROM #merge_outcome WHERE action = 'UPDATE');

  COMMIT TRAN;

  PRINT CONCAT('[filament_mounting] Upsert complete. Inserted=', @ins, ', Updated=', @upd);
END TRY
BEGIN CATCH
  IF XACT_STATE() <> 0 ROLLBACK TRAN;

  DECLARE @msg NVARCHAR(4000) = ERROR_MESSAGE();
  DECLARE @num INT = ERROR_NUMBER();
  DECLARE @state INT = ERROR_STATE();
  DECLARE @sev INT = ERROR_SEVERITY();

  RAISERROR('[transform_filament_mounting] %s (num=%d, state=%d, sev=%d)',
            @sev, 1, @msg, @num, @state, @sev);
END CATCH;
