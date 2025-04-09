CREATE TABLE product_requests (
    id INT PRIMARY KEY IDENTITY(1,1),
    requested_by INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL,
    status NVARCHAR(50) DEFAULT 'Pending',
    requested_at DATETIME2 DEFAULT GETDATE(),
    notes NVARCHAR(255),
    FOREIGN KEY (requested_by) REFERENCES users(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);