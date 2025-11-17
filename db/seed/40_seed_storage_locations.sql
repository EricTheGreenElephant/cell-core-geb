MERGE dbo.storage_locations AS tgt
USING (VALUES
        ('2250', 'Shelf', 'Filament; Production Room'),
        ('2253', 'Shelf', 'Filament; Inventory Room'),
        ('2254', 'Shelf', 'Filament; Inventory Room'),
        ('2255', 'Shelf', 'Filament; Inventory Room'),
        ('2278', 'Shelf', 'CellScrew; Inventory'),
        ('2277', 'Shelf', 'CellScrew; Inventory'),
        ('2279', 'Shelf', 'CellScrew; Inventory'),
        ('2280', 'Shelf', 'CellScrew; Inventory'),
        ('2281', 'Shelf', 'CellScrew; Inventory'),
        ('2282', 'Shelf', 'CellScrew; Inventory'),
        ('2283', 'Shelf', 'CellScrew; B-Ware'),
        ('2284', 'Shelf', 'CellScrew; B-Ware'),
        ('2287', 'Shelf', 'CellScrew; Quarantine'),
        ('2300', 'Shelf', 'CellScrew; Sales'),
        ('2301', 'Shelf', 'CellScrew; Sales'),
        ('2302', 'Shelf', 'CellScrew; Sales'),
        ('2310', 'Shelf', 'CellScrew; Internal Use'),
        ('2311', 'Shelf', 'CellScrew; Internal Use'),
        ('A', 'Room', 'Lids'),
        ('Offsite', 'Offsite', 'Treatment/Partner/Customer'),
        ('Waste', 'Waste', 'Disposed Product')
) AS src(location_name, location_type, description)
ON tgt.location_name = src.location_name
WHEN NOT MATCHED BY TARGET THEN
    INSERT (location_name, location_type, description, is_active)
    VALUES (src.location_name, src.location_type, src.description, 1);