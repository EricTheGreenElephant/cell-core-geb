IF OBJECT_ID('product_print_specs', 'U') IS NULL 
BEGIN
    CREATE TABLE product_print_specs (
        sku_id INT PRIMARY KEY,
        height_mm DECIMAL(7,2) NOT NULL CHECK (height_mm > 0),
        diameter_mm DECIMAL(7,2) NOT NULL CHECK (diameter_mm > 0),
        average_weight_g DECIMAL(7,2) NOT NULL CHECK (average_weight_g > 0),
        weight_buffer_g DECIMAL(4,2) NOT NULL CHECK (weight_buffer_g >= 0),

        CONSTRAINT fk_printspecs_sku FOREIGN KEY (sku_id) REFERENCES product_skus(id)
    );
END; 
