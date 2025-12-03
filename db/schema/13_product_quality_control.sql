IF OBJECT_ID('product_quality_control', 'U') IS NULL
BEGIN
    CREATE TABLE product_quality_control (
        id INT PRIMARY KEY IDENTITY(1,1),
        product_tracking_id INT NOT NULL,
        inspected_by INT NOT NULL,
        inspected_at DATETIME2 DEFAULT GETDATE() NOT NULL,
        weight_grams DECIMAL(6,2) NOT NULL,
        pressure_drop DECIMAL(6,3) NOT NULL,
        visual_pass BIT NOT NULL,
        inspection_result NVARCHAR(20) NOT NULL CHECK (inspection_result IN ('Passed', 'B-Ware', 'Waste', 'Quarantine')),
        notes NVARCHAR(255),

        CONSTRAINT fk_qc_print_job FOREIGN KEY (product_tracking_id) REFERENCES product_tracking(id),
        CONSTRAINT fk_qc_user_product FOREIGN KEY (inspected_by) REFERENCES users(id)
    );
END;