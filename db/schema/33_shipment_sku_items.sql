IF OBJECT_ID('shipment_sku_items', 'U') IS NULL
BEGIN 
    CREATE TABLE shipment_sku_items(
        id INT PRIMARY KEY IDENTITY(1, 1),
        shipment_id INT NOT NULL,
        product_sku_id INT NOT NULL,
        quantity INT NOT NULL CHECK (quantity > 0),

        CONSTRAINT fk_shipsku_shipment FOREIGN KEY (shipment_id) REFERENCES shipments(id),
        CONSTRAINT sk_shipsku_sku FOREIGN KEY (product_sku_id) REFERENCES product_skus(id)
    );
END;

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes WHERE name = 'ix_shipsku_shipment'
        AND object_id = OBJECT_ID('shipment_sku_items')
)
BEGIN
    CREATE INDEX ix_shipsku_shipment ON shipment_sku_items(shipment_id);
END;