CREATE TABLE storage_locations (
    id INT PRIMARY KEY IDENTITY(1,1),
    location_name NVARCHAR(100) NOT NULL UNIQUE,
    location_type NVARCHAR(50), -- e.g., "Shelf", "Room", "Warehouse"
    description NVARCHAR(255),
    created_at DATETIME2 NOT NULL DEFAULT GETDATE()
);