IF NOT EXISTS(SELECT 1 FROM customers)
BEGIN
    INSERT INTO customers(customer_name) VALUES
        ('CustABC123'),
        ('CustDEF456'),
        ('CustGHI789')
END;
