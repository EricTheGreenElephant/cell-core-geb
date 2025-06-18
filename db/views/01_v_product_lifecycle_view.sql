CREATE VIEW v_product_lifecycle AS
SELECT 
    pt.id AS product_id,
    lc.stage_name AS current_status,
    pt.last_updated_at,
    loc.location_name,

    -- Request info
    pr.id AS request_id,
    pr.quantity AS request_quantity,
    ptype.name AS product_type_name,
    pr.status AS request_status,
    pr.requested_at,

    -- Harvest info
    ph.id AS harvest_id,
    ph.print_date,
    u.display_name AS printed_by,

    -- Initial QC
    pqc.inspection_result AS initial_qc_result,
    pqc.weight_grams,
    pqc.pressure_drop,
    pqc.visual_pass,

    -- Treatment info
    tb.id AS treatment_batch_id,
    tb.status AS treatment_status,
    tb.sent_at AS treatment_sent_at,
    pti.qc_result AS final_qc_result,
    pti.sterilized AS treatment_sterilized,

    -- Shipment info
    s.id AS shipment_id,
    s.status AS shipment_status,
    s.ship_date,
    s.delivery_date,
    s.tracking_number,
    s.carrier

FROM product_tracking pt
LEFT JOIN lifecycle_stages lc ON pt.current_stage_id = lc.id
LEFT JOIN storage_locations loc ON pt.location_id = loc.id

-- Harvest & user
LEFT JOIN product_harvest ph ON pt.harvest_id = ph.id
LEFT JOIN users u ON ph.printed_by = u.id

-- Request & product type
LEFT JOIN product_requests pr ON ph.request_id = pr.id
LEFT JOIN product_types ptype ON pr.product_id = ptype.id

-- Initial QC
LEFT JOIN product_quality_control pqc ON pqc.harvest_id = ph.id

-- Treatment
LEFT JOIN treatment_batch_products tbp ON tbp.product_id = pt.id
LEFT JOIN treatment_batches tb ON tbp.batch_id = tb.id
LEFT JOIN post_treatment_inspections pti ON pti.product_id = pt.id

-- Shipment
LEFT JOIN shipment_items si ON si.product_id = pt.id
LEFT JOIN shipments s ON si.shipment_id = s.id;