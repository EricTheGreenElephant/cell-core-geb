IF NOT EXISTS (SELECT 1 FROM supplements)
BEGIN
    INSERT INTO supplements (name, is_active) VALUES
    ('TriDock', 1);
END;