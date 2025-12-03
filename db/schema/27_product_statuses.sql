IF OBJECT_ID('product_statuses', 'U') IS NULL
BEGIN
    CREATE TABLE product_statuses(
        id INT IDENTITY PRIMARY KEY,
        status_name NVARCHAR(50) NOT NULL UNIQUE,
        is_active BIT NOT NULL DEFAULT 1
    );
END;