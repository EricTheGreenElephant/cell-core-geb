INSERT INTO dbo.access_rights (user_id, area_id, access_level)
SELECT u.id, a.id, v.access_level
FROM (VALUES
    ('admin@yourcompany.com', 'Quality Management', 'Admin'),
    ('admin@yourcompany.com', 'Production', 'Admin'),
    ('admin@yourcompany.com', 'Filament Inventory', 'Admin'),
    ('admin@yourcompany.com', 'Sales', 'Admin'),
    ('admin@yourcompany.com', 'Logistics', 'Admin'),

    ('steve@yourcompany.com', 'Quality Management', 'Read'),
    ('steve@yourcompany.com', 'Production', 'Write'),
    ('steve@yourcompany.com', 'Filament Inventory', 'Write'),
    ('steve@yourcompany.com', 'Sales', 'Read'),
    ('steve@yourcompany.com', 'Logistics', 'Read'),

    ('arthur@yourcompany.com', 'Quality Management', 'Read'),
    ('arthur@yourcompany.com', 'Production', 'Read'),
    ('arthur@yourcompany.com', 'Filament Inventory', 'Read'),
    ('arthur@yourcompany.com', 'Sales', 'Write'),
    ('arthur@yourcompany.com', 'Logistics', 'Write'),

    ('sally@yourcompany.com', 'Quality Management', 'Write'),
    ('sally@yourcompany.com', 'Production', 'Read'),
    ('sally@yourcompany.com', 'Filament Inventory', 'Read'),
    ('sally@yourcompany.com', 'Sales', 'Read'),
    ('sally@yourcompany.com', 'Logistics', 'Read')
) AS v(user_principal_name, area_name, access_level)
JOIN dbo.users u 
    ON u.user_principal_name = v.user_principal_name
JOIN dbo.application_areas a 
    ON a.area_name = v.area_name 
LEFT JOIN dbo.access_rights ar 
    ON ar.user_id = u.id AND ar.area_id = a.id 
WHERE ar.id IS NULL;