IF OBJECT_ID('product_types', 'U') IS NULL
BEGIN
    CREATE TABLE product_types (
        id INT PRIMARY KEY IDENTITY(1,1),
        name NVARCHAR(100) NOT NULL UNIQUE,
        is_active BIT NOT NULL DEFAULT 1
    );
END;
