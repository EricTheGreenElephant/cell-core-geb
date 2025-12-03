IF OBJECT_ID('users', 'U') IS NULL
BEGIN
    CREATE TABLE users (
        id INT PRIMARY KEY IDENTITY(1,1),
        department_id INT NOT NULL,
        azure_ad_object_id UNIQUEIDENTIFIER NOT NULL UNIQUE,
        user_principal_name NVARCHAR(255),
        display_name NVARCHAR(100),
        created_at DATETIME2 DEFAULT GETDATE(),
        is_active BIT NOT NULL DEFAULT 1,

        CONSTRAINT fk_user_department FOREIGN KEY (department_id) REFERENCES departments(id)
    );
END;
