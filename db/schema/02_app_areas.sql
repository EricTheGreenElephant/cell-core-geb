CREATE TABLE application_areas (
    id INT PRIMARY KEY IDENTITY(1,1),
    area_name NVARCHAR(50) NOT NULL UNIQUE
);