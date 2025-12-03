IF OBJECT_ID('storage_locations', 'U') IS NULL
BEGIN
    CREATE TABLE storage_locations (
        id INT PRIMARY KEY IDENTITY(1,1),
        location_name NVARCHAR(100) NOT NULL UNIQUE,
        location_type NVARCHAR(50),
        description NVARCHAR(255),
        created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        is_active BIT NOT NULL DEFAULT 1
    );
END;