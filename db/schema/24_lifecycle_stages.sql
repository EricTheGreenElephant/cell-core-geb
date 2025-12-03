IF OBJECT_ID('lifecycle_stages', 'U') IS NULL
BEGIN 
    CREATE TABLE lifecycle_stages(
        id INT PRIMARY KEY IDENTITY(1,1),
        stage_code NVARCHAR(50) NOT NULL UNIQUE,
        stage_name NVARCHAR(100) NOT NULL,
        stage_order INT NOT NULL,
        is_active BIT NOT NULL DEFAULT 1
    );
END;
