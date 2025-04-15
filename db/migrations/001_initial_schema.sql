-- ====================================
-- 001_initial_schema.sql
-- Description: Initial schema setup
-- ====================================

-- ========== USER & ACCESS CONTROL ==========
IF OBJECT_ID('departments', 'U') IS NULL
BEGIN
    CREATE TABLE departments (
        id INT PRIMARY KEY IDENTITY(1,1),
        department_name NVARCHAR(50) NOT NULL UNIQUE
    );
END;

IF OBJECT_ID('application_areas', 'U') IS NULL
BEGIN
    CREATE TABLE application_areas (
        id INT PRIMARY KEY IDENTITY(1,1),
        area_name NVARCHAR(50) NOT NULL UNIQUE
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
        created_at DATETIME2 NOT NULL DEFAULT GETDATE()
    );
END;

IF OBJECT_ID('printers', 'U') IS NULL
BEGIN
    CREATE TABLE printers (
        id INT PRIMARY KEY IDENTITY(1,1),
        name NVARCHAR(100) NOT NULL UNIQUE,
        location_id INT NOT NULL,
        manufacturer NVARCHAR(100),
        model NVARCHAR(100),
        serial_number NVARCHAR(100),
        status NVARCHAR(50) NOT NULL DEFAULT 'Active',
        created_at DATETIME2 NOT NULL DEFAULT GETDATE(),

        CONSTRAINT fk_printer_location FOREIGN KEY (location_id) REFERENCES storage_locations(id)
    );
END;

-- ========== FILAMENT TRACKING ==========
-- IF OBJECT_ID('filaments', 'U') IS NULL
-- BEGIN
--     CREATE TABLE filaments (
--         id INT PRIMARY KEY IDENTITY(1,1),
--         name NVARCHAR(100) NOT NULL,
--         location_id INT NOT NULL,
--         weight_grams DECIMAL(10,2) NOT NULL,
--         material_type NVARCHAR(50) NOT NULL,
--         diameter_mm DECIMAL(4,2) NOT NULL DEFAULT 1.75,
--         created_at DATETIME2 NOT NULL DEFAULT GETDATE(),

--         CONSTRAINT fk_filament_location FOREIGN KEY (location_id) REFERENCES storage_locations(id)
--     );
-- END;

-- IF OBJECT_ID('filament_quality_control', 'U') IS NULL
-- BEGIN
--     CREATE TABLE filament_quality_control (
--         id INT PRIMARY KEY IDENTITY(1,1),
--         filament_id INT NOT NULL,
--         inspected_by INT NOT NULL,
--         inspection_date DATETIME2 NOT NULL DEFAULT GETDATE(),
--         result NVARCHAR(10) NOT NULL CHECK (result IN ('Pass', 'Fail')),
--         notes NVARCHAR(255),

--         CONSTRAINT fk_qc_user FOREIGN KEY (inspected_by) REFERENCES users(id),
--         CONSTRAINT fk_qc_filament FOREIGN KEY (filament_id) REFERENCES filaments(id)
--     );
-- END;

-- IF OBJECT_ID('filament_tracking', 'U') IS NULL
-- BEGIN
--     CREATE TABLE filament_tracking (
--         id INT PRIMARY KEY IDENTITY(1,1),
--         filament_id INT NOT NULL,
--         printer_id INT,
--         user_id INT NOT NULL,
--         status NVARCHAR(50) NOT NULL,
--         status_date DATETIME2 NOT NULL DEFAULT GETDATE(),
--         notes NVARCHAR(255),

--         CONSTRAINT fk_tracking_filament FOREIGN KEY (filament_id) REFERENCES filaments(id),
--         CONSTRAINT fk_tracking_printer FOREIGN KEY (printer_id) REFERENCES printers(id),
--         CONSTRAINT fk_tracking_user FOREIGN KEY (user_id) REFERENCES users(id)
--     );
-- END;

