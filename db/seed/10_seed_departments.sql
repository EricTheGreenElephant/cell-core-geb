MERGE dbo.departments AS tgt
USING (
    VALUES
        ('PROD', 'Production', 1),
        ('QM', 'Quality Management', 1),
        ('SALES', 'Sales', 1),
        ('LOG', 'Logistics', 1)
) AS src(department_code, department_name, is_active)
ON tgt.department_code = src.department_code
WHEN NOT MATCHED BY TARGET THEN
    INSERT (department_code, department_name, is_active)
    VALUES (src.department_code, src.department_name, src.is_active);