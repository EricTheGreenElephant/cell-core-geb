IF NOT EXISTS (SELECT 1 FROM application_areas)
BEGIN
    INSERT INTO application_areas (area_name, is_active) VALUES
    ('Quality Management', 1),
    ('Production', 1),
    ('Filament Inventory', 1),
    ('Sales', 1),
    ('Logistics', 1);
END;