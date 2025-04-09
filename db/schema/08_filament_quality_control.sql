CREATE TABLE filament_quality_control (
    id INT PRIMARY KEY IDENTITY(1,1),
    filament_id INT NOT NULL,
    inspected_by INT NOT NULL,
    inspection_date DATETIME2 NOT NULL DEFAULT GETDATE(),
    result NVARCHAR(10) NOT NULL CHECK (result IN ('Pass', 'Fail')),
    notes NVARCHAR(255),

    CONSTRAINT fk_qc_user
        FOREIGN KEY (inspected_by) REFERENCES users(id)
    
    CONSTRAINT fk_qc_filament
        FOREIGN KEY (filament_id) REFERENCES filaments(id)
);