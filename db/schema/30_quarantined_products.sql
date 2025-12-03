IF OBJECT_ID('quarantined_products', 'U') IS NULL
BEGIN
    CREATE TABLE quarantined_products(
        id INT IDENTITY PRIMARY KEY,
        product_tracking_id INT NOT NULL,
        from_stage_id INT NOT NULL,
        source NVARCHAR(50) NOT NULL CHECK (source IN ('Harvest QC', 'Post-Treatment QC', 'Ad-Hoc')),
        location_id INT NULL,
        quarantine_date DATETIME2 NOT NULL DEFAULT GETDATE(),
        quarantined_by INT NOT NULL,
        quarantine_reason NVARCHAR(255) NULL,
        quarantine_status NVARCHAR(20) NOT NULL CHECK (quarantine_status IN ('Active', 'Released', 'Disposed')),
        result NVARCHAR(20) NULL CHECK (result IN ('Passed', 'B-Ware', 'Waste')),
        resolved_at DATETIME2 NULL,
        resolved_by INT NULL,

        CONSTRAINT fk_quarantine_product FOREIGN KEY (product_tracking_id) REFERENCES product_tracking(id),
        CONSTRAINT fk_quarantine_stage FOREIGN KEY (from_stage_id) REFERENCES lifecycle_stages(id),
        CONSTRAINT fk_quarantine_user FOREIGN KEY (quarantined_by) REFERENCES users(id),
        CONSTRAINT fk_quarantine_resolved_user FOREIGN KEY (resolved_by) REFERENCES users(id),
        CONSTRAINT fk_quarantine_location FOREIGN KEY (location_id) REFERENCES storage_locations(id)
    );
END;
