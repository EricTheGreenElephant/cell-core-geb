-- ====================================
-- 001_initial_schema.sql
-- Description: Initial schema setup
-- ====================================

-- ========== USER & ACCESS CONTROL ==========
IF OBJECT_ID('departments', 'U') IS NULL
BEGIN
    CREATE TABLE departments (
        id INT PRIMARY KEY IDENTITY(1,1),
        department_code NVARCHAR(50) NULL UNIQUE,
        department_name NVARCHAR(50) NOT NULL UNIQUE,
        is_active BIT NOT NULL DEFAULT 1
    );
END;

IF OBJECT_ID('application_areas', 'U') IS NULL
BEGIN
    CREATE TABLE application_areas (
        id INT PRIMARY KEY IDENTITY(1,1),
        area_name NVARCHAR(50) NOT NULL UNIQUE,
        is_active BIT NOT NULL DEFAULT 1
    );
END;

IF OBJECT_ID('users', 'U') IS NULL
BEGIN
    CREATE TABLE users (
        id INT PRIMARY KEY IDENTITY(1,1),
        department_id INT NOT NULL,
        azure_ad_object_id UNIQUEIDENTIFIER NOT NULL UNIQUE,
        user_principal_name NVARCHAR(255),
        display_name NVARCHAR(100),
        created_at DATETIME2 DEFAULT GETDATE(),
        is_active BIT NOT NULL DEFAULT 1,

        CONSTRAINT fk_user_department FOREIGN KEY (department_id) REFERENCES departments(id)
    );
END;

IF OBJECT_ID('access_rights', 'U') IS NULL
BEGIN
    CREATE TABLE access_rights (
        id INT PRIMARY KEY IDENTITY(1,1),
        user_id INT NOT NULL,
        area_id INT NOT NULL,
        access_level NVARCHAR(20) NOT NULL CHECK (access_level IN ('Read', 'Write', 'Admin')),

        CONSTRAINT fk_access_user FOREIGN KEY (user_id) REFERENCES users(id),
        CONSTRAINT fk_access_area FOREIGN KEY (area_id) REFERENCES application_areas(id),
        CONSTRAINT uc_user_area UNIQUE (user_id, area_id)
    );
END;

-- ========== LOCATIONS & EQUIPMENT ==========
IF OBJECT_ID('storage_locations', 'U') IS NULL
BEGIN
    CREATE TABLE storage_locations (
        id INT PRIMARY KEY IDENTITY(1,1),
        location_name NVARCHAR(100) NOT NULL UNIQUE,
        location_type NVARCHAR(50),
        description NVARCHAR(255),
        created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        is_active BIT NOT NULL DEFAULT 1
    );
END;

IF OBJECT_ID('printers', 'U') IS NULL
BEGIN
    CREATE TABLE printers (
        id INT PRIMARY KEY IDENTITY(1,1),
        name NVARCHAR(100) NOT NULL UNIQUE,
        location_id INT NOT NULL,
        status NVARCHAR(50) NOT NULL DEFAULT 'Active',
        created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        is_active BIT NOT NULL DEFAULT 1,

        CONSTRAINT fk_printer_location FOREIGN KEY (location_id) REFERENCES storage_locations(id)
    );
END;

IF OBJECT_ID('lids', 'U') IS NULL
BEGIN 
    CREATE TABLE lids (
        id INT PRIMARY KEY IDENTITY(1,1),
        serial_number NVARCHAR(100) NOT NULL UNIQUE,
        quantity INT NOT NULL,
        location_id INT NOT NULL,
        received_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        received_by INT NOT NULL,
        qc_result NVARCHAR(10) NOT NULL CHECK (qc_result IN ('PASS', 'FAIL')),

        CONSTRAINT fk_lid_location
            FOREIGN KEY (location_id) REFERENCES storage_locations(id),
        CONSTRAINT fk_lid_user FOREIGN KEY (received_by) REFERENCES users(id)
    );
END;

