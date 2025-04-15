IF NOT EXISTS(SELECT 1 FROM storage_locations)
BEGIN
    INSERT INTO storage_locations(location_name, location_type, description)
    VALUES
        ("2255", "Shelf", ),
        ("2250", "Shelf", ),
        ("A", "Room", ),
        ("Airlock", "Production", );
END;