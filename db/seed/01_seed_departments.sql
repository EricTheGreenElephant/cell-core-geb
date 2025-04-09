IF NOT EXISTS (SELECT 1 FROM departments)
BEGIN
    INSERT INTO departments (department_name) VALUES
    ('Production'),
    ('Quality Control'),
    ('Shipping'),
    ('Engineering');
END;