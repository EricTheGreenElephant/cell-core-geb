IF NOT EXISTS(SELECT 1 FROM storage_locations)
BEGIN
    INSERT INTO storage_locations(location_name, location_type, description)
    VALUES
        ("2255", "Shelf", NULL),
        ("2250", "Shelf", NULL),
        ("A", "Room", NULL),
        ("Airlock", "Production", NULL);
END;