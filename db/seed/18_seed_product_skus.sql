IF NOT EXISTS (SELECT 1 FROM product_skus)
BEGIN
    INSERT INTO product_skus (product_type_id, sku, height_mm, diameter_mm, average_weight_g, weight_buffer_g, is_active) VALUES
    (1, "GEB-CS10KTCS", 283.9, 121, 860.00, 15.50, 1),
    (1, "GEB-CS10KTCS-2", 288.7, 121, 830.00, 15.50, 1),
    (2, "GEB-CS6KTCS", 191.9, 121, 550.00, 10.00, 1),
    (2, "GEB-CS6KTCS-2", 202.2, 121, 535.00, 10.00, 1),
    (3, "GEB-CSmTCS", 161.4, 53, 120.00, 7.50, 1),
END;
