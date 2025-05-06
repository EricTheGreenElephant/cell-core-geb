IF NOT EXISTS (SELECT 1 FROM product_types)
BEGIN
    INSERT INTO product_types (name, average_weight, buffer_weight) VALUES
    ('10K', 860.00, 15.50),
    ('6K', 535.00, 10.00),
    ('CS MINI', 146.00, 7.50);
END;