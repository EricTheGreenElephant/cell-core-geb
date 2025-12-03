MERGE dbo.printers AS tgt
USING (VALUES
    ('GEB1', 'Active', 1),
    ('GEB2', 'Active', 1),
    ('GEB3', 'Active', 1),
    ('GEB4', 'Active', 1),
    ('GEB5', 'Active', 1),
    ('GEB6', 'Active', 1),
    ('GEB7', 'Active', 1)
) AS src(name, status, is_active)
ON tgt.name = src.name
WHEN NOT MATCHED BY TARGET THEN
    INSERT (name, status, is_active)
    VALUES (src.name, src.status, src.is_active);