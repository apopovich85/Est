# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Flask-based electrical panel and control system estimating application. It manages projects, estimates, assemblies, components, and motors/loads with versioning, revision control, and comprehensive BOM (Bill of Materials) reporting.

**Key Domain Concepts:**
- **Projects** contain multiple **Estimates** (supporting and optional)
- **Estimates** contain **Assemblies** and individual **Components**
- **Assemblies** are collections of **Parts** that can be based on **Standard Assemblies** with versioning
- **Motors/Loads** are tracked separately within projects with VFD selection and revision control
- **Standard Assemblies** support version control with base/derived version relationships

## Development Commands

### Running the Application
```bash
# Using run.py (recommended)
venv/Scripts/python.exe run.py

# Or using Flask directly
venv/Scripts/python.exe -m flask run --port=5001

# Application runs at: http://127.0.0.1:5001
```

### Database Migrations
```bash
# Run migration scripts (located in project root)
venv/Scripts/python.exe <migration_script>.py

# Example: Add database index for performance
venv/Scripts/python.exe add_estimate_name_index.py
```

### Testing
```bash
# Syntax check Python files
venv/Scripts/python.exe -m py_compile <file.py>

# Validate Jinja2 templates
venv/Scripts/python.exe -c "from jinja2 import Environment, FileSystemLoader; env = Environment(loader=FileSystemLoader('app/templates')); template = env.get_template('<template_path>'); print('Template syntax OK')"
```

### Environment Setup
```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Architecture & Data Model

### Database: SQLite with Foreign Key Constraints
**CRITICAL:** Foreign key constraints are explicitly enabled in `app/__init__.py` via SQLAlchemy event listener. Without this, cascade deletes will not work.

### Core Entity Relationships

**Project Hierarchy:**
```
Project (project_id)
├─ Estimates (estimate_id, is_optional)
│  ├─ Assemblies (assembly_id, standard_assembly_id, quantity)
│  │  └─ AssemblyParts (quantity, part_id)
│  └─ EstimateComponents (individual components, part_id)
└─ Motors (motor_id, selected_vfd_part_id)
   └─ MotorRevisions (revision tracking)
```

**Standard Assembly Versioning:**
```
StandardAssembly (base_assembly_id=NULL) [Base version]
├─ StandardAssembly (base_assembly_id=parent) [Derived v1.1]
├─ StandardAssembly (base_assembly_id=parent) [Derived v1.2]
└─ StandardAssembly (base_assembly_id=parent) [Derived v1.3]
```

**Key Relationships:**
- `Assembly.standard_assembly_id` → Points to specific `StandardAssembly` version
- `Assembly.standard_assembly_version` → Stores version string (e.g., "1.3")
- When changing versions, lookup must check both base assembly and derived versions using `base_assembly_id`

### Cascade Delete Behavior
Deleting a **Project** cascades to:
- All Estimates (supporting and optional)
  - All Assemblies → AssemblyParts
  - All EstimateComponents
  - All EstimateRevisions
- All Motors → MotorRevisions

### Blueprint Structure
Application uses Flask blueprints with URL prefixes:
- `/` - main (dashboard)
- `/projects` - projects management
- `/estimates` - estimate management
- `/assemblies` - assembly operations
- `/components` - component/parts database
- `/parts` - parts management
- `/standard_assemblies` - standard assembly templates
- `/categories` - category management
- `/labor-rates` - labor rate configuration
- `/motors` - motors blueprint (no prefix)
- `/operator-desk` - operator desk wizard

## Critical Code Patterns

### Version Change Lookup Pattern
When changing assembly versions, must resolve the base assembly first:

```python
# Get current standard assembly
current_standard = StandardAssembly.query.get(assembly.standard_assembly_id)

# Find base assembly ID (could be itself or its parent)
base_id = current_standard.base_assembly_id if current_standard.base_assembly_id else current_standard.standard_assembly_id

# Search for target version in base OR derived versions
target = StandardAssembly.query.filter_by(standard_assembly_id=base_id, version=new_version).first()
if not target:
    target = StandardAssembly.query.filter_by(base_assembly_id=base_id, version=new_version).first()

