CREATE TABLE shipments (
    id INT PRIMARY KEY IDENTITY(1,1),
    customer_id INT NOT NULL,
    order_id INT,
    creator_id INT NOT NULL,
    created_date DATETIME2 NOT NULL DEFAULT GETDATE(),
    ship_date DATETIME2,
    delivery_date DATETIME2,
    status NVARCHAR(20) NOT NULL CHECK (status IN ('Pending', 'Shipped', 'In Transit', 'Delivered', 'Returned', 'Canceled')),
    updated_at DATETIME2 DEFAULT GETDATE(),
    tracking_number NVARCHAR(50),
    carrier NVARCHAR(50),

    CONSTRAINT fk_shipment_customer FOREIGN KEY (customer_id) REFERENCES customers(id),
    CONSTRAINT fk_shipment_order FOREIGN KEY (order_id) REFERENCES orders(id),
    CONSTRAINT fk_shipment_creator FOREIGN KEY (creator_id) REFERENCES users(id)
);