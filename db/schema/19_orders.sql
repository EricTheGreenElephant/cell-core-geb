CREATE TABLE orders (
    id INT PRIMARY KEY IDENTITY(1,1),
    customer_id INT NOT NULL,
    order_date DATETIME2 NOT NULL DEFAULT GETDATE(),
    order_creator_id INT NOT NULL,
    status NVARCHAR(20) NOT NULL CHECK (status IN ('Processing', 'Shipped', 'Completed', 'Canceled')),
    updated_at DATETIME2 DEFAULT GETDATE(),

    CONSTRAINT fk_order_customer FOREIGN KEY (customer_id) REFERENCES customers(id),
    CONSTRAINT fk_order_creator FOREIGN KEY (order_creator_id) REFERENCES users(id)
);