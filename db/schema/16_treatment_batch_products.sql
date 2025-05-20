CREATE TABLE treatment_batch_products (
    id INT PRIMARY KEY IDENTITY(1,1),
    batch_id INT NOT NULL,
    product_id INT NOT NULL UNIQUE,  -- Each product can only be in one batch
    surface_treat BIT NOT NULL,
    sterilize BIT NOT NULL
    CONSTRAINT fk_treatment_batch FOREIGN KEY (batch_id) REFERENCES treatment_batches(id),
    CONSTRAINT fk_treatment_product FOREIGN KEY (product_id) REFERENCES product_tracking(id)
);