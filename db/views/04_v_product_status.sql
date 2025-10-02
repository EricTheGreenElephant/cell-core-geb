IF OBJECT_ID('v_product_status', 'V') IS NOT NULL   
    DROP VIEW v_product_status;
GO

CREATE VIEW v_product_status AS
SELECT pt.id AS product_id,
    lc.stage_name AS current_stage,
    ps.status_name AS current_status,
    loc.location_name,
    pt.last_updated_at,

    ptype.name AS product_type,
    sku.sku,
    ph.id AS harvest_id,
    pr.lot_number,
    ph.print_date,
    printed_user.display_name AS printed_by,

    l.serial_number AS lid_serial_number,
    qc.inspection_result AS qc_result,
    qc.weight_grams,
    qc.visual_pass,
    qc_user.display_name AS qc_inspected_by,

    f.serial_number as filament,
    p.name as printer,

    tbi.batch_id AS treatment_batch_id,
    pti.qc_result AS post_treatment_result,

    s.id AS shipment_id,
    s.status AS shipment_status,
    s.delivery_date

FROM product_tracking pt
JOIN product_harvest ph ON pt.harvest_id = ph.id
JOIN product_requests pr ON ph.request_id = pr.id
JOIN product_skus sku ON pr.sku_id = sku.id
JOIN product_types ptype ON sku.product_type_id = ptype.id
JOIN users printed_user ON ph.printed_by = printed_user.id

LEFT JOIN lifecycle_stages lc ON pt.current_stage_id = lc.id
LEFT JOIN product_statuses ps ON pt.current_status_id = ps.id
LEFT JOIN product_quality_control qc ON qc.product_id = pt.id
LEFT JOIN treatment_batch_products tbi ON tbi.product_id = pt.id
LEFT JOIN post_treatment_inspections pti ON pti.product_id = pt.id
LEFT JOIN shipment_unit_items si ON si.product_id = pt.id
LEFT JOIN shipments s ON si.shipment_id = s.id
LEFT JOIN lids l ON ph.lid_id = l.id
LEFT JOIN users qc_user ON qc.inspected_by = qc_user.id
LEFT JOIN filament_mounting fm ON ph.filament_mounting_id = fm.id
LEFT JOIN filaments f ON fm.filament_id = f.id
LEFT JOIN printers p ON fm.printer_id = p.id
LEFT JOIN storage_locations loc ON pt.location_id = loc.id
