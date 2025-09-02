MERGE dbo.application_areas AS tgt
USING (VALUES
    ('Quality Management', 1),
    ('Production', 1),
    ('Filament Inventory', 1),
    ('Sales', 1),
    ('Logistics', 1)
) AS src(area_name, is_active)
ON tgt.area_name = src.area_name
WHEN NOT MATCHED BY TARGET THEN
    INSERT (area_name, is_active)
    VALUES (src.area_name, src.is_active);