IF OBJECT_ID('product_investigations', 'U') IS NULL
BEGIN
    CREATE TABLE product_investigations(
        id INT IDENTITY PRIMARY KEY,
        product_tracking_id INT NOT NULL,
        status VARCHAR(50) NOT NULL CHECK (status IN ('Under Investigation', 'Cleared A-Ware', 'Cleared B-Ware', 'Disposed')),
        deviation_number VARCHAR(50),
        comment NVARCHAR(255),
        created_by INT NOT NULL,
        created_at DATETIME2 DEFAULT GETDATE() NOT NULL,
        resolved_at DATETIME2 NULL,
        resolved_by INT NULL,

        CONSTRAINT fk_investigation_product FOREIGN KEY (product_tracking_id) REFERENCES product_tracking(id),
        CONSTRAINT fk_investigation_user FOREIGN KEY (created_by) REFERENCES users(id),
        CONSTRAINT fk_investigation_resolved_user FOREIGN KEY (resolved_by) REFERENCES users(id)
    );
END;