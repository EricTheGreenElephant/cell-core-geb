IF NOT EXISTS(SELECT 1 FROM product_statuses)
BEGIN
    INSERT INTO product_statuses(status_name) VALUES
        ('Pending'),
        ('A-Ware'),
        ('B-Ware'),
        ('In Quarantine'),
        ('Waste');
END;
