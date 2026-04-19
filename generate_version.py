#!/usr/bin/env python3
"""Generate dynamic version number based on git commit information."""

import subprocess
import os
import re
from datetime import datetime
import tomllib

def get_base_version():
    """Get base version from pyproject.toml."""
    pyproject_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pyproject.toml')
    if os.path.exists(pyproject_path):
        with open(pyproject_path, 'rb') as f:
            pyproject = tomllib.load(f)
        return pyproject.get('project', {}).get('version', '0.2.0')
    return '0.2.0'

def get_git_info():
    """Get git commit information."""
    try:
        # Get the current commit hash
        commit_hash = subprocess.check_output(
            ['git', 'rev-parse', '--short', 'HEAD'],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            universal_newlines=True
        ).strip()
        
        # Get the commit date
        commit_date = subprocess.check_output(
            ['git', 'show', '-s', '--format=%ci', 'HEAD'],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            universal_newlines=True
        ).strip()
        
        return commit_hash, commit_date
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Fallback if git is not available
        return None, None

def generate_version():
    """Generate dynamic version number."""
    base_version = get_base_version()
    commit_hash, commit_date = get_git_info()
    
    if commit_hash:
        # Extract date components from commit date
        # Format: 2024-01-01 12:00:00 +0000
        date_str = commit_date.split(' ')[0]
        version_date = date_str.replace('-', '')
        
        # Create version string: v<base>-<date>-<commit-hash>
        version = f"v{base_version}-{version_date}-{commit_hash}"
    else:
        # Fallback to timestamp-based version
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        version = f"v{base_version}-dev-{timestamp}"
    
    return version

def update_demo_version():
    """Update the version in the demo index.html file."""
    version = generate_version()
    demo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'demo', 'index.html')
    
    if os.path.exists(demo_path):
        with open(demo_path, 'r') as f:
            content = f.read()
        
        # Use regex to replace version badge content, aria-label and title, supports repeated runs
        updated_content = re.sub(
            r'<div class="version-badge" aria-label="版本 .*?" title="版本 .*?">.*?</div>',
            f'<div class="version-badge" aria-label="版本 {version}" title="版本 {version}">{version}</div>',
            content
        )
        
        with open(demo_path, 'w') as f:
            f.write(updated_content)
        
        print(f"Updated demo version to: {version}")
        return version
    else:
        print(f"Demo file not found: {demo_path}")
        return None

if __name__ == "__main__":
    version = update_demo_version()
    if version:
        print(f"Version generated: {version}")
    else:
        print("Failed to generate version")