IF OBJECT_ID('seals', 'U') IS NULL
BEGIN 
    CREATE TABLE seals (
        id INT PRIMARY KEY IDENTITY(1,1),
        serial_number NVARCHAR(100) NOT NULL UNIQUE,
        quantity INT NOT NULL,
        location_id INT NOT NULL,
        received_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        received_by INT NOT NULL,
        qc_result NVARCHAR(10) NOT NULL CHECK (qc_result IN ('PASS', 'FAIL')),

        CONSTRAINT fk_seal_location
            FOREIGN KEY (location_id) REFERENCES storage_locations(id),
        CONSTRAINT fk_seal_user FOREIGN KEY (received_by) REFERENCES users(id)
    );
END;

IF OBJECT_ID('filaments', 'U') IS NULL
BEGIN
    CREATE TABLE filaments (
        id INT PRIMARY KEY IDENTITY(1,1),
        filament_id BIGINT NOT NULL UNIQUE,
        serial_number NVARCHAR(100) NOT NULL,
        lot_number NVARCHAR(100) NOT NULL,
        location_id INT NOT NULL,
        weight_grams DECIMAL(10,2) NOT NULL,
        received_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        received_by INT NOT NULL,
        qc_result NVARCHAR(10) NOT NULL CHECK (qc_result IN ('PASS', 'FAIL')),

        CONSTRAINT fk_filament_location
            FOREIGN KEY (location_id) REFERENCES storage_locations(id),
        CONSTRAINT fk_filament_user FOREIGN KEY (received_by) REFERENCES users(id)
    );
END;

IF OBJECT_ID('filament_acclimatization', 'U') IS NULL
BEGIN
    CREATE TABLE filament_acclimatization(
        id INT PRIMARY KEY IDENTITY(1,1),
        filament_tracking_id INT NOT NULL UNIQUE,
        moved_by INT NOT NULL,
        moved_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        ready_at AS DATEADD(DAY, 2, moved_at) PERSISTED,
        status NVARCHAR(50) NOT NULL CHECK (status IN ('Acclimatizing', 'Complete')),

        CONSTRAINT fk_accl_fila FOREIGN KEY (filament_tracking_id) REFERENCES filaments(id),
        CONSTRAINT fk_accl_user FOREIGN KEY (moved_by) REFERENCES users(id)
    );
END;

IF OBJECT_ID('filament_mounting', 'U') IS NULL
BEGIN
    CREATE TABLE filament_mounting(
        id INT PRIMARY KEY IDENTITY(1,1),
        filament_tracking_id INT NOT NULL,
        printer_id INT NOT NULL,
        mounted_by INT NOT NULL,
        mounted_at DATETIME2 DEFAULT GETDATE(),
        unmounted_at DATETIME2 NULL,
        unmounted_by INT NULL,
        remaining_weight DECIMAL(10,2) NOT NULL,
        status NVARCHAR(50) NOT NULL DEFAULT 'In Use',

        CONSTRAINT chk_status CHECK (status IN ('In Use', 'Unmounted')),
        CONSTRAINT fk_mount_filament FOREIGN KEY (filament_tracking_id) REFERENCES filaments(id),
        CONSTRAINT fk_mount_printer FOREIGN KEY (printer_id) REFERENCES printers(id),
        CONSTRAINT fk_mount_user FOREIGN KEY (mounted_by) REFERENCES users(id),
        CONSTRAINT fk_mounting_unmounted_by FOREIGN KEY (unmounted_by) REFERENCES users(id)
    );
END;

-- =========== LIFECYCLE STAGES ============
IF OBJECT_ID('lifecycle_stages', 'U') IS NULL
BEGIN 
    CREATE TABLE lifecycle_stages(
        id INT PRIMARY KEY IDENTITY(1,1),
        stage_code NVARCHAR(50) NOT NULL UNIQUE,
        stage_name NVARCHAR(100) NOT NULL,
        stage_order INT NOT NULL,
        is_active BIT NOT NULL DEFAULT 1
    );
END;

-- ========== PRODUCT DEFINITIONS ==========
IF OBJECT_ID('product_types', 'U') IS NULL
BEGIN
    CREATE TABLE product_types (
        id INT PRIMARY KEY IDENTITY(1,1),
        name NVARCHAR(100) NOT NULL UNIQUE,
        is_active BIT NOT NULL DEFAULT 1
    );
END;

