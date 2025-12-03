IF OBJECT_ID('filament_mounting', 'U') IS NULL
BEGIN
    CREATE TABLE filament_mounting(
        id INT PRIMARY KEY IDENTITY(1,1),
        filament_tracking_id INT NOT NULL,
        printer_id INT NOT NULL,
        mounted_by INT NOT NULL,
        mounted_at DATETIME2 DEFAULT GETDATE(),
        unmounted_at DATETIME2 NULL,
        unmounted_by INT NULL,
        remaining_weight DECIMAL(10,2) NOT NULL,
        status NVARCHAR(50) NOT NULL DEFAULT 'In Use',

        CONSTRAINT chk_status CHECK (status IN ('In Use', 'Unmounted')),
        CONSTRAINT fk_mount_filament FOREIGN KEY (filament_tracking_id) REFERENCES filaments(id),
        CONSTRAINT fk_mount_printer FOREIGN KEY (printer_id) REFERENCES printers(id),
        CONSTRAINT fk_mount_user FOREIGN KEY (mounted_by) REFERENCES users(id),
        CONSTRAINT fk_mounting_unmounted_by FOREIGN KEY (unmounted_by) REFERENCES users(id)
    );
END;