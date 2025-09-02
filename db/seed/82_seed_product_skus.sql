INSERT INTO dbo.product_skus 
(product_type_id, sku, name, is_serialized, is_bundle, is_active) 
SELECT
    pt.id, v.sku, v.name, v.is_serialized, v.is_bundle, v.is_active
FROM (VALUES
    ('10K', 'GEB-CS10KTCS-4', 'CellScrew 10K', 1, 0, 1),
    ('6K', 'GEB-CS6KTCS-2', 'CellScrew 6K', 1, 0, 1),
    ('6K', 'GEB-CS6KTCS-4', 'CellScrew 6K', 1, 0, 1),
    ('6K', 'GEB-3CS6KTCS', ' Bundle 3x CellScrew 6K', 1, 1, 1),
    ('CS MINI', 'GEB-CSmTCS', 'CellScrew Mini', 1, 0, 1),
    ('CS MINI', 'GEB-3CSmTCS', 'Bundle 3x CellScrew Mini', 1, 1, 1),
    ('CS MINI', 'GEB-CSmTC2S', 'CellScrew Mini', 1, 0, 1),
    ('CS MINI', 'GEB-3CSmTC2S', 'Bundle 3x CellScrew Mini', 1, 1, 1),
    ('CS MINI', 'GEB-CSmTCS-2', 'CellScrew Mini', 1, 0, 1),
    ('CS MINI', 'GEB-3CSmTCS-2', 'Bundle 3x CellScrew Mini', 1, 1, 1),
    ('TriDock', 'GEB-CSmTD', 'TriDock', 0, 0, 1)
) AS v(product_type_name, sku, name, is_serialized, is_bundle, is_active)
JOIN dbo.product_types pt
    ON pt.name = v.product_type_name
LEFT JOIN dbo.product_skus s 
    ON s.sku = v.sku
WHERE s.id IS NULL;