IF OBJECT_ID('product_skus', 'U') IS NULL
BEGIN 
    CREATE TABLE product_skus (
        id INT PRIMARY KEY IDENTITY(1, 1),
        product_type_id INT NOT NULL,
        sku NVARCHAR(64) NOT NULL UNIQUE,
        name NVARCHAR(120) NOT NULL,
        is_serialized BIT NOT NULL,
        is_bundle BIT NOT NULL DEFAULT 0,
        pack_qty INT NOT NULL DEFAULT 1 CHECK (pack_qty > 0), 
        is_active BIT NOT NULL DEFAULT 1,

        CONSTRAINT fk_sku_type FOREIGN KEY (product_type_id) REFERENCES product_types(id)
    );
END;

IF OBJECT_ID('product_print_specs', 'U') IS NULL 
BEGIN
    CREATE TABLE product_print_specs (
        sku_id INT PRIMARY KEY,
        height_mm DECIMAL(7,2) NOT NULL CHECK (height_mm > 0),
        diameter_mm DECIMAL(7,2) NOT NULL CHECK (diameter_mm > 0),
        average_weight_g DECIMAL(7,2) NOT NULL CHECK (average_weight_g > 0),
        weight_buffer_g DECIMAL(4,2) NOT NULL CHECK (weight_buffer_g >= 0),

        CONSTRAINT fk_printspecs_sku FOREIGN KEY (sku_id) REFERENCES product_skus(id)
    );
END; 

IF OBJECT_ID('product_statuses', 'U') IS NULL
BEGIN
    CREATE TABLE product_statuses(
        id INT IDENTITY PRIMARY KEY,
        status_name NVARCHAR(50) NOT NULL UNIQUE,
        is_active BIT NOT NULL DEFAULT 1
    );
END;

IF OBJECT_ID('product_requests', 'U') IS NULL
BEGIN
    CREATE TABLE product_requests (
        id INT PRIMARY KEY IDENTITY(1,1),
        requested_by INT NOT NULL,
        sku_id INT NOT NULL,
        lot_number NVARCHAR(50) NOT NULL,
        status NVARCHAR(50) DEFAULT 'Pending',
        requested_at DATETIME2 DEFAULT GETDATE(),
        notes NVARCHAR(255),

        CONSTRAINT chk_request_status CHECK (status IN ('Pending', 'Fulfilled', 'Cancelled')),
        CONSTRAINT fk_request_user FOREIGN KEY (requested_by) REFERENCES users(id),
        CONSTRAINT fk_request_sku FOREIGN KEY (sku_id) REFERENCES product_skus(id)
    );
END;

IF OBJECT_ID('product_harvest', 'U') IS NULL
BEGIN
    CREATE TABLE product_harvest (
        id INT PRIMARY KEY IDENTITY(1,1),
        request_id INT NOT NULL,
        lid_id INT NOT NULL,
        seal_id INT NOT NULL,
        filament_mounting_id INT NOT NULL,
        printed_by INT NOT NULL,
        print_date DATETIME2,

        CONSTRAINT fk_harvest_request FOREIGN KEY (request_id) REFERENCES product_requests(id),
        CONSTRAINT fk_lid_id FOREIGN KEY (lid_id) REFERENCES lids(id),
        CONSTRAINT fk_seal_id FOREIGN KEY (seal_id) REFERENCES seals(id),
        CONSTRAINT fk_harvest_filament_mounting FOREIGN KEY (filament_mounting_id) REFERENCES filament_mounting(id),
        CONSTRAINT fk_harvest_user FOREIGN KEY (printed_by) REFERENCES users(id)
    );
END;

