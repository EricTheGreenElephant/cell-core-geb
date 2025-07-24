IF NOT EXISTS(SELECT 1 FROM access_rights)
BEGIN 
    INSERT INTO access_rights(user_id, area_id, access_level) VALUES
        (1, 1, 'Admin'),
        (1, 2, 'Admin'),
        (1, 3, 'Admin'),
        (1, 4, 'Admin'),
        (1, 5, 'Admin'),
        (2, 1, 'Read'),
        (2, 2, 'Write'),
        (2, 3, 'Write'),
        (2, 4, 'Read'),
        (2, 5, 'Read'),
        (3, 1, 'Read'),
        (3, 2, 'Read'),
        (3, 3, 'Read'),
        (3, 4, 'Write'),
        (3, 5, 'Write'),
        (4, 1, 'Write'),
        (4, 2, 'Read'),
        (4, 3, 'Read'),
        (4, 4, 'Read'),
        (4, 5, 'Read');
END;
