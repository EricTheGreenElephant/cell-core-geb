MERGE dbo.lifecycle_stages AS tgt
USING (VALUES
        ('Printed', 'Printed, Pending QC', 1, 1),
        ('HarvestQCComplete', 'Harvest QC Complete; Pending Storage', 2, 1),
        ('InInterimStorage', 'Stored; Pending QM Approval for Treatment', 3, 1),
        ('QMTreatmentApproval', 'QM Approved for Treatment; Pending Treatment', 4, 1),
        ('InTreatment', 'In Treatment / Shipped; Pending Return', 5, 1),
        ('PostTreatmentQC', 'Returned / Post-Treatment QC; Pending Storage', 6, 1),
        ('PostTreatmentStorage', 'Stored; Pending QM Approval', 7, 1),
        ('QMSalesApproval', 'QM Approved For Sales; Pending Sales', 8, 1),
        ('Quarantine', 'Moved to Quarantine', 99, 1),
        ('Disposed', 'Discarded Product', 100, 1),
        ('PendingShipment', 'Marked for Shipment', 110, 1),
        ('Shipped', 'Shipped to Customer', 120, 1),
        ('Internal Use', 'Internal Use/Client', 130, 1),
        ('Expired', 'Overaged - Do Not Use', 999, 1)
) AS src(stage_code, stage_name, stage_order, is_active)
ON tgt.stage_code = src.stage_code
WHEN MATCHED THEN
    UPDATE SET 
        stage_name = src.stage_name,
        stage_order = src.stage_order,
        is_active = src.is_active
WHEN NOT MATCHED BY TARGET THEN
    INSERT (stage_code, stage_name, stage_order, is_active)
    VALUES (src.stage_code, src.stage_name, src.stage_order, src.is_active);