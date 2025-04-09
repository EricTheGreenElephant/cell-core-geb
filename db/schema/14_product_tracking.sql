CREATE TABLE product_tracking (
    id INT PRIMARY KEY IDENTITY(1,1),           -- Unique bottle ID
    harvest_id INT NOT NULL UNIQUE,           -- One-to-one with print job
    current_status NVARCHAR(50) NOT NULL,       -- e.g., 'Printed', 'QC Passed', 'Shipped', etc.
    location_id INT,                            -- FK → storage_locations
    last_updated_at DATETIME2 DEFAULT GETDATE(),

    CONSTRAINT fk_harvest_product_job FOREIGN KEY (harvest_id) REFERENCES product_harvest(id),
    CONSTRAINT fk_harvest_product_location FOREIGN KEY (location_id) REFERENCES storage_locations(id)
);