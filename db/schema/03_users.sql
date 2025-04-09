CREATE TABLE users (
    id INT PRIMARY KEY IDENTITY(1,1),
    department_id INT NOT NULL,
    azure_ad_object_id UNIQUEIDENTIFIER NOT NULL UNIQUE,
    user_principal_name NVARCHAR(255), -- e.g., jdoe@greenebt.com
    display_name NVARCHAR(100),
    created_at DATETIME2 DEFAULT GETDATE(),

    CONSTRAINT fk_user_department
        FOREIGN KEY (department_id) REFERENCES departments(id)
);