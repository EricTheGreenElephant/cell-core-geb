-- Products approved for sale but not yet shipped

SELECT *
FROM v_product_lifecycle
WHERE final_qc_result = 'Approved for Sale'
  AND shipment_status IS NULL;