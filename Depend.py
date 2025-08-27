#!/usr/bin/env python3
"""
Script to download all required static dependencies locally
Run this to get Bootstrap, FontAwesome, and Chart.js files
"""

import os
import urllib.request
import zipfile
import shutil
from pathlib import Path

def download_file(url, filename):
    """Download a file from URL"""
    print(f"Downloading {filename}...")
    urllib.request.urlretrieve(url, filename)
    print(f"Downloaded {filename}")

def extract_and_move(zip_file, extract_to, target_dir, files_to_copy):
    """Extract ZIP and move specific files"""
    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    
    # Find the extracted directory
    extracted_dirs = [d for d in os.listdir(extract_to) if os.path.isdir(os.path.join(extract_to, d))]
    
    if extracted_dirs:
        source_dir = os.path.join(extract_to, extracted_dirs[0])
        
        # Copy specified files
        for file_pattern, target_subdir in files_to_copy:
            target_path = os.path.join(target_dir, target_subdir)
            os.makedirs(target_path, exist_ok=True)
            
            # Find and copy files matching pattern
            for root, dirs, files in os.walk(source_dir):
                for file in files:
                    if file_pattern in file:
                        source_file = os.path.join(root, file)
                        target_file = os.path.join(target_path, file)
                        shutil.copy2(source_file, target_file)
                        print(f"Copied {file} to {target_subdir}")

def download_dependencies():
    """Download all required static dependencies"""
    
    # Create static directories
    static_dirs = ['static/css', 'static/js', 'static/images']
    for directory in static_dirs:
        os.makedirs(directory, exist_ok=True)
    
    # Create temporary download directory
    temp_dir = 'temp_downloads'
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        # Download Bootstrap 5.3.2
        bootstrap_url = "https://github.com/twbs/bootstrap/releases/download/v5.3.2/bootstrap-5.3.2-dist.zip"
        bootstrap_zip = os.path.join(temp_dir, "bootstrap.zip")
        download_file(bootstrap_url, bootstrap_zip)
        
        extract_and_move(
            bootstrap_zip, 
            temp_dir, 
            'static',
            [
                ('bootstrap.min.css', 'css'),
                ('bootstrap.bundle.min.js', 'js')
            ]
        )
        
        # Download FontAwesome 6.5.0
        fontawesome_url = "https://use.fontawesome.com/releases/v6.5.0/fontawesome-free-6.5.0-web.zip"
        fontawesome_zip = os.path.join(temp_dir, "fontawesome.zip")
        download_file(fontawesome_url, fontawesome_zip)
        
        extract_and_move(
            fontawesome_zip,
            temp_dir,
            'static',
            [
                ('all.min.css', 'css'),
                ('fontawesome.min.css', 'css')
            ]
        )
        
        # Copy webfonts
        fa_extract_dir = os.path.join(temp_dir, [d for d in os.listdir(temp_dir) if 'fontawesome' in d][0])
        webfonts_source = os.path.join(fa_extract_dir, 'webfonts')
        webfonts_target = 'static/webfonts'
        if os.path.exists(webfonts_source):
            shutil.copytree(webfonts_source, webfonts_target, dirs_exist_ok=True)
            print("Copied FontAwesome webfonts")
        
        # Download Chart.js 4.4.0
        chartjs_url = "https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.min.js"
        chartjs_file = "static/js/chart.min.js"
        download_file(chartjs_url, chartjs_file)
        
        print("\nAll dependencies downloaded successfully!")
        
    except Exception as e:
        print(f"Error downloading dependencies: {e}")
        print("You may need to download these manually:")
        print("1. Bootstrap 5.3.2 from https://getbootstrap.com/")
        print("2. FontAwesome 6.5.0 from https://fontawesome.com/")
        print("3. Chart.js 4.4.0 from https://www.chartjs.org/")
        
    finally:
        # Clean up temp directory
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            print("Cleaned up temporary files")

def create_placeholder_logo():
    """Create a simple placeholder logo using SVG"""
    logo_svg = '''
<svg width="30" height="30" xmlns="http://www.w3.org/2000/svg">
  <rect width="30" height="30" fill="#0d6efd" rx="3"/>
  <text x="15" y="20" text-anchor="middle" fill="white" font-family="Arial" font-size="16" font-weight="bold">E</text>
</svg>
    '''
    
    with open('static/images/logo.svg', 'w') as f:
        f.write(logo_svg.strip())
    print("Created placeholder logo")

def main():
    """Main function"""
    print("Setting up local dependencies for Flask Estimates Manager...")
    
    # Change to project directory if it exists
    if os.path.exists('project_estimates'):
        os.chdir('project_estimates')
    
    download_dependencies()
    create_placeholder_logo()
    
    print("\nSetup complete! Your project now has all required static files.")
    print("You can now run the Flask application without internet connectivity.")

if __name__ == '__main__':
    main()