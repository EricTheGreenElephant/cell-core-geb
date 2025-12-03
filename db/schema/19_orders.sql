IF OBJECT_ID('orders', 'U') IS NULL
BEGIN
    CREATE TABLE orders (
        id INT PRIMARY KEY IDENTITY(1,1),
        parent_order_id INT,
        customer_id INT NOT NULL,
        order_date DATETIME2 NOT NULL DEFAULT GETDATE(),
        order_creator_id INT NOT NULL,
        status NVARCHAR(20) NOT NULL CHECK (status IN ('Processing', 'Shipped', 'Completed', 'Canceled')),
        updated_at DATETIME2 DEFAULT GETDATE(),
        updated_by INT NOT NULL,
        notes NVARCHAR(255),

        CONSTRAINT fk_order_parent FOREIGN KEY (parent_order_id) REFERENCES orders(id),
        CONSTRAINT fk_order_customer FOREIGN KEY (customer_id) REFERENCES customers(id),
        CONSTRAINT fk_order_creator FOREIGN KEY (order_creator_id) REFERENCES users(id),
        CONSTRAINT fk_order_updated_by FOREIGN KEY (updated_by) REFERENCES users(id)
    );
END;

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes WHERE name = 'ix_orders_customer_date'
        AND object_id = OBJECT_ID('orders')
)
BEGIN 
    CREATE INDEX ix_orders_customer_date ON orders(customer_id, order_date);
END;