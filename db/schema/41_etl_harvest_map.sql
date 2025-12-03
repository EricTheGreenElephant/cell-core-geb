IF OBJECT_ID('etl_harvest_map','U') IS NULL
BEGIN
  CREATE TABLE etl_harvest_map(
    product_id_bigint BIGINT NOT NULL PRIMARY KEY,   -- 1 product -> 1 harvest
    harvest_id        INT    NOT NULL UNIQUE,        -- and each harvest used once
    CONSTRAINT fk_map_harvest
      FOREIGN KEY (harvest_id) REFERENCES dbo.product_harvest(id)
  );
END;