IF OBJECT_ID('product_tracking', 'U') IS NULL
BEGIN
    CREATE TABLE product_tracking (
        id INT PRIMARY KEY IDENTITY(1,1),
        harvest_id INT NOT NULL UNIQUE,
        product_id BIGINT NOT NULL UNIQUE,
        product_type_id INT NOT NULL,
        sku_id INT NOT NULL,
        current_status_id INT NULL,
        previous_stage_id INT NULL,
        current_stage_id INT NOT NULL,
        location_id INT,
        last_updated_at DATETIME2 DEFAULT GETDATE(),

        CONSTRAINT fk_tracking_harvest FOREIGN KEY (harvest_id) REFERENCES product_harvest(id),
        CONSTRAINT fk_tracking_sku FOREIGN KEY (sku_id) REFERENCES product_skus(id),
        CONSTRAINT fk_tracking_type FOREIGN KEY (product_type_id) REFERENCES product_types(id), 
        CONSTRAINT fk_tracking_status FOREIGN KEY (current_status_id) REFERENCES product_statuses(id),
        CONSTRAINT fk_tracking_location FOREIGN KEY (location_id) REFERENCES storage_locations(id),
        CONSTRAINT fk_tracking_stage FOREIGN KEY (current_stage_id) REFERENCES lifecycle_stages(id),
        CONSTRAINT fk_tracking_prev_stage FOREIGN KEY (previous_stage_id) REFERENCES lifecycle_stages(id)
    );
END;

IF OBJECT_ID('product_quality_control', 'U') IS NULL
BEGIN
    CREATE TABLE product_quality_control (
        id INT PRIMARY KEY IDENTITY(1,1),
        product_tracking_id INT NOT NULL,
        inspected_by INT NOT NULL,
        inspected_at DATETIME2 DEFAULT GETDATE() NOT NULL,
        weight_grams DECIMAL(6,2) NOT NULL,
        pressure_drop DECIMAL(6,3) NOT NULL,
        visual_pass BIT NOT NULL,
        inspection_result NVARCHAR(20) NOT NULL CHECK (inspection_result IN ('Passed', 'B-Ware', 'Waste', 'Quarantine')),
        notes NVARCHAR(255),

        CONSTRAINT fk_qc_print_job FOREIGN KEY (product_tracking_id) REFERENCES product_tracking(id),
        CONSTRAINT fk_qc_user_product FOREIGN KEY (inspected_by) REFERENCES users(id)
    );
END;

IF OBJECT_ID('product_status_history', 'U') IS NULL
BEGIN
    CREATE TABLE product_status_history (
        id INT PRIMARY KEY IDENTITY(1,1),
        product_tracking_id INT NOT NULL,
        from_stage_id INT NULL,
        to_stage_id INT NOT NULL,
        reason NVARCHAR(255),
        changed_by INT NOT NULL,
        changed_at DATETIME2 NOT NULL DEFAULT GETDATE(),

        CONSTRAINT fk_status_product FOREIGN KEY (product_tracking_id) REFERENCES product_tracking(id),
        CONSTRAINT fk_status_from_stage FOREIGN KEY (from_stage_id) REFERENCES lifecycle_stages(id),
        CONSTRAINT fk_status_to_stage FOREIGN KEY (to_stage_id) REFERENCES lifecycle_stages(id),
        CONSTRAINT fk_status_user FOREIGN KEY (changed_by) REFERENCES users(id)
    );
END;

-- ======= MATERIAL USAGE TRACKING ========
IF OBJECT_ID('material_usage', 'U') IS NULL
BEGIN
    CREATE TABLE material_usage (
        id INT IDENTITY PRIMARY KEY,
        product_tracking_id INT NOT NULL,
        harvest_id INT NULL,
        material_type NVARCHAR(50) NOT NULL CHECK (material_type IN ('Filament', 'Lid', 'Seal')),
        lot_number NVARCHAR(100) NOT NULL,
        used_quantity DECIMAL(10, 2) NOT NULL,
        used_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        used_by INT NOT NULL,
        reason NVARCHAR(255),

        CONSTRAINT fk_usage_product FOREIGN KEY (product_tracking_id) REFERENCES product_tracking(id),
        CONSTRAINT fk_usage_harvest FOREIGN KEY (harvest_id) REFERENCES product_harvest(id),
        CONSTRAINT fk_usage_user FOREIGN KEY (used_by) REFERENCES users(id)
    );
END;

