CREATE TABLE filament_tracking (
    id INT PRIMARY KEY IDENTITY(1,1),
    filament_id INT NOT NULL,
    printer_id INT,
    user_id INT NOT NULL,
    status NVARCHAR(50) NOT NULL,
    status_date DATETIME2 NOT NULL DEFAULT GETDATE(),
    notes NVARCHAR(255),

    CONSTRAINT fk_tracking_filament
        FOREIGN KEY (filament_id) REFERENCES filaments(id),

    CONSTRAINT fk_tracking_printer
        FOREIGN KEY (printer_id) REFERENCES printers(id),

    CONSTRAINT fk_tracking_user
        FOREIGN KEY (user_id) REFERENCES users(id)
);