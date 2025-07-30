IF NOT EXISTS(SELECT 1 FROM filaments)
BEGIN
    INSERT INTO filaments(serial_number, lot_number, location_id, weight_grams, received_by, qc_result)
    VALUES
        ('123ABC-1', '123ABC', 1, 8000, 2, 'PASS'),
        ('123ABC-2', '123ABC', 1, 8000, 3, 'PASS'),
        ('123ABC-3', '123ABC', 1, 8000, 3, 'PASS'),
        ('456DEF-1', '456DEF', 1, 8000, 3, 'FAIL');
        ('456DEF-2', '456DEF', 1, 8000, 3, 'FAIL');
        ('456DEF-3', '456DEF', 1, 8000, 3, 'FAIL');
        
END;

