IF OBJECT_ID('product_requests', 'U') IS NULL
BEGIN
    CREATE TABLE product_requests (
        id INT PRIMARY KEY IDENTITY(1,1),
        requested_by INT NOT NULL,
        sku_id INT NOT NULL,
        lot_number NVARCHAR(50) NOT NULL,
        status NVARCHAR(50) DEFAULT 'Pending',
        requested_at DATETIME2 DEFAULT GETDATE(),
        notes NVARCHAR(255),

        CONSTRAINT chk_request_status CHECK (status IN ('Pending', 'Fulfilled', 'Cancelled')),
        CONSTRAINT fk_request_user FOREIGN KEY (requested_by) REFERENCES users(id),
        CONSTRAINT fk_request_sku FOREIGN KEY (sku_id) REFERENCES product_skus(id)
    );
END;
