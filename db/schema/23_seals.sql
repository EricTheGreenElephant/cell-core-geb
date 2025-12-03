IF OBJECT_ID('seals', 'U') IS NULL
BEGIN 
    CREATE TABLE seals (
        id INT PRIMARY KEY IDENTITY(1,1),
        serial_number NVARCHAR(100) NOT NULL UNIQUE,
        quantity INT NOT NULL,
        location_id INT NOT NULL,
        received_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        received_by INT NOT NULL,
        qc_result NVARCHAR(10) NOT NULL CHECK (qc_result IN ('PASS', 'FAIL')),

        CONSTRAINT fk_seal_location
            FOREIGN KEY (location_id) REFERENCES storage_locations(id),
        CONSTRAINT fk_seal_user FOREIGN KEY (received_by) REFERENCES users(id)
    );
END;
