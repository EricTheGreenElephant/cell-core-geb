CREATE TABLE filament_mounting(
    id INT PRIMARY KEY IDENTITY,
    filament_id INT NOT NULL UNIQUE,
    printer_id INT NOT NULL,
    mounted_by INT NOT NULL,
    mounted_at DATETIME2 DEFAULT GETDATE(),
    remaining_weight DECIMAL(10,2) NOT NULL,
    status NVARCHAR(50) NOT NULL DEFAULT 'In Use',

    CONSTRAINT fk_mount_filament FOREIGN KEY (filament_id) REFERENCES filaments(id),
    CONSTRAINT fk_mount_printer FOREIGN KEY (printer_id) REFERENCES printers(id),
    CONSTRAINT fk_mount_user FOREIGN KEY (mounted_by) REFERENCES users(id)
)