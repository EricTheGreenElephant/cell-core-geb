-- Filament spools under threshold (e.g., 200g remaining)

SELECT f.id, f.name, f.weight_grams - ISNULL(SUM(pqc.weight_grams), 0) AS current_weight
FROM filaments f
JOIN filament_tracking ft ON ft.filament_id = f.id
JOIN product_harvest ph ON ph.filament_tracking_id = ft.id
JOIN product_quality_control pqc ON pqc.harvest_id = ph.id
GROUP BY f.id, f.name, f.weight_grams
HAVING f.weight_grams - ISNULL(SUM(pqc.weight_grams), 0) < 200;