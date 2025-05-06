IF OBJECT_ID('v_product_status', 'V') IS NOT NULL   
    DROP VIEW v_product_status;
GO

CREATE VIEW v_product_status AS
SELECT pt.id AS tracking_id,
    pt.current_status,
    pt.last_updated_at,
    
    pr.id AS request_id,
    pr.lot_number,
    ptype.name AS product_type,
    pr.status AS request_status,
    pr.requested_at,

    ph.id AS harvest_id,
    ph.print_date,
    u.display_name AS printed_by,

    qc.inspection_result AS qc_result,
    qc.weight_grams,
    qc.visual_pass,

    tbi.batch_id AS treatment_batch_id,
    pti.final_result AS post_treatment_result,

    s.id AS shipment_id,
    s.status AS shipment_status,
    s.delivery_date

FROM product_tracking pt
JOIN product_harvest ph ON pt.harvest_id = ph.id
JOIN product_requests pr ON ph.request_id = pr.id
JOIN product_types ptype ON pr.product_id = ptype.id
JOIN users u ON ph.printed_by = u.id

LEFT JOIN product_quality_control qc ON qc.harvest_id = ph.id
LEFT JOIN treatment_batch_products tbi ON tbi.product_id = pt.id
LEFT JOIN post_treatment_inspections pti ON pti.product_id = pt.id
LEFT JOIN shipment_items si ON si.product_id = pt.id
LEFT JOIN shipments s ON si.shipment_id = s.id