IF OBJECT_ID('filaments', 'U') IS NULL
BEGIN
    CREATE TABLE filaments (
        id INT PRIMARY KEY IDENTITY(1,1),
        serial_number NVARCHAR(100) NOT NULL UNIQUE,
        location_id INT NOT NULL,
        weight_grams DECIMAL(10,2) NOT NULL,
        material_type NVARCHAR(50) NOT NULL,
        created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        received_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        received_by INT NOT NULL,
        qc_result NVARCHAR(10) NOT NULL CHECK (qc_result in ('PASS', 'FAIL')),

        CONSTRAINT fk_filament_location
            FOREIGN KEY (location_id) REFERENCES storage_locations(id),
        CONSTRAINT fk_filament_user FOREIGN KEY (received_by) REFERENCES users(id)
    );
END;

IF OBJECT_ID('filament_acclimatization', 'U') IS NULL
BEGIN
    CREATE TABLE filament_acclimatization(
        id INT PRIMARY KEY IDENTITY,
        filament_id INT NOT NULL UNIQUE,
        moved_by INT NOT NULL,
        moved_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        ready_at AS DATEADD(DAY, 2, moved_at) PERSISTED,
        status NVARCHAR(50) NOT NULL DEFAULT 'In Acclimatization',

        CONSTRAINT fk_accl_fila FOREIGN KEY (filament_id) REFERENCES filaments(id),
        CONSTRAINT fk_accl_user FOREIGN KEY (moved_by) REFERENCES users(id)
    );
END;

IF OBJECT_ID('filament_mounting', 'U') IS NULL
BEGIN
    CREATE TABLE filament_mounting(
        id INT PRIMARY KEY IDENTITY,
        filament_id INT NOT NULL UNIQUE,
        printer_id INT NOT NULL,
        mounted_by INT NOT NULL,
        mounted_at DATETIME2 DEFAULT GETDATE(),
        remaining_weight DECIMAL(10,2) NOT NULL,
        status NVARCHAR(50) NOT NULL DEFAULT 'In Use',

        CONSTRAINT fk_mount_filament FOREIGN KEY (filament_id) REFERENCES filaments(id),
        CONSTRAINT fk_mount_printer FOREIGN KEY (printer_id) REFERENCES printers(id),
        CONSTRAINT fk_mount_user FOREIGN KEY (mounted_by) REFERENCES users(id)
    );
END;

-- ========== PRODUCT DEFINITIONS ==========
IF OBJECT_ID('product_types', 'U') IS NULL
BEGIN
    CREATE TABLE product_types (
        id INT PRIMARY KEY IDENTITY(1,1),
        name NVARCHAR(100) NOT NULL UNIQUE,
        average_weight DECIMAL(6,2) NOT NULL,
        percentage_change DECIMAL(5,4) NOT NULL
    );
END;

IF OBJECT_ID('product_requests', 'U') IS NULL
BEGIN
    CREATE TABLE product_requests (
        id INT PRIMARY KEY IDENTITY(1,1),
        requested_by INT NOT NULL,
        product_id INT NOT NULL,
        quantity INT NOT NULL,
        status NVARCHAR(50) DEFAULT 'Pending',
        requested_at DATETIME2 DEFAULT GETDATE(),
        notes NVARCHAR(255),

        CONSTRAINT fk_request_user FOREIGN KEY (requested_by) REFERENCES users(id),
        CONSTRAINT fk_request_product FOREIGN KEY (product_id) REFERENCES product_types(id)
    );
END;

IF OBJECT_ID('product_harvest', 'U') IS NULL
BEGIN
    CREATE TABLE product_harvest (
        id INT PRIMARY KEY IDENTITY(1,1),
        request_id INT NOT NULL,
        filament_mounting_id INT NOT NULL,
        printed_by INT NOT NULL,
        print_date DATETIME2,
        print_status NVARCHAR(50) DEFAULT 'Queued',

        CONSTRAINT fk_harvest_request FOREIGN KEY (request_id) REFERENCES product_requests(id),
        CONSTRAINT fk_harvest_filament_mounting FOREIGN KEY (filament_mounting_id) REFERENCES filament_mounting(id),
        CONSTRAINT fk_harvest_user FOREIGN KEY (printed_by) REFERENCES users(id)
    );
