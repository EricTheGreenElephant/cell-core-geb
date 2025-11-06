INSERT INTO group_area_rights
(group_oid, area_id, access_level)
SELECT 
    TRY_CONVERT(UNIQUEIDENTIFIER, v.group_oid),
    a.id,
    v.access_level
FROM (VALUES
    (N'23b95f1c-02f8-4e0e-bb18-153b97fc8004', N'Production', N'Read'),
    (N'feacdb25-3548-41c1-a883-cd390b15782c', N'Production', N'Write'),
    (N'3f772c96-0723-4069-8d15-add5b53f30df', N'Logistics', N'Read'),
    (N'95f3232c-6f40-44de-86b0-b4f148963255', N'Logistics', N'Write'),
    (N'2f806a22-d7e8-48b2-9ee4-a16a03dde648', N'Quality Management', N'Write'),
    (N'741b0872-4d2b-47a5-a1e5-373803ce12ef', N'Quality Management', N'Read'),
    (N'391d747e-a387-4d7b-ae64-66c7141266a8', N'Sales', N'Read'),
    (N'c4270822-5292-4e9c-958c-2ca332058001', N'Sales', N'Write')
) AS v(group_oid, area_name, access_level)
JOIN application_areas a   
    ON a.area_name = v.area_name
LEFT JOIN group_area_rights gar 
    ON gar.group_oid = TRY_CONVERT(UNIQUEIDENTIFIER, v.group_oid)
    AND gar.area_id = a.id 
WHERE gar.id IS NULL;

DECLARE @GlobalAdminOid UNIQUEIDENTIFIER = TRY_CONVERT(UNIQUEIDENTIFIER, N'28ff3777-4390-428a-8355-ae80bca1cb62');

INSERT INTO group_area_rights
(group_oid, area_id, access_level)
SELECT 
    @GlobalAdminOid,
    a.id,
    N'Admin'
FROM application_areas a   
LEFT JOIN group_area_rights gar 
    ON gar.group_oid = @GlobalAdminOid
    AND gar.area_id = a.id  
WHERE gar.id IS NULL;
