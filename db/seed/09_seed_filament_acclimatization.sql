IF NOT EXISTS(SELECT 1 FROM filament_acclimatization)
BEGIN
    INSERT INTO filament_acclimatization(filament_id, moved_by, moved_at, status) VALUES
        (1, 2, GETDATE(), 'In Acclimatization'),
        (2, 2, DATEADD(DAY, -5, GETDATE()), 'In Acclimatization'),
        (4, 2, DATEADD(DAY, 3, GETDATE()), 'In Production');
END;
