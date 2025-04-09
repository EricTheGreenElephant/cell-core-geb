-- Products that failed post-treatment QC

SELECT pt.id, pti.final_result
FROM product_tracking pt
JOIN post_treatment_inspections pti ON pti.product_id = pt.id
WHERE pti.final_result IN ('Rejected');