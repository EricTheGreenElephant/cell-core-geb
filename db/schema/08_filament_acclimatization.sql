CREATE TABLE filament_acclimatization (
    id INT PRIMARY KEY IDENTITY,
    filament_id INT NOT NULL UNIQUE,
    moved_by INT NOT NULL,
    moved_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    ready_at AS DATEADD(DAY, 2, moved_at) PERSISTED,
    status NVARCHAR(50) NOT NULL DEFAULT 'In Acclimatization',

    CONSTRAINT fk_accl_fila FOREIGN KEY (filament_id) REFERENCES filaments(id),
    CONSTRAINT fk_accl_user FOREIGN KEY (moved_by) REFERENCES users(id)
)