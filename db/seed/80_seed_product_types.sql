MERGE dbo.product_types AS tgt
USING (VALUES
    ('10K', 1),
    ('6K', 1),
    ('CS MINI', 1),
    ('TriDock', 1)
) AS src(name, is_active)
ON tgt.name = src.name
WHEN NOT MATCHED BY TARGET THEN
    INSERT (name, is_active)
    VALUES(src.name, src.is_active);