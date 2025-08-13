CREATE OR ALTER VIEW v_lid_inventory AS 
SELECT 
    l.id AS lid_id,
    l.serial_number,
    l.quantity,
    l.qc_result,
    l.received_at,
    u.display_name AS received_by,
    s.location_name
FROM lids l
LEFT JOIN users u ON l.received_by = u.id
LEFT JOIN storage_locations s ON l.location_id = s.id;