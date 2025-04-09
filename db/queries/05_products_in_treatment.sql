-- Products currently out for treatment

SELECT pt.id, tb.status, tb.sent_at
FROM product_tracking pt
JOIN treatment_batch_products tbp ON tbp.product_id = pt.id
JOIN treatment_batches tb ON tbp.batch_id = tb.id
WHERE tb.status IN ('Shipped', 'In Transit');