CREATE TABLE post_treatment_inspections (
    id INT PRIMARY KEY IDENTITY(1,1),
    product_id INT NOT NULL,
    inspected_by INT NOT NULL,
    inspected_at DATETIME2 DEFAULT GETDATE(),
    visual_pass BIT NOT NULL,
    sterilized BIT NOT NULL,
    final_result NVARCHAR(20) NOT NULL
        CHECK (final_result IN ('Approved for Sale', 'Internal Use', 'Rejected')),
    notes NVARCHAR(255),

    FOREIGN KEY (product_id) REFERENCES product_tracking(id),
    FOREIGN KEY (inspected_by) REFERENCES users(id)
);