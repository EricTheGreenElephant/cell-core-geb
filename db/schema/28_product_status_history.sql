IF OBJECT_ID('product_status_history', 'U') IS NULL
BEGIN
    CREATE TABLE product_status_history (
        id INT PRIMARY KEY IDENTITY(1,1),
        product_tracking_id INT NOT NULL,
        from_stage_id INT NULL,
        to_stage_id INT NOT NULL,
        reason NVARCHAR(255),
        changed_by INT NOT NULL,
        changed_at DATETIME2 NOT NULL DEFAULT GETDATE(),

        CONSTRAINT fk_status_product FOREIGN KEY (product_tracking_id) REFERENCES product_tracking(id),
        CONSTRAINT fk_status_from_stage FOREIGN KEY (from_stage_id) REFERENCES lifecycle_stages(id),
        CONSTRAINT fk_status_to_stage FOREIGN KEY (to_stage_id) REFERENCES lifecycle_stages(id),
        CONSTRAINT fk_status_user FOREIGN KEY (changed_by) REFERENCES users(id)
    );
END;