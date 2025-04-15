CREATE VIEW v_filament_status AS 
SELECT 
    f.id AS filament_id,
    f.serial_number,
    f.weight_grams,
    fm.remaining_weight
    CASE
        WHEN fm.remaining_weight IS NULL THEN 'Available'
        WHEN fm.remaining_weight < 200 THEN 'Replace'
        WHEN fm.remaining_weight < 650 THEN 'Low'
        ELSE 'OK'
    END AS usage_status,
    fa.ready_at,
    fm.status AS mounted_status
FROM filaments f
LEFT JOIN filament_acclimatization fa ON f.id = fa.filament_id
LEFT JOIN filament_mounting fm ON f.id = fm.filament_id;