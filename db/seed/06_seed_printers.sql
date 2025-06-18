IF NOT EXISTS (SELECT 1 FROM printers)
BEGIN
    INSERT INTO printers (name, location_id, status, is_active) VALUES
    ('GEB1', 3, 'Active', 1),
    ('GEB2', 3, 'Active', 1),
    ('GEB3', 3, 'Inactive', 1),
    ('GEB4', 3, 'Active', 1);
END;