# Update BOTH the ID and version string
assembly.standard_assembly_id = target.standard_assembly_id
assembly.standard_assembly_version = new_version
```

### Performance: Eager Loading
Projects list uses eager loading to avoid N+1 queries:

```python
from sqlalchemy.orm import joinedload

# Load projects with their estimates in one query
query = Project.query.options(joinedload(Project.estimates))
```

### JavaScript in Templates: Escaping
When passing data to JavaScript onclick handlers, escape single quotes:

```jinja
<!-- WRONG - breaks with apostrophes -->
onclick="function({{ id }}, '{{ name }}')"

<!-- CORRECT - escapes apostrophes -->
onclick="function({{ id }}, '{{ name|replace("'", "\\'") }}')"
```

### Jinja2 Templates: No Python Built-ins
Jinja2 templates don't have Python's `min()`, `max()`, etc. Use conditionals:

```jinja
<!-- WRONG -->
{{ min(a, b) }}

<!-- CORRECT -->
{% set result = a if a < b else b %}
{{ result }}
```

### Database Indexes
Performance-critical indexes are added via migration scripts in project root:
- `idx_estimate_name` on `estimates.estimate_name` for search performance

## Component Patterns

### Cost Calculations
- `Assembly.calculated_total` - Sum of all AssemblyPart totals (unit_price × quantity)
- `Estimate.calculated_total` - Sum of all Assembly and EstimateComponent totals
- `Estimate.grand_total` - Material cost + labor cost
- `Project.total_project_grand_total()` - Sum of non-optional estimates only

### Optional vs Supporting Estimates
- `Estimate.is_optional` flag determines if included in project totals
- Supporting estimates (is_optional=False) are included in all project calculations
- Optional estimates are shown separately and excluded from default totals

### Drag-and-Drop Reordering
Tables with `draggable-row` class and `data-estimate-id` support reordering:
- Separate table bodies: `#estimatesTableBody` and `#optionalEstimatesTableBody`
- Uses `sort_order` column for persistence
- Prevents cross-table dragging via `currentTableBody` tracking

## Data Model Computed Properties

### Project Methods
All project total methods exclude optional estimates (`is_optional=True`):
- `total_project_material_cost()` - Materials only
- `total_project_labor_cost()` - Labor only
- `total_project_grand_total()` - Materials + Labor
- `total_project_engineering_hours()`
- `total_project_panel_shop_hours()`
- `total_project_machine_assembly_hours()`

### Estimate Properties
- `calculated_total` - Material cost from assemblies and components
- `total_labor_cost` - Engineering + panel shop + machine assembly labor
- `grand_total` - Materials + labor
- `total_hours` - Sum of all labor hours

## Application State

### Database Location
- Database file: `estimates.db` in project root
- Configured in `app/__init__.py` as relative path from `app.root_path`
- Auto-created on first run via `db.create_all()`

### CSRF Protection
- Enabled globally via Flask-WTF
- Forms must include: `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>`
- AJAX requests need: `'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')`

### Pagination Defaults
- Projects list: 50 per page
- Estimate search: Results limited to 500, requires minimum 2 characters

## Template Inheritance

All pages extend `base.html` which provides:
- Navigation bar with all major sections
- Flash message display
- Bootstrap 5 styling
- Font Awesome icons
- jQuery and custom JavaScript helpers

### Common Template Patterns
- Search pages require `search_performed` flag to distinguish between initial load and search results
- Modal forms use Bootstrap 5 modal components
- Toast notifications via custom `showToast(type, title, message)` function
- Tables use `table-responsive` wrapper for horizontal scrolling

## Migration Scripts Pattern

Database schema changes are handled via standalone Python scripts in project root:
- Create new script named descriptively (e.g., `add_<feature>_column.py`)
- Use raw SQL via SQLAlchemy's `text()` for schema changes
- Check if change already exists before applying
- Always commit changes and provide success/error feedback
- Example: `add_estimate_name_index.py`
