-- Migration script to convert Components to Parts-based system
-- WARNING: Make a backup before running this script!

BEGIN TRANSACTION;

-- Step 1: Create the new assembly_parts table
CREATE TABLE IF NOT EXISTS assembly_parts (
    assembly_part_id INTEGER PRIMARY KEY AUTOINCREMENT,
    assembly_id INTEGER NOT NULL,
    part_id INTEGER NOT NULL,
    quantity DECIMAL(10,3) NOT NULL DEFAULT 1.000,
    unit_of_measure VARCHAR(20) DEFAULT 'EA',
    sort_order INTEGER DEFAULT 0,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (assembly_id) REFERENCES assemblies (assembly_id),
    FOREIGN KEY (part_id) REFERENCES parts (part_id)
);

-- Step 2: Create an index for better performance
CREATE INDEX IF NOT EXISTS idx_assembly_parts_assembly_id ON assembly_parts(assembly_id);
CREATE INDEX IF NOT EXISTS idx_assembly_parts_part_id ON assembly_parts(part_id);

-- Step 3: Migrate existing components to parts
-- First, create parts from unique components that don't exist in parts table
INSERT INTO parts (category, manufacturer, part_number, description, price, effective_date, created_at, updated_at)
SELECT DISTINCT 
    'General' as category,
    'Unknown' as manufacturer,
    COALESCE(c.part_number, 'COMP-' || c.component_id) as part_number,
    c.component_name as description,
    c.unit_price as price,
    date('now') as effective_date,
    c.created_at,
    c.updated_at
FROM components c
LEFT JOIN parts p ON p.part_number = COALESCE(c.part_number, 'COMP-' || c.component_id)
WHERE p.part_id IS NULL;

-- Step 4: Create assembly_parts records for all existing components
INSERT INTO assembly_parts (assembly_id, part_id, quantity, unit_of_measure, sort_order, notes, created_at, updated_at)
SELECT 
    c.assembly_id,
    p.part_id,
    c.quantity,
    c.unit_of_measure,
    c.sort_order,
    c.description as notes,
    c.created_at,
    c.updated_at
FROM components c
JOIN parts p ON p.part_number = COALESCE(c.part_number, 'COMP-' || c.component_id);

-- Step 5: Migrate price history from components to parts
-- Only migrate if the component's part doesn't already have price history
INSERT INTO parts_price_history (part_id, old_price, new_price, changed_at, changed_reason)
SELECT DISTINCT
    p.part_id,
    ph.old_price,
    ph.new_price,
    ph.changed_at,
    'Migrated from component: ' || ph.changed_reason
FROM price_history ph
JOIN components c ON ph.component_id = c.component_id
JOIN parts p ON p.part_number = COALESCE(c.part_number, 'COMP-' || c.component_id)
WHERE NOT EXISTS (
    SELECT 1 FROM parts_price_history pph 
    WHERE pph.part_id = p.part_id 
    AND pph.changed_at = ph.changed_at
);

-- Step 6: Update assembly relationships in the assemblies table
-- (The model change will handle this, but we can add a trigger to maintain backward compatibility)

-- Verification queries (run these to check the migration)
-- SELECT 'Components before migration:', COUNT(*) FROM components;
-- SELECT 'Parts after migration:', COUNT(*) FROM parts;
-- SELECT 'Assembly parts after migration:', COUNT(*) FROM assembly_parts;
-- SELECT 'Price history records migrated:', COUNT(*) FROM parts_price_history WHERE changed_reason LIKE 'Migrated%';

COMMIT;

-- Optional: After verifying the migration is successful, you can drop the old tables
-- (Uncomment these lines only after thorough testing)
-- DROP TABLE IF EXISTS price_history;
-- DROP TABLE IF EXISTS components;

-- Success message
SELECT 'Migration completed successfully! Components have been converted to Parts-based system.' as result;