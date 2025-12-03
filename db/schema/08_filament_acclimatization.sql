IF OBJECT_ID('filament_acclimatization', 'U') IS NULL
BEGIN
    CREATE TABLE filament_acclimatization(
        id INT PRIMARY KEY IDENTITY(1,1),
        filament_tracking_id INT NOT NULL UNIQUE,
        moved_by INT NOT NULL,
        moved_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        ready_at AS DATEADD(DAY, 2, moved_at) PERSISTED,
        status NVARCHAR(50) NOT NULL CHECK (status IN ('Acclimatizing', 'Complete')),

        CONSTRAINT fk_accl_fila FOREIGN KEY (filament_tracking_id) REFERENCES filaments(id),
        CONSTRAINT fk_accl_user FOREIGN KEY (moved_by) REFERENCES users(id)
    );
END;
