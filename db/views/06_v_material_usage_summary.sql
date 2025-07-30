IF OBJECT_ID('v_material_usage_summary', 'V') IS NOT NULL
    DROP VIEW v_material_usage_summary;
GO

CREATE VIEW v_material_usage_summary AS
SELECT 
    mu.id AS usage_id,
    mu.material_type,
    mu.lot_number,
    mu.used_quantity,
    mu.harvest_id,
    ph.print_date,
    mu.product_id,
    pt.tracking_id,
    ptype.name AS product_type,
    u.display_name AS used_by

FROM material_usage mu
LEFT JOIN product_harvest ph ON mu.harvest_id = ph.id
LEFT JOIN product_tracking pt ON mu.product_id = pt.id
LEFT JOIN product_requests pr ON ph.request_id = pr.id
LEFT JOIN product_types ptype ON pr.product_id = ptype.id
LEFT JOIN users u ON mu.used_by = u.id;