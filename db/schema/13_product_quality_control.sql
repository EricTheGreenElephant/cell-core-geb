CREATE TABLE product_quality_control (
    id INT PRIMARY KEY IDENTITY(1,1),
    harvest_id INT NOT NULL,
    inspected_by INT NOT NULL,
    inspected_at DATETIME2 DEFAULT GETDATE(),

    weight_grams DECIMAL(6,2) NOT NULL,
    pressure_drop DECIMAL(6,2) NOT NULL,
    visual_pass BIT NOT NULL,

    inspection_result NVARCHAR(20) NOT NULL
        CHECK (inspection_result IN ('Passed', 'B-Ware', 'Waste')),

    notes NVARCHAR(255),

    CONSTRAINT fk_qc_print_job FOREIGN KEY (harvest_id) REFERENCES product_harvest(id),
    CONSTRAINT fk_qc_user FOREIGN KEY (inspected_by) REFERENCES users(id)
);