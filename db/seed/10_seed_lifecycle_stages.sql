IF NOT EXISTS(SELECT 1 FROM lifecycle_stages)
BEGIN
    INSERT INTO lifecycle_stages(stage_code, stage_name, stage_order) VALUES
        ('Printed', 'Printed, Pending QC', 1),
        ('HarvestQCComplete', 'Harvest QC Complete; Pending Storage', 2),
        ('InInterimStorage', 'Stored; Pending QM Approval for Treatment', 3),
        ('QMTreatmentApproval', 'QM Approved for Treatment; Pending Treatment', 4),
        ('InTreatment', 'In Treatment / Shipped; Pending Return', 5),
        ('PostTreatmentQC', 'Returned / Post-Treatment QC; Pending Storage', 6),
        ('PostTreatmentStorage', 'Stored; Pending QM Approval', 7),
        ('QMSalesApproval', 'QM Approved For Sales; Pending Sales', 8),
        ('Quarantine', 'Moved to Quarantine', 99),
        ('Disposed', 'Discarded Product', 100),
        ('Shipped', 'Shipped to Customer', 110),
        ('Internal Use', 'Internal Use/Client', 120);
END;
