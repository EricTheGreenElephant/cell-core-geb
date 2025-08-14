IF NOT EXISTS (SELECT 1 FROM sales_catalogue_supplements)
BEGIN
    INSERT INTO sales_catalogue_supplements (catalogue_id, supplement_id, supplement_quantity) VALUES
    (1, 1, 1),
    (6, 1, 1);
END;