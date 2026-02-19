/* 003_tech_transfer_flags.sql */

IF COL_LENGTH('dbo.product_requests', 'is_tech_transfer') IS NULL
BEGIN
  ALTER TABLE dbo.product_requests
  ADD is_tech_transfer BIT NOT NULL
      CONSTRAINT DF_product_requests_is_tech_transfer DEFAULT (0);
END
GO

IF COL_LENGTH('dbo.product_skus', 'tech_transfer') IS NULL
BEGIN
  ALTER TABLE dbo.product_skus
  ADD tech_transfer BIT NOT NULL
      CONSTRAINT DF_product_skus_tech_transfer DEFAULT (0);
END
GO

IF COL_LENGTH('dbo.product_tracking', 'was_tech_transfer') IS NULL
BEGIN
  ALTER TABLE dbo.product_tracking
  ADD was_tech_transfer BIT NOT NULL
      CONSTRAINT DF_product_tracking_was_tech_transfer DEFAULT (0);
END
GO

IF NOT EXISTS (
  SELECT 1
  FROM sys.indexes
  WHERE name = 'IX_product_tracking_was_tech_transfer'
    AND object_id = OBJECT_ID('dbo.product_tracking')
)
BEGIN
  CREATE INDEX IX_product_tracking_was_tech_transfer
  ON dbo.product_tracking(was_tech_transfer);
END
GO
