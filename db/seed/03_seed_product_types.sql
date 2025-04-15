IF NOT EXISTS (SELECT 1 FROM product_types)
BEGIN
    INSERT INTO product_types (name, average_weight, percentage_change) VALUES
    ('Bottle - Small', 500.00, 0.0500),
    ('Bottle - Medium', 700.00, 0.0450),
    ('Bottle - Large', 800.00, 0.0400);
END;