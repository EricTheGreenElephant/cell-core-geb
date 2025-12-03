IF OBJECT_ID('product_skus', 'U') IS NULL
BEGIN 
    CREATE TABLE product_skus (
        id INT PRIMARY KEY IDENTITY(1, 1),
        product_type_id INT NOT NULL,
        sku NVARCHAR(64) NOT NULL UNIQUE,
        name NVARCHAR(120) NOT NULL,
        is_serialized BIT NOT NULL,
        is_bundle BIT NOT NULL DEFAULT 0,
        pack_qty INT NOT NULL DEFAULT 1 CHECK (pack_qty > 0), 
        is_active BIT NOT NULL DEFAULT 1,

        CONSTRAINT fk_sku_type FOREIGN KEY (product_type_id) REFERENCES product_types(id)
    );
END;