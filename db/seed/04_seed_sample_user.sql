IF NOT EXISTS (
    SELECT 1 FROM users WHERE user_principal_name = 'admin@yourcompany.com'
)
BEGIN
    INSERT INTO users (department_id, azure_ad_object_id, user_principal_name, display_name, is_active)
    VALUES 
        (1, NEWID(), 'admin@yourcompany.com', 'Admin User', 1),
        (2, NEWID(), 'steve@yourcompany.com', 'StFi', 1),
        (3, NEWID(), 'arthur@yourcompany.com', 'ArSe', 1),
        (4, NEWID(), 'sally@yourcompany.com', 'SaFe', 1);
    
END;