-- ======== QUARANTINED PRODUCTS ===========
IF OBJECT_ID('quarantined_products', 'U') IS NULL
BEGIN
    CREATE TABLE quarantined_products(
        id INT IDENTITY PRIMARY KEY,
        product_tracking_id INT NOT NULL,
        from_stage_id INT NOT NULL,
        source NVARCHAR(50) NOT NULL CHECK (source IN ('Harvest QC', 'Post-Treatment QC', 'Ad-Hoc')),
        location_id INT NULL,
        quarantine_date DATETIME2 NOT NULL DEFAULT GETDATE(),
        quarantined_by INT NOT NULL,
        quarantine_reason NVARCHAR(255) NULL,
        quarantine_status NVARCHAR(20) NOT NULL CHECK (quarantine_status IN ('Active', 'Released', 'Disposed')),
        result NVARCHAR(20) NULL CHECK (result IN ('Passed', 'B-Ware', 'Waste')),
        resolved_at DATETIME2 NULL,
        resolved_by INT NULL,

        CONSTRAINT fk_quarantine_product FOREIGN KEY (product_tracking_id) REFERENCES product_tracking(id),
        CONSTRAINT fk_quarantine_stage FOREIGN KEY (from_stage_id) REFERENCES lifecycle_stages(id),
        CONSTRAINT fk_quarantine_user FOREIGN KEY (quarantined_by) REFERENCES users(id),
        CONSTRAINT fk_quarantine_resolved_user FOREIGN KEY (resolved_by) REFERENCES users(id),
        CONSTRAINT fk_quarantine_location FOREIGN KEY (location_id) REFERENCES storage_locations(id)
    );
END;

IF OBJECT_ID('product_investigations', 'U') IS NULL
BEGIN
    CREATE TABLE product_investigations(
        id INT IDENTITY PRIMARY KEY,
        product_tracking_id INT NOT NULL,
        status VARCHAR(50) NOT NULL CHECK (status IN ('Under Investigation', 'Cleared A-Ware', 'Cleared B-Ware', 'Disposed')),
        deviation_number VARCHAR(50),
        comment NVARCHAR(255),
        created_by INT NOT NULL,
        created_at DATETIME2 DEFAULT GETDATE() NOT NULL,
        resolved_at DATETIME2 NULL,
        resolved_by INT NULL,

        CONSTRAINT fk_investigation_product FOREIGN KEY (product_tracking_id) REFERENCES product_tracking(id),
        CONSTRAINT fk_investigation_user FOREIGN KEY (created_by) REFERENCES users(id),
        CONSTRAINT fk_investigation_resolved_user FOREIGN KEY (resolved_by) REFERENCES users(id)
    );
END;

-- ========== TREATMENT TRACKING ==========
IF OBJECT_ID('treatment_batches', 'U') IS NULL
BEGIN
    CREATE TABLE treatment_batches (
        id INT PRIMARY KEY IDENTITY(1,1),
        sent_by INT NOT NULL,
        sent_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        received_at DATETIME2,
        notes NVARCHAR(255),
        status NVARCHAR(50) NOT NULL CHECK (status IN ('Shipped', 'Inspected')),

        CONSTRAINT fk_treatment_sent_by FOREIGN KEY (sent_by) REFERENCES users(id)
    );
END;

IF OBJECT_ID('treatment_batch_products', 'U') IS NULL
BEGIN
    CREATE TABLE treatment_batch_products (
        id INT PRIMARY KEY IDENTITY(1,1),
        batch_id INT NOT NULL,
        product_tracking_id INT NOT NULL UNIQUE,
        surface_treat BIT NOT NULL,
        sterilize BIT NOT NULL,

        CONSTRAINT fk_treatment_batch FOREIGN KEY (batch_id) REFERENCES treatment_batches(id),
        CONSTRAINT fk_treatment_product FOREIGN KEY (product_tracking_id) REFERENCES product_tracking(id)
    );
END;

IF OBJECT_ID('post_treatment_inspections', 'U') IS NULL
BEGIN
    CREATE TABLE post_treatment_inspections (
        id INT PRIMARY KEY IDENTITY(1,1),
        product_tracking_id INT NOT NULL,
        inspected_by INT NOT NULL,
        inspected_at DATETIME2 DEFAULT GETDATE(),
        visual_pass BIT NOT NULL,
        surface_treated BIT NOT NULL,
        sterilized BIT NOT NULL,
        qc_result NVARCHAR(20) NOT NULL CHECK (qc_result IN ('Passed', 'B-Ware', 'Quarantine', 'Waste')),
        notes NVARCHAR(255),

        CONSTRAINT fk_post_qc_product FOREIGN KEY (product_tracking_id) REFERENCES product_tracking(id),
        CONSTRAINT fk_post_qc_user FOREIGN KEY (inspected_by) REFERENCES users(id)
    );
