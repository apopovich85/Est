# ==================================================
# run.py (Alternative startup script)
#!/usr/bin/env python3
import os
from app import create_app

app = create_app()

if __name__ == '__main__':
    os.makedirs('uploads', exist_ok=True)
    app.run(debug=True, host='127.0.0.1', port=5001)