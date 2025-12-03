IF OBJECT_ID('post_treatment_inspections', 'U') IS NULL
BEGIN
    CREATE TABLE post_treatment_inspections (
        id INT PRIMARY KEY IDENTITY(1,1),
        product_tracking_id INT NOT NULL,
        inspected_by INT NOT NULL,
        inspected_at DATETIME2 DEFAULT GETDATE(),
        visual_pass BIT NOT NULL,
        surface_treated BIT NOT NULL,
        sterilized BIT NOT NULL,
        qc_result NVARCHAR(20) NOT NULL CHECK (qc_result IN ('Passed', 'B-Ware', 'Quarantine', 'Waste')),
        notes NVARCHAR(255),

        CONSTRAINT fk_post_qc_product FOREIGN KEY (product_tracking_id) REFERENCES product_tracking(id),
        CONSTRAINT fk_post_qc_user FOREIGN KEY (inspected_by) REFERENCES users(id)
    );
END;