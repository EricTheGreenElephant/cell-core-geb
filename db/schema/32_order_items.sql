IF OBJECT_ID('order_items', 'U') IS NULL
BEGIN
    CREATE TABLE order_items (
        id INT PRIMARY KEY IDENTITY(1,1),
        order_id INT NOT NULL,
        product_sku_id INT NOT NULL,
        quantity INT NOT NULL CHECK (quantity > 0),

        CONSTRAINT fk_order_items_order FOREIGN KEY (order_id) REFERENCES orders(id),
        CONSTRAINT fk_order_items_sku FOREIGN KEY (product_sku_id) REFERENCES product_skus(id)
    );
END;

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes WHERE name = 'ix_oi_order'
        AND object_id = OBJECT_ID('order_items')
)
BEGIN
    CREATE INDEX ix_oi_order ON order_items(order_id);
END;