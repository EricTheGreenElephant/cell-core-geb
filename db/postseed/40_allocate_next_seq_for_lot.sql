/* 40_allocate_next_seq_for_lot.sql
   Returns next SSSS for a given YYCC lot_number prefix, safely under concurrency.
*/

CREATE OR ALTER PROCEDURE dbo.AllocateNextSeqForLot
  @lot_number NVARCHAR(50)
AS
BEGIN
  SET NOCOUNT ON;
  SET XACT_ABORT ON;

  DECLARE @lock_result INT;
  DECLARE @resource NVARCHAR(255);
  DECLARE @next INT;

  SET @resource = 'LOTSEQ:' + @lot_number;

  BEGIN TRAN;

  -- Lock per lot number so two users can't allocate the same SSSS concurrently
  EXEC @lock_result = sp_getapplock
      @Resource = @resource,
      @LockMode = 'Exclusive',
      @LockOwner = 'Transaction',
      @LockTimeout = 10000;

  IF @lock_result < 0
  BEGIN
      ROLLBACK;
      THROW 50010, 'Failed to acquire lot sequence lock', 1;
  END

  -- Find current max SSSS for this lot_number prefix, then +1
  SELECT @next =
      ISNULL(MAX(TRY_CAST(RIGHT(product_code, 4) AS INT)), 0) + 1
  FROM dbo.product_tracking
  WHERE product_code LIKE @lot_number + '____';

  COMMIT;

  SELECT @next AS item_seq;
END
GO
