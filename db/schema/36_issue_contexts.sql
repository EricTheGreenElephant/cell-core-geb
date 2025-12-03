IF OBJECT_ID('issue_contexts', 'U') IS NULL
BEGIN 
    CREATE TABLE issue_contexts (
        id INT IDENTITY PRIMARY KEY,
        context_code NVARCHAR(50) NOT NULL UNIQUE
    );

    INSERT INTO issue_contexts (context_code)
    SELECT v.context_code
    FROM (VALUES ('HarvestQC'), ('PostTreatmentQC'), ('Quarantine'), ('AdHoc')) v(context_code)
    WHERE NOT EXISTS (SELECT 1 FROM issue_contexts ic WHERE ic.context_code = v.context_code);
END;
