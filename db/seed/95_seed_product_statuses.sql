MERGE dbo.product_statuses AS tgt 
USING (VALUES
    ('Pending', 1),
    ('A-Ware', 1),
    ('B-Ware', 1),
    ('In Quarantine', 1),
    ('Waste', 1)
) AS src(status_name, is_active)
ON tgt.status_name = src.status_name
WHEN MATCHED THEN 
    UPDATE SET is_active = src.is_active
WHEN NOT MATCHED BY TARGET THEN 
    INSERT (status_name, is_active)
    VALUES (src.status_name, src.is_active);
