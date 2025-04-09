-- Products that failed initial QC

SELECT pt.id AS product_id, pqc.inspection_result
FROM product_tracking pt
JOIN product_harvest ph ON pt.harvest_id = ph.id
JOIN product_quality_control pqc ON pqc.harvest_id = ph.id
WHERE pqc.inspection_result IN ('B-Ware', 'Waste');