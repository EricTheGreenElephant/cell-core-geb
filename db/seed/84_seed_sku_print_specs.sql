INSERT INTO dbo.product_print_specs
    (sku_id, height_mm, diameter_mm, average_weight_g, weight_buffer_g)
SELECT 
    s.id,
    v.height_mm,
    v.diameter_mm,
    v.average_weight_g,
    v.weight_buffer_g
FROM (VALUES 
    ('GEB-CS10KTCS-4', 288.7, 121, 930, 46),
    ('GEB-CS6KTCS-2', 202.2, 121, 615, 30),
    ('GEB-CS6KTCS-4', 202.2, 121, 615, 30),
    ('GEB-CSmTCS', 161.4, 53, 120, 7.50),
    ('GEB-CSmTC2S', 161.4, 53, 120, 7.50),
    ('GEB-CSmTCS-2', 161.4, 53, 162, 8)
) AS v(sku, height_mm, diameter_mm, average_weight_g, weight_buffer_g)
JOIN dbo.product_skus s 
    ON s.sku = v.sku 
LEFT JOIN dbo.product_print_specs p 
    ON p.sku_id = s.id 
WHERE p.sku_id IS NULL;