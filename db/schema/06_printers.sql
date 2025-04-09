CREATE TABLE printers (
    id INT PRIMARY KEY IDENTITY(1,1),
    name NVARCHAR(100) NOT NULL UNIQUE,
    location_id INT NOT NULL,
    manufacturer NVARCHAR(100),
    model NVARCHAR(100),
    serial_number NVARCHAR(100),
    status NVARCHAR(50) NOT NULL DEFAULT 'Active',
    created_at DATETIME2 NOT NULL DEFAULT GETDATE(),

    CONSTRAINT fk_printer_location
        FOREIGN KEY (location_id)
        REFERENCES storage_locations(id)
);