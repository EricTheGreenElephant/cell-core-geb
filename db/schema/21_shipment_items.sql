CREATE TABLE shipment_items (
    id INT PRIMARY KEY IDENTITY(1,1),
    shipment_id INT NOT NULL,
    product_id INT NOT NULL,  -- Printed item

    quantity INT NOT NULL,

    CONSTRAINT fk_shipment_item_shipment FOREIGN KEY (shipment_id) REFERENCES shipments(id),
    CONSTRAINT fk_shipment_item_product FOREIGN KEY (product_id) REFERENCES product_tracking(id)
);