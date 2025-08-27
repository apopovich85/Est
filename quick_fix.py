import os
from pathlib import Path

# Create necessary directories
current_dir = Path.cwd()
(current_dir / 'database').mkdir(exist_ok=True)
(current_dir / 'uploads').mkdir(exist_ok=True)

# Test write permissions
test_file = current_dir / 'database' / 'test.txt'
test_file.write_text('test')
test_file.unlink()

print("✓ Directories created and writable")
print("Now run: python init_db.py")