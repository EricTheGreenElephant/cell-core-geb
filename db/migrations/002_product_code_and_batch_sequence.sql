/* 002_product_code_and_batch_sequence.sql
   Adds new product_code column + unique index.
   Adds a batch-number SEQUENCE for generating YYCC lot_number prefixes.
*/

-- A) Add product_code column
IF COL_LENGTH('dbo.product_tracking', 'product_code') IS NULL
BEGIN
  ALTER TABLE dbo.product_tracking
  ADD product_code NVARCHAR(20) NULL;
END
GO

-- B) Unique index for product_code (new rows only)
IF NOT EXISTS (
  SELECT 1
  FROM sys.indexes
  WHERE name = 'UX_product_tracking_product_code'
    AND object_id = OBJECT_ID('dbo.product_tracking')
)
BEGIN
  CREATE UNIQUE INDEX UX_product_tracking_product_code
  ON dbo.product_tracking(product_code)
  WHERE product_code IS NOT NULL;
END
GO

-- C) Batch number sequence (for CC)
IF NOT EXISTS (
  SELECT 1
  FROM sys.sequences
  WHERE name = 'seq_batch_number'
    AND SCHEMA_NAME(schema_id) = 'dbo'
)
BEGIN
  CREATE SEQUENCE dbo.seq_batch_number
    AS INT
    START WITH 1
    INCREMENT BY 1;
END
GO
