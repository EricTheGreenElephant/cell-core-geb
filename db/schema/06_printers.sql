IF OBJECT_ID('printers', 'U') IS NULL
BEGIN
    CREATE TABLE printers (
        id INT PRIMARY KEY IDENTITY(1,1),
        name NVARCHAR(100) NOT NULL UNIQUE,
        status NVARCHAR(50) NOT NULL DEFAULT 'Active',
        created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        is_active BIT NOT NULL DEFAULT 1
    );
END;