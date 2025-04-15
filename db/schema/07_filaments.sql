CREATE TABLE filaments (
    id INT PRIMARY KEY IDENTITY(1,1),
    serial_number NVARCHAR(100) NOT NULL UNIQUE,
    location_id INT NOT NULL,
    weight_grams DECIMAL(10,2) NOT NULL,
    material_type NVARCHAR(50) NOT NULL,
    created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    received_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    received_by INT NOT NULL,
    qc_result NVARCHAR(10) NOT NULL CHECK (qc_result in ('PASS', 'FAIL')),

    CONSTRAINT fk_filament_location
        FOREIGN KEY (location_id) REFERENCES storage_locations(id),
    CONSTRAINT fk_filament_user FOREIGN KEY (received_by) REFERENCES users(id)
);