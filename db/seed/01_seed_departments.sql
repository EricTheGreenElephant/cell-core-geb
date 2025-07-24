IF NOT EXISTS (SELECT 1 FROM departments)
BEGIN
    INSERT INTO departments (department_name, is_active) VALUES
    ('Production', 1),
    ('Quality Management', 1),
    ('Sales', 1),
    ('Logistics', 1);
END;    