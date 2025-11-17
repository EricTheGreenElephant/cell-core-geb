CREATE OR ALTER VIEW v_seal_inventory AS 
SELECT 
    s.id AS seal_id,
    s.serial_number,
    s.quantity,
    s.qc_result,
    s.received_at,
    u.display_name AS received_by,
    sl.location_name
FROM seals s
LEFT JOIN users u ON s.received_by = u.id
LEFT JOIN storage_locations sl ON s.location_id = sl.id
WHERE s.serial_number <> 'LEGACY_SEAL';