END;

-- ========= SALES CATALOGUE ===========
-- IF OBJECT_ID('sales_catalogue', 'U') IS NULL
-- BEGIN 
--     CREATE TABLE sales_catalogue (
--         id INT PRIMARY KEY IDENTITY(1,1),
--         article_number INT UNIQUE NOT NULL,
--         package_name VARCHAR(100) UNIQUE NOT NULL,
--         package_desc VARCHAR (255) NOT NULL,
--         price DECIMAL(10,2) NOT NULL,
--         is_active BIT NOT NULL
--     );
-- END;

-- IF OBJECT_ID('sales_catalogue_products', 'U') IS NULL
-- BEGIN 
--     CREATE TABLE sales_catalogue_products (
--         id INT PRIMARY KEY IDENTITY(1,1),
--         catalogue_id INT NOT NULL,
--         product_sku_id INT NOT NULL,
--         product_quantity INT NOT NULL CHECK (product_quantity > 0),

--         CONSTRAINT fk_scprod_sku FOREIGN KEY (product_sku_id) REFERENCES product_skus(id),
--         CONSTRAINT fk_scprod_catalogue FOREIGN KEY (catalogue_id) REFERENCES sales_catalogue(id),
--         CONSTRAINT uc_scprod UNIQUE (catalogue_id, product_sku_id)
--     );
-- END;

-- IF OBJECT_ID('sales_catalogue_supplements', 'U') IS NULL
-- BEGIN
--     CREATE TABLE sales_catalogue_supplements(
--         id INT PRIMARY KEY IDENTITY(1,1),
--         catalogue_id INT NOT NULL,
--         supplement_sku_id INT NOT NULL,
--         supplement_quantity INT NOT NULL CHECK (supplement_quantity > 0),

--         CONSTRAINT fk_scsupp_supp FOREIGN KEY (supplement_sku_id) REFERENCES supplement_skus(id),
--         CONSTRAINT fk_scsupp_catalogue FOREIGN KEY (catalogue_id) REFERENCES sales_catalogue(id),
--         CONSTRAINT uc_scsupp UNIQUE (catalogue_id, supplement_id)
--     );
-- END;

-- ========== ORDER FULFILLMENT ==========
IF OBJECT_ID('customers', 'U') IS NULL
BEGIN
    CREATE TABLE customers (
        id INT PRIMARY KEY IDENTITY(1,1),
        customer_name NVARCHAR(50) NOT NULL UNIQUE
    );
END;

IF OBJECT_ID('orders', 'U') IS NULL
BEGIN
    CREATE TABLE orders (
        id INT PRIMARY KEY IDENTITY(1,1),
        parent_order_id INT,
        customer_id INT NOT NULL,
        order_date DATETIME2 NOT NULL DEFAULT GETDATE(),
        order_creator_id INT NOT NULL,
        status NVARCHAR(20) NOT NULL CHECK (status IN ('Processing', 'Shipped', 'Completed', 'Canceled')),
        updated_at DATETIME2 DEFAULT GETDATE(),
        updated_by INT NOT NULL,
        notes NVARCHAR(255),

        CONSTRAINT fk_order_parent FOREIGN KEY (parent_order_id) REFERENCES orders(id),
        CONSTRAINT fk_order_customer FOREIGN KEY (customer_id) REFERENCES customers(id),
        CONSTRAINT fk_order_creator FOREIGN KEY (order_creator_id) REFERENCES users(id),
        CONSTRAINT fk_order_updated_by FOREIGN KEY (updated_by) REFERENCES users(id)
    );
END;

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes WHERE name = 'ix_orders_customer_date'
        AND object_id = OBJECT_ID('orders')
)
BEGIN 
    CREATE INDEX ix_orders_customer_date ON orders(customer_id, order_date);
