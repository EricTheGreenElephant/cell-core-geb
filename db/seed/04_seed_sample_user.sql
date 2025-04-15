IF NOT EXISTS (
    SELECT 1 FROM users WHERE user_principal_name = 'admin@yourcompany.com'
)
BEGIN
    INSERT INTO users (department_id, azure_ad_object_id, user_principal_name, display_name)
    VALUES 
        (1, NEWID(), 'admin@yourcompany.com', 'Admin User'),
        (2, NEWID(), 'steve@yourcompany.com', 'StFi'),
        (3, NEWID(), 'arthur@yourcompany.com', 'ArSe');
    
END;