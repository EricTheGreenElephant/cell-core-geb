IF OBJECT_ID('treatment_batches', 'U') IS NULL
BEGIN
    CREATE TABLE treatment_batches (
        id INT PRIMARY KEY IDENTITY(1,1),
        sent_by INT NOT NULL,
        sent_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        received_at DATETIME2,
        notes NVARCHAR(255),
        status NVARCHAR(50) NOT NULL CHECK (status IN ('Shipped', 'Inspected')),

        CONSTRAINT fk_treatment_sent_by FOREIGN KEY (sent_by) REFERENCES users(id)
    );
END;