END;

IF OBJECT_ID('order_items', 'U') IS NULL
BEGIN
    CREATE TABLE order_items (
        id INT PRIMARY KEY IDENTITY(1,1),
        order_id INT NOT NULL,
        product_sku_id INT NOT NULL,
        quantity INT NOT NULL CHECK (quantity > 0),

        CONSTRAINT fk_order_items_order FOREIGN KEY (order_id) REFERENCES orders(id),
        CONSTRAINT fk_order_items_sku FOREIGN KEY (product_sku_id) REFERENCES product_skus(id)
    );
END;

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes WHERE name = 'ix_oi_order'
        AND object_id = OBJECT_ID('order_items')
)
BEGIN
    CREATE INDEX ix_oi_order ON order_items(order_id);
END;

IF OBJECT_ID('shipments', 'U') IS NULL
BEGIN
    CREATE TABLE shipments (
        id INT PRIMARY KEY IDENTITY(1,1),
        customer_id INT NOT NULL,
        order_id INT,
        creator_id INT NOT NULL,
        created_date DATETIME2 NOT NULL DEFAULT GETDATE(),
        ship_date DATETIME2,
        delivery_date DATETIME2,
        status NVARCHAR(20) NOT NULL CHECK (status IN ('Pending', 'Shipped', 'In Transit', 'Delivered', 'Returned', 'Canceled')),
        updated_at DATETIME2 DEFAULT GETDATE(),
        updated_by INT NOT NULL,
        tracking_number NVARCHAR(50),
        carrier NVARCHAR(50),
        notes NVARCHAR(255),

        CONSTRAINT fk_shipment_customer FOREIGN KEY (customer_id) REFERENCES customers(id),
        CONSTRAINT fk_shipment_order FOREIGN KEY (order_id) REFERENCES orders(id),
        CONSTRAINT fk_shipment_creator FOREIGN KEY (creator_id) REFERENCES users(id),
        CONSTRAINT fk_shipment_update_user FOREIGN KEY (updated_by) REFERENCES users(id)
    );
END;

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes WHERE name = 'ix_shipments_customer_date'
        AND object_id = OBJECT_ID('shipments')
)
BEGIN
    CREATE INDEX ix_shipments_customer_date ON shipments(customer_id, created_date);
END;

IF OBJECT_ID('shipment_sku_items', 'U') IS NULL
BEGIN 
    CREATE TABLE shipment_sku_items(
        id INT PRIMARY KEY IDENTITY(1, 1),
        shipment_id INT NOT NULL,
        product_sku_id INT NOT NULL,
        quantity INT NOT NULL CHECK (quantity > 0),

        CONSTRAINT fk_shipsku_shipment FOREIGN KEY (shipment_id) REFERENCES shipments(id),
        CONSTRAINT sk_shipsku_sku FOREIGN KEY (product_sku_id) REFERENCES product_skus(id)
    );
END;

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes WHERE name = 'ix_shipsku_shipment'
        AND object_id = OBJECT_ID('shipment_sku_items')
)
BEGIN
    CREATE INDEX ix_shipsku_shipment ON shipment_sku_items(shipment_id);
END;

IF OBJECT_ID('shipment_unit_items', 'U') IS NULL
BEGIN
    CREATE TABLE shipment_unit_items(
        id INT PRIMARY KEY IDENTITY(1, 1),
        shipment_id INT NOT NULL,
        product_tracking_id INT NOT NULL UNIQUE,

        CONSTRAINT fk_shipunit_shipment FOREIGN KEY (shipment_id) REFERENCES shipments(id),
        CONSTRAINT fk_shipunit_product FOREIGN KEY (product_tracking_id) REFERENCES product_tracking(id)
    );
END;

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes WHERE name = 'ix_shipunit_shipment'
        AND object_id = OBJECT_ID('shipment_unit_items')
)
BEGIN
    CREATE INDEX ix_shipunit_shipment ON shipment_unit_items(shipment_id);
END;

