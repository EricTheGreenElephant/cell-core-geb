INSERT INTO dbo.product_skus 
(product_type_id, sku, name, is_serialized, is_bundle, pack_qty, is_active) 
SELECT
    pt.id, v.sku, v.name, v.is_serialized, v.is_bundle, v.pack_qty, v.is_active
FROM (VALUES
    ('10K', 'GEB-CS10KTCS-4', 'CellScrew 10K', 1, 0, 1, 1),
    ('6K', 'GEB-CS6KTCS-2', 'CellScrew 6K', 1, 0, 1, 0),
    ('6K', 'GEB-CS6KTCS-4', 'CellScrew 6K', 1, 0, 1, 1),
    ('CS MINI', 'GEB-CSmTCS', 'CellScrew Mini', 0, 1, 3, 0),
    ('CS MINI', 'GEB-CSmTC2S', 'CellScrew Mini', 0, 1, 3, 0),
    ('CS MINI', 'GEB-CSmTCS-2', 'CellScrew Mini', 0, 1, 3, 1),
    ('TriDock', 'GEB-CSmTD', 'TriDock', 0, 0, 1, 1)
) AS v(product_type_name, sku, name, is_serialized, is_bundle, pack_qty, is_active)
JOIN dbo.product_types pt
    ON pt.name = v.product_type_name
LEFT JOIN dbo.product_skus s 
    ON s.sku = v.sku
WHERE s.id IS NULL;
