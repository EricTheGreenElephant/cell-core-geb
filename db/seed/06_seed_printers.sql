IF NOT EXISTS (SELECT 1 FROM printers)
BEGIN
    INSERT INTO printers (name, location_id, manufacturer, model, serial_number, status) VALUES
    ('GEB1', 3, 'PrintersRus', '230B', '11AA22BB', 'Active'),
    ('GEB2', 3, 'PrintersRus', '230B', '11AA33CC', 'Active'),
    ('GEB3', 3, 'PrintersRus', '230B', '11AA44DD', 'Inactive');
END;
