from flask import Blueprint, render_template, request, jsonify
from app.models import Project, Estimate
from app import db, csrf
import subprocess
import os
from datetime import datetime

bp = Blueprint('main', __name__)

@bp.route('/')
@bp.route('/dashboard')
def dashboard():
    """Dashboard showing overview of all projects"""
    # Get filter parameter from query string (default to 'active')
    filter_type = request.args.get('filter', 'active')

    # Build query based on filter
    query = db.session.query(Project)
    if filter_type == 'active':
        query = query.filter(Project.is_active == True)
    elif filter_type == 'closed':
        query = query.filter(Project.is_active == False)
    # 'all' shows everything

    projects = query.order_by(Project.updated_at.desc()).all()

    # Calculate summary statistics
    total_projects = len(projects)
    total_estimates = db.session.query(Estimate).count()
    total_value = sum(project.total_value() for project in projects)

    # Get recent activity (last 5 updated projects)
    recent_projects = projects[:5]

    return render_template('index.html',
                         projects=projects,
                         recent_projects=recent_projects,
                         total_projects=total_projects,
                         total_estimates=total_estimates,
                         total_value=total_value,
                         current_filter=filter_type)

@bp.route('/backup', methods=['POST'])
@csrf.exempt
def backup_to_git():
    """
    Perform a git backup of the entire codebase and database.
    This creates a commit with all changes and pushes to the remote repository.
    """
    try:
        # Get the project root directory (where the .git folder is)
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

        # Change to project root directory
        os.chdir(project_root)

        # Check if there are any changes
        status_result = subprocess.run(
            ['git', 'status', '--porcelain'],
            capture_output=True,
            text=True,
            timeout=10
        )

        changes = status_result.stdout.strip()

        if not changes:
            return jsonify({
                'success': True,
                'message': 'No changes to backup. Repository is up to date.',
                'files_changed': 0,
                'commit_hash': None,
                'push_status': 'No push needed'
            })

        # Count files changed
        files_changed = len(changes.split('\n'))

        # Add all changes (including database)
        add_result = subprocess.run(
            ['git', 'add', '.'],
            capture_output=True,
            text=True,
            timeout=30
        )

        if add_result.returncode != 0:
            raise Exception(f"Git add failed: {add_result.stderr}")

        # Create commit with timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        commit_message = f"Automated backup - {timestamp}"

        commit_result = subprocess.run(
            ['git', 'commit', '-m', commit_message],
            capture_output=True,
            text=True,
            timeout=30
        )

        if commit_result.returncode != 0:
            # Check if it's just a "nothing to commit" message
            if "nothing to commit" in commit_result.stdout.lower():
                return jsonify({
                    'success': True,
                    'message': 'No changes to commit. Working tree is clean.',
                    'files_changed': 0,
                    'commit_hash': None,
                    'push_status': 'No push needed'
                })
            raise Exception(f"Git commit failed: {commit_result.stderr}")

        # Get the commit hash
        hash_result = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            capture_output=True,
            text=True,
            timeout=10
        )
        commit_hash = hash_result.stdout.strip()

        # Push to remote
        push_result = subprocess.run(
            ['git', 'push'],
            capture_output=True,
            text=True,
            timeout=60
        )

        if push_result.returncode != 0:
            # Commit was successful but push failed - still report as partial success
            return jsonify({
                'success': True,
                'message': f'Backup committed locally (hash: {commit_hash}), but push failed. Check your network connection or remote repository.',
                'files_changed': files_changed,
                'commit_hash': commit_hash,
                'push_status': f'Failed: {push_result.stderr}',
                'warning': 'Push to remote failed'
            })

        # Success!
        return jsonify({
            'success': True,
            'message': f'Backup completed successfully! {files_changed} file(s) backed up.',
            'files_changed': files_changed,
            'commit_hash': commit_hash,
            'push_status': 'Successfully pushed to remote'
        })

    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': 'Git operation timed out. The repository may be too large or the connection is slow.'
        }), 500

    except FileNotFoundError:
        return jsonify({
            'success': False,
            'error': 'Git is not installed or not found in the system PATH.'
        }), 500

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Backup failed: {str(e)}'
        }), 500