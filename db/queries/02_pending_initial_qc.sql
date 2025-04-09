-- Printed products awaiting initial QC check

SELECT pt.id AS product_id, ph.print_date, u.display_name AS printed_by
FROM product_tracking pt
JOIN product_harvest ph ON pt.harvest_id = ph.id
JOIN users u ON ph.printed_by = u.id
LEFT JOIN product_quality_control pqc ON pqc.harvest_id = ph.id
WHERE pqc.id IS NULL;