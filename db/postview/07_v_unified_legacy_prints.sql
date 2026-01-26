CREATE OR ALTER VIEW dbo.vw_unified_legacy_prints
AS
WITH ValidStage AS (
    SELECT DISTINCT
        TRY_CAST(sed.product_id  AS BIGINT)      AS product_id_bigint,
        TRY_CAST(sed.filament_id AS BIGINT)      AS filament_id_bigint,
        LTRIM(RTRIM(sed.printer))                AS printer_name,
        LTRIM(RTRIM(sed.operator_harvest))       AS operator_name,
        TRY_CONVERT(DATETIME2, sed.date_harvest) AS print_date_dt,
        TRY_CONVERT(DATE,      sed.date_harvest) AS print_date_d,
        LTRIM(RTRIM(sed.product))                AS product_name,
        LTRIM(RTRIM(sed.storage))                AS storage_name,
        UPPER(LTRIM(RTRIM(sed.status_quality_check)))          AS qc,
        UPPER(LTRIM(RTRIM(ISNULL(sed.second_rate_goods, '')))) AS second_rate,
        UPPER(LTRIM(RTRIM(ISNULL(sed.prozess_step, ''))))      AS step_u
    FROM dbo.stg_excel_data sed
    WHERE sed.product_id IS NOT NULL
      AND TRY_CAST(sed.product_id AS BIGINT) IS NOT NULL
      AND sed.filament_id IS NOT NULL
      AND TRY_CAST(sed.filament_id AS BIGINT) IS NOT NULL
      AND sed.status_quality_check IS NOT NULL
      AND LTRIM(RTRIM(sed.product)) IN (N'10K', N'6K', N'CS MINI')
      AND TRY_CONVERT(date, sed.date_harvest) >= '2025-07-17'
),
Joined AS (
    SELECT
        vs.product_id_bigint,
        vs.filament_id_bigint,
        f.id  AS filament_tracking_id,
        p.id  AS printer_id,
        vs.operator_name,
        vs.print_date_dt,
        vs.print_date_d,
        vs.product_name,
        vs.storage_name,
        vs.qc,
        vs.second_rate,
        vs.step_u
    FROM ValidStage vs
    INNER JOIN dbo.filaments f ON f.filament_id = vs.filament_id_bigint
    INNER JOIN dbo.printers  p ON LTRIM(RTRIM(p.name)) = vs.printer_name
),
Mounted AS (
    SELECT
        j.*,
        fm.id AS filament_mounting_id
    FROM Joined j
    INNER JOIN dbo.filament_mounting fm
      ON fm.filament_tracking_id = j.filament_tracking_id
     AND fm.printer_id           = j.printer_id
),
Resolved AS (
    SELECT
        m.product_id_bigint,
        m.filament_id_bigint,
        m.filament_tracking_id,
        m.printer_id,
        m.filament_mounting_id,
        m.operator_name,
        COALESCE(u.id, 1) AS printed_by_id,
        m.print_date_dt,
        m.print_date_d,
        m.product_name,
        m.storage_name,
        m.qc,
        m.second_rate,
        m.step_u,
        pt.id AS product_type_id,
        (SELECT MIN(ps.id) FROM dbo.product_skus ps WHERE ps.product_type_id = pt.id) AS sku_id,
        CASE
          WHEN m.qc = 'FAIL'                         THEN (SELECT TOP 1 id FROM dbo.product_statuses WHERE status_name = N'Waste')
          WHEN m.qc = 'PASS' AND m.second_rate='YES' THEN (SELECT TOP 1 id FROM dbo.product_statuses WHERE status_name = N'B-Ware')
          WHEN m.qc = 'PASS' AND m.second_rate='NO'  THEN (SELECT TOP 1 id FROM dbo.product_statuses WHERE status_name = N'A-Ware')
          ELSE NULL
        END AS current_status_id,
        CASE m.step_u
          WHEN 'SOLD'            THEN 12
          WHEN 'SALES'           THEN 8
          WHEN 'NOT USABLE'      THEN 10
          WHEN 'INTERNAL'        THEN 13
          WHEN 'IN TREATMENT'    THEN 5
          WHEN 'INTERIM STORAGE' THEN 4
          ELSE 1
        END AS current_stage_id
    FROM Mounted m
    INNER JOIN dbo.product_types pt
      ON LTRIM(RTRIM(pt.name)) = LTRIM(RTRIM(m.product_name))
    LEFT JOIN dbo.users u
      ON u.display_name = m.operator_name
)
SELECT
    ROW_NUMBER() OVER (ORDER BY product_id_bigint) AS harvest_seq,  -- <- deterministic sequence starting at 1
    *
FROM Resolved;
