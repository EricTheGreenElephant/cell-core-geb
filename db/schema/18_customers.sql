IF OBJECT_ID('customers', 'U') IS NULL
BEGIN
    CREATE TABLE customers (
        id INT PRIMARY KEY IDENTITY(1,1),
        customer_name NVARCHAR(50) NOT NULL UNIQUE
    );
END;