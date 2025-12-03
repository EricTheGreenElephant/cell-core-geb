IF OBJECT_ID('post_treatment_inspection_reasons', 'U') IS NULL
BEGIN
    CREATE TABLE post_treatment_inspection_reasons (
        id INT IDENTITY PRIMARY KEY,
        inspection_id INT NOT NULL,
        reason_id INT NOT NULL,

        CONSTRAINT fk_pti_reason_inspection FOREIGN KEY (inspection_id) REFERENCES post_treatment_inspections(id),
        CONSTRAINT fk_pti_reason_reason FOREIGN KEY (reason_id) REFERENCES issue_reasons(id),
        CONSTRAINT uc_pti_reason UNIQUE (inspection_id, reason_id)
    );
END;