END;

IF OBJECT_ID('filament_usage_log', 'U') IS NULL
BEGIN
    CREATE TABLE filament_usage_log (
        id INT PRIMARY KEY IDENTITY,
        filament_id INT NOT NULL,
        harvest_id INT NOT NULL,
        used_grams DECIMAL(6, 2) NOT NULL,
        deducted_by INT NOT NULL,
        deducted_at DATETIME2 DEFAULT GETDATE(),

        CONSTRAINT fk_usage_filament FOREIGN KEY (filament_id) REFERENCES filaments(id),
        CONSTRAINT fk_usage_user FOREIGN KEY (deducted_by) REFERENCES users(id),
        CONSTRAINT fk_usage_product FOREIGN KEY (harvest_id) REFERENCES product_harvest(id)
    );
END;

IF OBJECT_ID('product_quality_control', 'U') IS NULL
BEGIN
    CREATE TABLE product_quality_control (
        id INT PRIMARY KEY IDENTITY(1,1),
        harvest_id INT NOT NULL,
        inspected_by INT NOT NULL,
        inspected_at DATETIME2 DEFAULT GETDATE(),
        weight_grams DECIMAL(6,2) NOT NULL,
        pressure_drop DECIMAL(6,2) NOT NULL,
        visual_pass BIT NOT NULL,
        inspection_result NVARCHAR(20) NOT NULL CHECK (inspection_result IN ('Passed', 'B-Ware', 'Waste')),
        notes NVARCHAR(255),

        CONSTRAINT fk_qc_print_job FOREIGN KEY (harvest_id) REFERENCES product_harvest(id),
        CONSTRAINT fk_qc_user_product FOREIGN KEY (inspected_by) REFERENCES users(id)
    );
END;

IF OBJECT_ID('product_tracking', 'U') IS NULL
BEGIN
    CREATE TABLE product_tracking (
        id INT PRIMARY KEY IDENTITY(1,1),
        harvest_id INT NOT NULL UNIQUE,
        current_status NVARCHAR(50) NOT NULL,
        location_id INT,
        last_updated_at DATETIME2 DEFAULT GETDATE(),

        CONSTRAINT fk_tracking_harvest FOREIGN KEY (harvest_id) REFERENCES product_harvest(id),
        CONSTRAINT fk_tracking_location FOREIGN KEY (location_id) REFERENCES storage_locations(id)
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
        status NVARCHAR(50) NOT NULL DEFAULT 'Shipped',

        CONSTRAINT fk_treatment_sent_by FOREIGN KEY (sent_by) REFERENCES users(id)
    );
END;

IF OBJECT_ID('treatment_batch_products', 'U') IS NULL
BEGIN
    CREATE TABLE treatment_batch_products (
        id INT PRIMARY KEY IDENTITY(1,1),
        batch_id INT NOT NULL,
        product_id INT NOT NULL UNIQUE,

        CONSTRAINT fk_treatment_batch FOREIGN KEY (batch_id) REFERENCES treatment_batches(id),
        CONSTRAINT fk_treatment_product FOREIGN KEY (product_id) REFERENCES product_tracking(id)
    );
END;

IF OBJECT_ID('post_treatment_inspections', 'U') IS NULL
BEGIN
    CREATE TABLE post_treatment_inspections (
        id INT PRIMARY KEY IDENTITY(1,1),
        product_id INT NOT NULL,
        inspected_by INT NOT NULL,
        inspected_at DATETIME2 DEFAULT GETDATE(),
        visual_pass BIT NOT NULL,
        sterilized BIT NOT NULL,
        final_result NVARCHAR(20) NOT NULL CHECK (final_result IN ('Approved for Sale', 'Internal Use', 'Rejected')),
        notes NVARCHAR(255),

        CONSTRAINT fk_post_qc_product FOREIGN KEY (product_id) REFERENCES product_tracking(id),
        CONSTRAINT fk_post_qc_user FOREIGN KEY (inspected_by) REFERENCES users(id)
    );
