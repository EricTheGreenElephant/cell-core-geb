MERGE dbo.storage_locations AS tgt
USING (VALUES
        ('2253', 'Shelf', 'Filament; Materials; Inventory Room'),
        ('2255', 'Shelf', 'Filament; Materials; Inventory Room'),
        ('2254', 'Shelf', 'Filament; Materials; Inventory Room'),
        ('2256', 'Shelf', 'Filament; Materials; Inventory Room'),
        ('2257', 'Shelf', 'Filament; Materials; Inventory Room'),
        ('2258', 'Shelf', 'Filament; Materials; Inventory Room'),
        ('2259', 'Shelf', 'Filament; Materials; Inventory Room'),
        ('2260', 'Shelf', 'Filament; Materials; Inventory Room'),
        ('2273', 'Shelf', 'CellScrew; Inventory'),
        ('2274', 'Shelf', 'CellScrew; Inventory'),
        ('2275', 'Shelf', 'CellScrew; Inventory'),
        ('2277', 'Shelf', 'CellScrew; Inventory'),
        ('2278', 'Shelf', 'CellScrew; Inventory'),
        ('2276', 'Shelf', 'CellScrew; B-Ware'),
        ('2280', 'Shelf', 'CellScrew; B-Ware'),
        ('2279', 'Shelf', 'CellScrew; Quarantine'),
        ('K11c-3', 'Shelf', 'CellScrew; 6K; Sales'),
        ('K11c-4', 'Shelf', 'CellScrew; 6K; Sales'),
        ('K11c-5', 'Shelf', 'CellScrew; 10K; Sales'),
        ('K11c-6', 'Shelf', 'CellScrew; 10K; Sales'),
        ('K11c-7', 'Shelf', 'CellScrew; mini; Sales'),
        ('K11c-8', 'Shelf', 'CellScrew; mini; Sales'),
        ('207', 'Room', 'CellScrew; Internal Use'),
        ('Offsite', 'Offsite', 'Treatment/Partner/Customer'),
        ('Waste', 'Waste', 'Disposed Product')
) AS src(location_name, location_type, description)
ON tgt.location_name = src.location_name
WHEN NOT MATCHED BY TARGET THEN
    INSERT (location_name, location_type, description, is_active)
    VALUES (src.location_name, src.location_type, src.description, 1);