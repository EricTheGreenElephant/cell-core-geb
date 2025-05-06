IF NOT EXISTS(SELECT 1 FROM filaments)
BEGIN
    INSERT INTO filaments(serial_number, location_id, weight_grams, received_by, qc_result)
    VALUES
        ('123ABC', 1, 8000, 2, 'PASS'),
        ('456DEF', 2, 8000, 3, 'PASS'),
        ('789GHI', 1, 8000, 3, 'FAIL');
END;

