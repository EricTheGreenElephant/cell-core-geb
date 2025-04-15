CREATE TABLE filament_usage_log (
    id INT PRIMARY KEY IDENTITY,
    filament_id INT NOT NULL,
    harvest_id INT NOT NULL,
    used_grams DECIMAL(6, 2) NOT NULL,
    deducted_by INT NOT NULL,
    deducted_at DATETIME2 DEFAULT GETDATE(),

    CONSTRAINT fk_usage_filament FOREIGN KEY (filament_id) REFERENCES filaments(id),
    CONSTRAINT fk_usage_user FOREIGN KEY (deducted_by) REFERENCES users(id),
    CONSTRAINT fk_usage_product FOREIGN KEY (harvest_id) REFERENCES product_harvest(id)
)