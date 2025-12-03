IF OBJECT_ID('group_area_rights', 'U') IS NULL
BEGIN
    CREATE TABLE group_area_rights (
        id INT PRIMARY KEY IDENTITY(1,1),
        group_oid UNIQUEIDENTIFIER NOT NULL,
        area_id INT NOT NULL,
        access_level NVARCHAR(20) NOT NULL CHECK (access_level IN ('Read', 'Write', 'Admin')),
        
        CONSTRAINT uc_group_area UNIQUE (group_oid, area_id),
        CONSTRAINT fk_gar_area FOREIGN KEY (area_id) REFERENCES application_areas(id)
    );

    CREATE INDEX IX_gar_group ON group_area_rights(group_oid);
    CREATE INDEX IX_gar_area ON group_area_rights(area_id);
END