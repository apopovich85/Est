-- WARNING: This will permanently delete all component data from estimates
-- Make sure you have a backup before running these commands

-- Drop foreign key constraints first
PRAGMA foreign_keys=off;

-- Drop the price_history table (references components)
DROP TABLE IF EXISTS price_history;

-- Drop the components table (references assemblies)
DROP TABLE IF EXISTS components;

-- Re-enable foreign key constraints
PRAGMA foreign_keys=on;

-- Optional: Clean up any orphaned assembly records that had no components
-- DELETE FROM assemblies WHERE assembly_id NOT IN (
--     SELECT DISTINCT assembly_id FROM components WHERE assembly_id IS NOT NULL
-- );