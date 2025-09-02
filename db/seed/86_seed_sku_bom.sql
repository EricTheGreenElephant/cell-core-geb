INSERT INTO dbo.sku_bom
    (parent_sku_id, component_sku_id, component_qty)
SELECT
    parent.id,
    comp.id,
    v.component_qty
FROM (VALUES
    ('GEB-3CS6KTCS', 'GEB-CS6KTCS-4', 3),
    ('GEB-3CSmTCS-2', 'GEB-CSmTCS-2', 3),
    ('GEB-3CSmTC2S', 'GEB-CSmTC2S', 3),
    ('GEB-3CSmTCS', 'GEB-CSmTCS', 3)
) AS v(parent_sku, component_sku, component_qty)
JOIN dbo.product_skus parent 
    ON parent.sku = v.parent_sku 
JOIN dbo.product_skus comp 
    ON comp.sku = v.component_sku
LEFT JOIN dbo.sku_bom b 
    ON b.parent_sku_id = parent.id 
    AND b.component_sku_id = comp.id 
WHERE b.id IS NULL;
