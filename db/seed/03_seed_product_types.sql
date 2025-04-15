IF NOT EXISTS (SELECT 1 FROM products)
BEGIN
    INSERT INTO products (name, average_weight, percentage_change) VALUES
    ('Bottle - Small', 500.00, 0.0500),
    ('Bottle - Medium', 700.00, 0.0450),
    ('Bottle - Large', 800.00, 0.0400);
END;