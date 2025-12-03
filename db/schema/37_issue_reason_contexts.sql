IF OBJECT_ID('issue_reason_contexts', 'U') IS NULL
BEGIN
    CREATE TABLE issue_reason_contexts (
        id INT IDENTITY PRIMARY KEY,
        reason_id INT NOT NULL,
        context_id INT NOT NULL,
        
        CONSTRAINT fk_irc_reason FOREIGN KEY (reason_id) REFERENCES issue_reasons(id),
        CONSTRAINT fk_irc_context FOREIGN KEY (context_id) REFERENCES issue_contexts(id),
        CONSTRAINT uc_reason_context UNIQUE (reason_id, context_id)
    );
END;