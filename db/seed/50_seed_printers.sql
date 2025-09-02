INSERT INTO dbo.printers (name, location_id, status, is_active)
SELECT v.name, s.id, v.status, 1
FROM (VALUES
    ('GEB1', '2250', 'Active', 1),
    ('GEB2', '2250', 'Active', 1),
    ('GEB3', '2250', 'Inactive', 1),
    ('GEB4', '2250', 'Active', 1)
) AS v(name, location_name, status, is_active)
JOIN dbo.storage_locations s 
    ON s.location_name = v.location_name
LEFT JOIN dbo.printers p
    ON p.name = v.name 
WHERE p.id IS NULL;