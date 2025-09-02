CREATE OR ALTER VIEW dbo.v_product_lifecycle AS
SELECT 
    pt.id AS product_id,
    lc.stage_name AS current_status,
    pt.last_updated_at,
    loc.location_name,

    pr.id AS request_id,
    ptype.name AS product_type_name,
    ps.sku,
    pr.status AS request_status,
    pr.requested_at,

    ph.id AS harvest_id,
    ph.print_date,
    u.display_name AS printed_by,

    pqc.inspection_result AS initial_qc_result,
    pqc.weight_grams,
    pqc.pressure_drop,
    pqc.visual_pass,

    tb.id AS treatment_batch_id,
    tb.status AS treatment_status,
    tb.sent_at AS treatment_sent_at,
    pti.qc_result AS final_qc_result,
    pti.sterilized AS treatment_sterilized,

    s.id AS shipment_id,
    s.status AS shipment_status,
    s.ship_date,
    s.delivery_date,
    s.tracking_number,
    s.carrier

FROM product_tracking pt
LEFT JOIN lifecycle_stages lc  ON pt.current_stage_id = lc.id
LEFT JOIN storage_locations loc ON pt.location_id = loc.id
LEFT JOIN product_harvest ph   ON pt.harvest_id = ph.id
LEFT JOIN users u              ON ph.printed_by = u.id
LEFT JOIN product_requests pr  ON ph.request_id = pr.id
LEFT JOIN product_skus ps      ON pr.sku_id = ps.id
LEFT JOIN product_types ptype  ON ps.product_type_id = ptype.id
LEFT JOIN product_quality_control pqc ON pqc.product_id = pt.id
LEFT JOIN treatment_batch_products tbp ON tbp.product_id = pt.id
LEFT JOIN treatment_batches tb         ON tbp.batch_id   = tb.id
LEFT JOIN post_treatment_inspections pti ON pti.product_id = pt.id
LEFT JOIN shipment_unit_items si            ON si.product_id = pt.id
LEFT JOIN shipments s                  ON si.shipment_id = s.id;