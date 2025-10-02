MERGE dbo.customers AS tgt 
USING (VALUES
    ('CustABC123'),
    ('CustDEF456'),
    ('CustGHI789')
) AS src(customer_name)
ON tgt.customer_name = src.customer_name
WHEN NOT MATCHED BY TARGET THEN
    INSERT (customer_name) VALUES (src.customer_name);