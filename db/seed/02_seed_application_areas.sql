IF NOT EXISTS (SELECT 1 FROM application_areas)
BEGIN
    INSERT INTO application_areas (area_name) VALUES
    ('Quality Control'),
    ('Production'),
    ('Filament Inventory'),
    ('Sales'),
    ('Logistics');
END;