IF OBJECT_ID('shipment_unit_items', 'U') IS NULL
BEGIN
    CREATE TABLE shipment_unit_items(
        id INT PRIMARY KEY IDENTITY(1, 1),
        shipment_id INT NOT NULL,
        product_tracking_id INT NOT NULL UNIQUE,

        CONSTRAINT fk_shipunit_shipment FOREIGN KEY (shipment_id) REFERENCES shipments(id),
        CONSTRAINT fk_shipunit_product FOREIGN KEY (product_tracking_id) REFERENCES product_tracking(id)
    );
END;

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes WHERE name = 'ix_shipunit_shipment'
        AND object_id = OBJECT_ID('shipment_unit_items')
)
BEGIN
    CREATE INDEX ix_shipunit_shipment ON shipment_unit_items(shipment_id);
END;