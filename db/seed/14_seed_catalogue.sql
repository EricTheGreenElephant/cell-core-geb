IF NOT EXISTS (SELECT 1 FROM sales_catalogue)
BEGIN
    INSERT INTO sales_catalogue (article_number, package_name, package_desc, price, is_active) VALUES
    (10000, 'CS mini Bundle Starter', '3x CS MINI, 1 TriDock', 699, 1),
    (10001, 'CS mini Bundle', '3x CS MINI', 699, 1),
    (10002, 'CS 6K', '1x 6K', 446, 1),
    (10003, 'CS 10K', '1x 10K', 637, 1),
    (10004, 'CS 6K Starter Bundle', '3x 6K', 1199, 1),
    (10005, 'CS mini TriDock', '1x TriDock', 89, 1);
END;