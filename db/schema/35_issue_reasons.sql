IF OBJECT_ID('issue_reasons', 'U') IS NULL
BEGIN
    CREATE TABLE issue_reasons (
        id INT IDENTITY PRIMARY KEY,
        reason_code NVARCHAR(50) NOT NULL UNIQUE,
        reason_label NVARCHAR(120) NOT NULL,
        category NVARCHAR(50) NOT NULL,
        default_outcome NVARCHAR(20) NULL CHECK (default_outcome IN ('B-Ware', 'Waste', 'Quarantine')),
        severity TINYINT NULL,
        is_active BIT NOT NULL DEFAULT 1,
        created_at DATETIME2 NOT NULL DEFAULT GETDATE()
    );
END;
