IF OBJECT_ID('product_tracking', 'U') IS NULL
BEGIN
    CREATE TABLE product_tracking (
        id INT PRIMARY KEY IDENTITY(1,1),
        harvest_id INT NOT NULL UNIQUE,
        product_id BIGINT NOT NULL UNIQUE,
        product_type_id INT NOT NULL,
        sku_id INT NOT NULL,
        current_status_id INT NULL,
        previous_stage_id INT NULL,
        current_stage_id INT NOT NULL,
        location_id INT,
        last_updated_at DATETIME2 DEFAULT GETDATE(),

        CONSTRAINT fk_tracking_harvest FOREIGN KEY (harvest_id) REFERENCES product_harvest(id),
        CONSTRAINT fk_tracking_sku FOREIGN KEY (sku_id) REFERENCES product_skus(id),
        CONSTRAINT fk_tracking_type FOREIGN KEY (product_type_id) REFERENCES product_types(id), 
        CONSTRAINT fk_tracking_status FOREIGN KEY (current_status_id) REFERENCES product_statuses(id),
        CONSTRAINT fk_tracking_location FOREIGN KEY (location_id) REFERENCES storage_locations(id),
        CONSTRAINT fk_tracking_stage FOREIGN KEY (current_stage_id) REFERENCES lifecycle_stages(id),
        CONSTRAINT fk_tracking_prev_stage FOREIGN KEY (previous_stage_id) REFERENCES lifecycle_stages(id)
    );
END;