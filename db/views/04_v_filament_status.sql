CREATE OR ALTER VIEW v_filament_status AS
SELECT
    f.id AS filament_id,
    f.serial_number,
    f.weight_grams AS initial_weight,
    f.qc_result,
    f.received_at,
    u.display_name AS received_by_name,
    sl.location_name,

    -- Derived Current Status
    CASE
        WHEN fm.id IS NOT NULL AND fm.unmounted_at IS NULL THEN 'In Use'
        WHEN fa.status = 'In Acclimatization' THEN 'In Acclimatization'
        WHEN fm.unmounted_at IS NOT NULL THEN 'Unmounted'
        ELSE 'In Storage'
    END AS current_status,

    -- Mounting Info
    fm.printer_id,
    p.name AS printer_name,
    fm.remaining_weight,
    fm.mounted_at,
    fm.unmounted_at,

    -- Acclimatization Info
    fa.moved_at AS acclimatized_at,
    fa.ready_at

FROM filaments f
LEFT JOIN filament_mounting fm ON fm.filament_id = f.id
LEFT JOIN printers p ON p.id = fm.printer_id
LEFT JOIN filament_acclimatization fa ON fa.filament_id = f.id
LEFT JOIN users u ON f.received_by = u.id
LEFT JOIN storage_locations sl ON f.location_id = sl.id;