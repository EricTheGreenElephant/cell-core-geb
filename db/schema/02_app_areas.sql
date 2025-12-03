IF OBJECT_ID('application_areas', 'U') IS NULL
BEGIN
    CREATE TABLE application_areas (
        id INT PRIMARY KEY IDENTITY(1,1),
        area_name NVARCHAR(50) NOT NULL UNIQUE,
        is_active BIT NOT NULL DEFAULT 1
    );
END;
