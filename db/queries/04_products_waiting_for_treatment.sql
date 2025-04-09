-- QC-passed products that haven't been assigned to a treatment batch

SELECT pt.id, pt.current_status
FROM product_tracking pt
JOIN product_harvest ph ON pt.harvest_id = ph.id
JOIN product_quality_control pqc ON pqc.harvest_id = ph.id
LEFT JOIN treatment_batch_products tbp ON tbp.product_id = pt.id
WHERE pqc.inspection_result = 'Passed'
  AND tbp.product_id IS NULL;