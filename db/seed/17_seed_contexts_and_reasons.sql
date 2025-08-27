INSERT INTO issue_reasons (reason_code, reason_label, category, default_outcome)
SELECT * FROM (VALUES
('VIS_MISSING_LID',   'Missing lid',            'Visual',    'B-Ware'),
('VIS_BROKEN_BAG',    'Broken bag',             'Visual',    'B-Ware'),
('VIS_CONTAMINATION', 'Contamination visible',  'Visual',    'Waste'),
('PKG_SEAL_ISSUE',    'Packaging seal issue',   'Packaging', 'B-Ware'),
('LBL_DAMAGED',       'Damaged label',          'Packaging', 'B-Ware'),
('PROC_INCOMPLETE',   'Incomplete documentation','Process',  'Quarantine'),
('OTHER_BWARE', 'Other - B-Ware (please specify)', 'General', 'B-Ware'),
('OTHER_QUARANTINE', 'Other - Quarantine (please specify)', 'General', 'Quarantine'),
('OTHER_WASTE', 'Other - Waste', 'General', 'Waste')
) v(reason_code, reason_label, category, default_outcome)
WHERE NOT EXISTS (SELECT 1 FROM issue_reasons r WHERE r.reason_code = v.reason_code);

INSERT INTO issue_reason_contexts (reason_id, context_id)
SELECT r.id, c.id
FROM issue_reasons r
JOIN issue_contexts c ON c.context_code IN ('HarvestQC', 'PostTreatmentQC')
LEFT JOIN issue_reason_contexts x ON x.reason_id = r.id AND x.context_id = c.id
WHERE x.id IS NULL;