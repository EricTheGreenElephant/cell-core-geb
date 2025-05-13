CREATE TABLE product_harvest (
    id INT PRIMARY KEY IDENTITY(1,1),
    request_id INT NOT NULL,
    lid_id INT NOT NULL,
    filament_tracking_id INT NOT NULL,
    printed_by INT NOT NULL,
    print_date DATETIME2,
    print_status NVARCHAR(50) DEFAULT 'Queued',

    CONSTRAINT fk_harvest_request FOREIGN KEY (request_id) REFERENCES product_requests(id),
    CONSTRAINT fk_lid_id FOREIGN KEY (lid_id) REFERENCES lids(id),
    CONSTRAINT fk_harvest_filament_mounting FOREIGN KEY (filament_mounting_id) REFERENCES filament_mounting(id),
    CONSTRAINT fk_harvest_user FOREIGN KEY (printed_by) REFERENCES users(id)
);