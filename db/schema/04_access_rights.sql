CREATE TABLE access_rights (
    id INT PRIMARY KEY IDENTITY(1,1),
    user_id INT NOT NULL,
    area_id INT NOT NULL,
    access_level NVARCHAR(20) NOT NULL
        CHECK (access_level IN ('Read', 'Write', 'Admin')),

    CONSTRAINT fk_access_user FOREIGN KEY (user_id) REFERENCES users(id),
    CONSTRAINT fk_access_area FOREIGN KEY (area_id) REFERENCES application_areas(id),

    CONSTRAINT uc_user_area UNIQUE (user_id, area_id)  -- prevent duplicates
);