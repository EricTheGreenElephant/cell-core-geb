IF NOT EXISTS (SELECT 1 FROM sales_catalogue_products)
BEGIN
    INSERT INTO sales_catalogue_products (catalogue_id, product_id, product_quantity) VALUES
    (1, 3, 3),
    (2, 3, 3),
    (3, 2, 1),
    (4, 1, 1),
    (5, 2, 3);
END;