-- ========== AUDITS ==========
IF OBJECT_ID('audit_log', 'U') IS NULL
BEGIN
    CREATE TABLE audit_log (
        id INT PRIMARY KEY IDENTITY(1,1),
        table_name NVARCHAR(100) NOT NULL,
        record_id INT NOT NULL,
        field_name NVARCHAR(100) NOT NULL,
        old_value NVARCHAR(MAX),
        new_value NVARCHAR(MAX),
        reason NVARCHAR(255) NOT NULL,
        changed_by INT NOT NULL,
        changed_at DATETIME2 NOT NULL DEFAULT GETDATE(),

        CONSTRAINT fk_audit_user FOREIGN KEY (changed_by) REFERENCES users(id)
    );
END;

-- ======= ISSUE CODES =======
IF OBJECT_ID('issue_reasons', 'U') IS NULL
BEGIN
    CREATE TABLE issue_reasons (
        id INT IDENTITY PRIMARY KEY,
        reason_code NVARCHAR(50) NOT NULL UNIQUE,
        reason_label NVARCHAR(120) NOT NULL,
        category NVARCHAR(50) NOT NULL,
        default_outcome NVARCHAR(20) NULL CHECK (default_outcome IN ('B-Ware', 'Waste', 'Quarantine')),
        severity TINYINT NULL,
        is_active BIT NOT NULL DEFAULT 1,
        created_at DATETIME2 NOT NULL DEFAULT GETDATE()
    );
END;

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

IF OBJECT_ID('product_quality_control_reasons', 'U') IS NULL
BEGIN
    CREATE TABLE product_quality_control_reasons (
        id INT IDENTITY PRIMARY KEY,
        qc_id INT NOT NULL,
        reason_id INT NOT NULL,

        CONSTRAINT fk_pqc_reason_qc FOREIGN KEY (qc_id) REFERENCES product_quality_control(id),
        CONSTRAINT fk_pqc_reason_reason FOREIGN KEY (reason_id) REFERENCES issue_reasons(id),
        CONSTRAINT uc_pqc_reason UNIQUE (qc_id, reason_id)
    );
END;

IF OBJECT_ID('post_treatment_inspection_reasons', 'U') IS NULL
BEGIN
    CREATE TABLE post_treatment_inspection_reasons (
        id INT IDENTITY PRIMARY KEY,
        inspection_id INT NOT NULL,
        reason_id INT NOT NULL,

        CONSTRAINT fk_pti_reason_inspection FOREIGN KEY (inspection_id) REFERENCES post_treatment_inspections(id),
        CONSTRAINT fk_pti_reason_reason FOREIGN KEY (reason_id) REFERENCES issue_reasons(id),
        CONSTRAINT uc_pti_reason UNIQUE (inspection_id, reason_id)
    );
END;

IF OBJECT_ID('quarantined_product_reasons', 'U') IS NULL
BEGIN
    CREATE TABLE quarantined_product_reasons (
        id INT IDENTITY PRIMARY KEY,
        quarantine_id INT NOT NULL,
        reason_id INT NOT NULL,

        CONSTRAINT fk_qpr_quarantine FOREIGN KEY (quarantine_id) REFERENCES quarantined_products(id),
        CONSTRAINT fk_qpr_reason FOREIGN KEY (reason_id) REFERENCES issue_reasons(id),
        CONSTRAINT uc_qpr UNIQUE (quarantine_id, reason_id)
    );
END;

-- ======= HELPER TABLES
IF OBJECT_ID('etl_harvest_map','U') IS NULL
BEGIN
  CREATE TABLE etl_harvest_map(
    product_id_bigint BIGINT NOT NULL PRIMARY KEY,   -- 1 product -> 1 harvest
    harvest_id        INT    NOT NULL UNIQUE,        -- and each harvest used once
    CONSTRAINT fk_map_harvest
      FOREIGN KEY (harvest_id) REFERENCES dbo.product_harvest(id)
  );
END;

IF OBJECT_ID('etl_treatment_map','U') IS NULL
BEGIN
CREATE TABLE etl_treatment_map(
    treatment_id BIGINT NOT NULL PRIMARY KEY,
    batch_id     INT    NOT NULL UNIQUE,
    CONSTRAINT fk_etl_treatment_batch
    FOREIGN KEY (batch_id) REFERENCES dbo.treatment_batches(id)
);
END
