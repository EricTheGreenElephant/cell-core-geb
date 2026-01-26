MERGE dbo.issue_reasons AS tgt 
USING (
    VALUES 
        ('VIS_COLOR_DIFF',   'Color differences',      'Visual',    'B-Ware', 1),
        ('VIS_UNDER_EXT',    'Under-extrusion bottom', 'Visual',    'B-Ware', 1),
        ('VIS_BLACK_LINE_W',   'Black line with scratch', 'Visual',   'B-Ware', 1),
        ('VIS_BLACK_LINE_WO', 'Black line without scratch', 'Visual', 'B-Ware', 1),
        ('VIS_PARTICLES_IN', 'Particles in inner area', 'Visual',    'B-Ware', 1),
        ('VIS_GREATER_FIVE', 'Greater than five particles', 'Visual', 'B-Ware', 1),
        ('VIS_STRINGING', 'Stringing', 'Visual', 'B-Ware', 1),
        ('VIS_CRACKS', 'Cracks/Damage outer shell', 'Visual', 'Waste', 1),
        ('VIS_TEARS', 'Tears/Damage on surface', 'Visual', 'Waste', 1),
        ('VIS_OFFSET', 'Offset', 'Visual', 'Waste', 1),
        ('VIS_GYROID', 'Visible gyroid pattern', 'Visual', 'Waste', 1),
        ('VIS_BROKEN_BAG',    'Broken bag',             'Visual',    'B-Ware', 1),
        ('VIS_CONTAMINATION', 'Contamination visible',  'Visual',    'Waste', 1),
        ('PKG_SEAL_ISSUE',    'Packaging seal issue',   'Packaging', 'B-Ware', 1),
        ('LBL_DAMAGED',       'Damaged label',          'Packaging', 'B-Ware', 1),
        ('PROC_INCOMPLETE',   'Incomplete documentation','Process',  'Quarantine', 1),
        ('OTHER_BWARE', 'Other - B-Ware (please specify)', 'General', 'B-Ware', 1),
        ('OTHER_QUARANTINE', 'Other - Quarantine (please specify)', 'General', 'Quarantine', 1),
        ('OTHER_WASTE', 'Other - Waste', 'General', 'Waste', 1)
) AS src (reason_code, reason_label, category, default_outcome, is_active)
ON tgt.reason_code = src.reason_code 
WHEN MATCHED THEN 
    UPDATE SET
        reason_label = src.reason_label,
        category = src.category,
        default_outcome = src.default_outcome,
        is_active = src.is_active
WHEN NOT MATCHED BY TARGET THEN
    INSERT (reason_code, reason_label, category, default_outcome, is_active)
    VALUES (src.reason_code, src.reason_label, src.category, src.default_outcome, src.is_active);

INSERT INTO dbo.issue_reason_contexts (reason_id, context_id)
SELECT r.id, c.id 
FROM dbo.issue_reasons r 
JOIN dbo.issue_contexts c 
    ON c.context_code IN ('HarvestQC', 'PostTreatmentQC', 'AdHoc')
LEFT JOIN dbo.issue_reason_contexts x
    ON x.reason_id = r.id AND x.context_id = c.id 
WHERE x.id IS NULL;