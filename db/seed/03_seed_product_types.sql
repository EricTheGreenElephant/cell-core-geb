IF NOT EXISTS (SELECT 1 FROM product_types)
BEGIN
    INSERT INTO product_types (name, is_active) VALUES
    ('10K', 1),
    ('6K', 1),
    ('CS MINI', 1);
END;