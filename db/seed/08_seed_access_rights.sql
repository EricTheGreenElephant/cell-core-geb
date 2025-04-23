IF NOT EXISTS(SELECT 1 FROM access_rights)
BEGIN 
    INSERT INTO access_rights(user_id, area_id, access_level) VALUES
        (1, 1, 'Admin'),
        (1, 2, 'Admin'),
        (1, 3, 'Admin'),
        (1, 4, 'Admin'),
        (2, 1, 'Write'),
        (2, 2, 'Write'),
        (2, 3, 'Read'),
        (2, 4, 'Read'),
        (3, 1, 'Write'),
        (3, 2, 'Read'),
        (3, 3, 'Write'),
        (3, 4, 'Read');
END;
