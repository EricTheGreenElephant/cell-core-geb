CREATE TABLE departments (
    id INT PRIMARY KEY IDENTITY(1,1),
    department_name NVARCHAR(50) NOT NULL UNIQUE
);