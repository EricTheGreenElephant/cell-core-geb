CREATE TABLE product_types (
    id INT PRIMARY KEY IDENTITY(1,1),
    name NVARCHAR(100) NOT NULL UNIQUE,
    average_weight DECIMAL(6,2) NOT NULL,
    percentage_change DECIMAL(5,4) NOT NULL
);