INSERT INTO dbo.users (department_id, azure_ad_object_id, user_principal_name, display_name, is_active)
SELECT d.id, NEWID(), v.user_principal_name, v.display_name, 1
FROM (VALUES
    ('PROD', 'admin@yourcompany.com', 'Admin User'),
    ('QM', 'sabrina@yourcompany.com', 'SaSe'),
    ('PROD', 'Nils@yourcompany.com', 'NiKa'),
    ('SALES', 'arthur@yourcompany.com', 'ArSe'),
    ('LOG', 'anika@yourcompany.com', 'AnMu'),
    ('LOG', 'henning@yourcompnay.com', 'HeRe'),
    ('LOG', 'paul@yourcompany.com', 'PaMe'),
    ('PROD', 'fouad@yourcompany.com', 'FoNo'),
    ('PROD', 'bjorn@yourcompany.com', 'BjBo')
) AS v(dept_code, user_principal_name, display_name)
JOIN dbo.departments d 
    ON d.department_code = v.dept_code
LEFT JOIN dbo.users u 
    ON u.user_principal_name = v.user_principal_name
WHERE u.id IS NULL;