IF OBJECT_ID('material_usage', 'U') IS NULL
BEGIN
    CREATE TABLE material_usage (
        id INT IDENTITY PRIMARY KEY,
        product_tracking_id INT NOT NULL,
        harvest_id INT NULL,
        material_type NVARCHAR(50) NOT NULL CHECK (material_type IN ('Filament', 'Lid', 'Seal')),
        lot_number NVARCHAR(100) NOT NULL,
        used_quantity DECIMAL(10, 2) NOT NULL,
        used_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        used_by INT NOT NULL,
        reason NVARCHAR(255),

        CONSTRAINT fk_usage_product FOREIGN KEY (product_tracking_id) REFERENCES product_tracking(id),
        CONSTRAINT fk_usage_harvest FOREIGN KEY (harvest_id) REFERENCES product_harvest(id),
        CONSTRAINT fk_usage_user FOREIGN KEY (used_by) REFERENCES users(id)
    );
END;