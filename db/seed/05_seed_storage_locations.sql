IF NOT EXISTS(SELECT 1 FROM storage_locations)
BEGIN
    INSERT INTO storage_locations(location_name, location_type, description)
    VALUES
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
        ('A', 'Room', 'Lids'),
        ('Offsite', 'Offsite', 'Treatment/Partner/Customer'),
        ('Waste', 'Waste', 'Disposed Product');
        
END;