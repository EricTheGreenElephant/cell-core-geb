IF OBJECT_ID('quarantined_product_reasons', 'U') IS NULL
BEGIN
    CREATE TABLE quarantined_product_reasons (
        id INT IDENTITY PRIMARY KEY,
        quarantine_id INT NOT NULL,
        reason_id INT NOT NULL,

        CONSTRAINT fk_qpr_quarantine FOREIGN KEY (quarantine_id) REFERENCES quarantined_products(id),
        CONSTRAINT fk_qpr_reason FOREIGN KEY (reason_id) REFERENCES issue_reasons(id),
        CONSTRAINT uc_qpr UNIQUE (quarantine_id, reason_id)
    );
END;
