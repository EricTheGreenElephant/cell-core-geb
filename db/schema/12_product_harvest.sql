CREATE TABLE product_harvest (
    id INT PRIMARY KEY IDENTITY(1,1),
    request_id INT NOT NULL,
    filament_tracking_id INT NOT NULL,
    printed_by INT NOT NULL,
    print_date DATETIME2,
    print_status NVARCHAR(50) DEFAULT 'Queued',
    FOREIGN KEY (request_id) REFERENCES product_requests(id),
    FOREIGN KEY (filament_tracking_id) REFERENCES filament_tracking(id),
    FOREIGN KEY (printed_by) REFERENCES users(id)
);