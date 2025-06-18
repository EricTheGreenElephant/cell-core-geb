IF NOT EXISTS(SELECT 1 FROM filament_acclimatization)
BEGIN
    INSERT INTO filament_acclimatization(filament_id, moved_by, moved_at, status) VALUES
        (1, 2, GETDATE(), 'Acclimatizing'),
        (2, 2, DATEADD(DAY, -5, GETDATE()), 'Acclimatizing'),
        (3, 2, DATEADD(DAY, 3, GETDATE()), 'Complete');
END;
