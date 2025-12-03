IF OBJECT_ID('audit_log', 'U') IS NULL
BEGIN
    CREATE TABLE audit_log (
        id INT PRIMARY KEY IDENTITY(1,1),
        table_name NVARCHAR(100) NOT NULL,
        record_id INT NOT NULL,
        field_name NVARCHAR(100) NOT NULL,
        old_value NVARCHAR(MAX),
        new_value NVARCHAR(MAX),
        reason NVARCHAR(255) NOT NULL,
        changed_by INT NOT NULL,
        changed_at DATETIME2 NOT NULL DEFAULT GETDATE(),

        CONSTRAINT fk_audit_user FOREIGN KEY (changed_by) REFERENCES users(id)
    );
END;
