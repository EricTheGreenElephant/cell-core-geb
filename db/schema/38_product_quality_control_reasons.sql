IF OBJECT_ID('product_quality_control_reasons', 'U') IS NULL
BEGIN
    CREATE TABLE product_quality_control_reasons (
        id INT IDENTITY PRIMARY KEY,
        qc_id INT NOT NULL,
        reason_id INT NOT NULL,

        CONSTRAINT fk_pqc_reason_qc FOREIGN KEY (qc_id) REFERENCES product_quality_control(id),
        CONSTRAINT fk_pqc_reason_reason FOREIGN KEY (reason_id) REFERENCES issue_reasons(id),
        CONSTRAINT uc_pqc_reason UNIQUE (qc_id, reason_id)
    );
END;