END;

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
        customer_id INT NOT NULL,
        order_date DATETIME2 NOT NULL DEFAULT GETDATE(),
        order_creator_id INT NOT NULL,
        status NVARCHAR(20) NOT NULL CHECK (status IN ('Processing', 'Shipped', 'Completed', 'Canceled')),
        updated_at DATETIME2 DEFAULT GETDATE(),

        CONSTRAINT fk_order_customer FOREIGN KEY (customer_id) REFERENCES customers(id),
        CONSTRAINT fk_order_creator FOREIGN KEY (order_creator_id) REFERENCES users(id)
    );
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
        tracking_number NVARCHAR(50),
        carrier NVARCHAR(50),

        CONSTRAINT fk_shipment_customer FOREIGN KEY (customer_id) REFERENCES customers(id),
        CONSTRAINT fk_shipment_order FOREIGN KEY (order_id) REFERENCES orders(id),
        CONSTRAINT fk_shipment_creator FOREIGN KEY (creator_id) REFERENCES users(id)
    );
END;

IF OBJECT_ID('shipment_items', 'U') IS NULL
BEGIN
    CREATE TABLE shipment_items (
        id INT PRIMARY KEY IDENTITY(1,1),
        shipment_id INT NOT NULL,
        product_id INT NOT NULL,
        quantity INT NOT NULL,

        CONSTRAINT fk_shipment_item_shipment FOREIGN KEY (shipment_id) REFERENCES shipments(id),
        CONSTRAINT fk_shipment_item_product FOREIGN KEY (product_id) REFERENCES product_tracking(id)
    );
END;

-- ========== VIEWS ==========
IF OBJECT_ID('v_product_lifecycle', 'V') IS NULL
BEGIN
    EXEC('CREATE VIEW v_product_lifecycle AS
        SELECT 
            pt.id AS product_id,
            pt.current_status,
            pt.last_updated_at,
            loc.location_name,

            pr.id AS request_id,
            pr.quantity AS request_quantity,
            ptype.name AS product_type_name,
            pr.status AS request_status,
            pr.requested_at,

            ph.id AS harvest_id,
            ph.print_date,
            u.display_name AS printed_by,

            pqc.inspection_result AS initial_qc_result,
            pqc.weight_grams,
            pqc.pressure_drop,
            pqc.visual_pass,

            tb.id AS treatment_batch_id,
            tb.status AS treatment_status,
            tb.sent_at AS treatment_sent_at,
            pti.final_result AS final_qc_result,
            pti.sterilized AS treatment_sterilized,

            s.id AS shipment_id,
            s.status AS shipment_status,
            s.ship_date,
            s.delivery_date,
            s.tracking_number,
            s.carrier

        FROM product_tracking pt
        LEFT JOIN storage_locations loc ON pt.location_id = loc.id
        LEFT JOIN product_harvest ph ON pt.harvest_id = ph.id
        LEFT JOIN users u ON ph.printed_by = u.id
        LEFT JOIN product_requests pr ON ph.request_id = pr.id
        LEFT JOIN product_types ptype ON pr.product_id = ptype.id
        LEFT JOIN product_quality_control pqc ON pqc.harvest_id = ph.id
        LEFT JOIN treatment_batch_products tbp ON tbp.product_id = pt.id
        LEFT JOIN treatment_batches tb ON tbp.batch_id = tb.id
        LEFT JOIN post_treatment_inspections pti ON pti.product_id = pt.id
        LEFT JOIN shipment_items si ON si.product_id = pt.id
        LEFT JOIN shipments s ON si.shipment_id = s.id');
END;