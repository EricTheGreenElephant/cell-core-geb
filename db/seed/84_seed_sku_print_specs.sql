INSERT INTO dbo.sku_print_specs
    (sku_id, height_mm, diameter_mm, average_weight_g, weight_buffer_g)
SELECT 
    s.id,
    v.height_mm,
    v.diameter_mm,
    v.average_weight_g,
    v.weight_buffer_g
FROM (VALUES 
    ('GEB-CS10KTCS-4', 288.7, 121, 830, 15.50),
    ('GEB-CS6KTCS-2', 202.2, 121, 535, 10),
    ('GEB-CS6KTCS-4', 202.2, 121, 535, 10),
    ('GEB-CSmTCS', 161.4, 53, 120, 7.50),
    ('GEB-CSmTC2S', 161.4, 53, 120, 7.50),
    ('GEB-CSmTCS-2', 161.4, 53, 120, 7.50)
) AS v(sku, height_mm, diameter_mm, average_weight_g, weight_buffer_g)
JOIN dbo.product_skus s 
    ON s.sku = v.sku 
LEFT JOIN dbo.sku_print_specs p 
    ON p.sku_id = s.id 
WHERE s.is_serialized = 1
    AND s.is_bundle = 0
    AND p.sku_id IS NULL;