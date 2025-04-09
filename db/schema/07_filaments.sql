CREATE TABLE filaments (
    id INT PRIMARY KEY IDENTITY(1,1),
    name NVARCHAR(100) NOT NULL,
    location_id INT NOT NULL,
    weight_grams DECIMAL(10,2) NOT NULL,
    material_type NVARCHAR(50) NOT NULL,
    diameter_mm DECIMAL(4,2) NOT NULL DEFAULT 1.75,
    created_at DATETIME2 NOT NULL DEFAULT GETDATE(),

    CONSTRAINT fk_filament_location
        FOREIGN KEY (location_id) REFERENCES storage_locations(id)

);