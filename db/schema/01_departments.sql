IF OBJECT_ID('departments', 'U') IS NULL
BEGIN
    CREATE TABLE departments (
        id INT PRIMARY KEY IDENTITY(1,1),
        department_code NVARCHAR(50) NULL UNIQUE,
        department_name NVARCHAR(50) NOT NULL UNIQUE,
        is_active BIT NOT NULL DEFAULT 1
    );
END;
