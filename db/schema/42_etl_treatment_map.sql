IF OBJECT_ID('etl_treatment_map','U') IS NULL
BEGIN
CREATE TABLE etl_treatment_map(
    treatment_id BIGINT NOT NULL PRIMARY KEY,
    batch_id     INT    NOT NULL UNIQUE,
    CONSTRAINT fk_etl_treatment_batch
    FOREIGN KEY (batch_id) REFERENCES dbo.treatment_batches(id)
);
END
