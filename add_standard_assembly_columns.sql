-- Add new columns to existing assemblies table for standard assemblies integration
-- Run this SQL script against your SQLite database

-- Add standard_assembly_id column to assemblies table
ALTER TABLE assemblies ADD COLUMN standard_assembly_id INTEGER;

-- Add standard_assembly_version column to assemblies table  
ALTER TABLE assemblies ADD COLUMN standard_assembly_version VARCHAR(20);

-- Create the new standard_assemblies table
CREATE TABLE IF NOT EXISTS standard_assemblies (
    standard_assembly_id INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100) NOT NULL,
    base_assembly_id INTEGER,
    version VARCHAR(20) NOT NULL DEFAULT '1.0',
    is_active BOOLEAN DEFAULT 1,
    is_template BOOLEAN DEFAULT 0,
    created_by VARCHAR(100),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (base_assembly_id) REFERENCES standard_assemblies (standard_assembly_id)
);

-- Create the standard_assembly_components table
CREATE TABLE IF NOT EXISTS standard_assembly_components (
    component_id INTEGER PRIMARY KEY,
    standard_assembly_id INTEGER NOT NULL,
    part_id INTEGER NOT NULL,
    quantity DECIMAL(10, 3) NOT NULL DEFAULT 1.000,
    unit_of_measure VARCHAR(20) DEFAULT 'EA',
    notes TEXT,
    sort_order INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (standard_assembly_id) REFERENCES standard_assemblies (standard_assembly_id),
    FOREIGN KEY (part_id) REFERENCES parts (part_id)
);

-- Create the assembly_versions table
CREATE TABLE IF NOT EXISTS assembly_versions (
    version_id INTEGER PRIMARY KEY,
    standard_assembly_id INTEGER NOT NULL,
    version_number VARCHAR(20) NOT NULL,
    notes TEXT,
    created_by VARCHAR(100),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (standard_assembly_id) REFERENCES standard_assemblies (standard_assembly_id)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_standard_assemblies_category ON standard_assemblies(category);
CREATE INDEX IF NOT EXISTS idx_standard_assemblies_active ON standard_assemblies(is_active);
CREATE INDEX IF NOT EXISTS idx_standard_assemblies_template ON standard_assemblies(is_template);
CREATE INDEX IF NOT EXISTS idx_standard_assembly_components_assembly ON standard_assembly_components(standard_assembly_id);
CREATE INDEX IF NOT EXISTS idx_standard_assembly_components_part ON standard_assembly_components(part_id);
CREATE INDEX IF NOT EXISTS idx_assembly_versions_assembly ON assembly_versions(standard_assembly_id);

-- Success message
SELECT 'Standard Assemblies migration completed successfully!' as status;