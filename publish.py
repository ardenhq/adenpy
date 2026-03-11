#!/usr/bin/env python3
"""
PyPI Publishing Script for Arden

This script helps publish the Arden package to PyPI with proper checks.
"""

import os
import sys
import subprocess
import shutil
import re
from pathlib import Path

def run_command(cmd, check=True):
    """Run a command and return the result."""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"Error: {result.stderr}")
        sys.exit(1)
    return result

def get_current_version():
    """Get the current version from pyproject.toml."""
    try:
        with open("pyproject.toml", "r") as f:
            content = f.read()
        
        match = re.search(r'version\s*=\s*"([^"]+)"', content)
        if match:
            return match.group(1)
        else:
            print("❌ Could not find version in pyproject.toml")
            return None
    except Exception as e:
        print(f"❌ Error reading pyproject.toml: {e}")
        return None

def update_version(new_version):
    """Update the version in pyproject.toml."""
    try:
        with open("pyproject.toml", "r") as f:
            content = f.read()
        
        # Replace version (only in [project] section)
        new_content = re.sub(
            r'(\[project\].*?version\s*=\s*)"[^"]+"',
            rf'\1"{new_version}"',
            content,
            flags=re.DOTALL
        )
        
        with open("pyproject.toml", "w") as f:
            f.write(new_content)
        
        print(f"✅ Updated version to {new_version}")
        return True
    except Exception as e:
        print(f"❌ Error updating version: {e}")
        return False

def suggest_next_version(current_version):
    """Suggest next version numbers."""
    try:
        parts = current_version.split(".")
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
        
        suggestions = [
            f"{major}.{minor}.{patch + 1}",  # Patch increment
            f"{major}.{minor + 1}.0",        # Minor increment
            f"{major + 1}.0.0"               # Major increment
        ]
        return suggestions
    except:
        return ["0.1.2", "0.2.0", "1.0.0"]

def get_version_input():
    """Get version number from user input."""
    current_version = get_current_version()
    if not current_version:
        return None
    
    print(f"\n📋 Current version: {current_version}")
    
    suggestions = suggest_next_version(current_version)
    print("💡 Suggested versions:")
    for i, version in enumerate(suggestions, 1):
        labels = ["(patch)", "(minor)", "(major)"]
        print(f"   {i}. {version} {labels[i-1]}")
    
    while True:
        choice = input(f"\nEnter new version (1-3 for suggestions, or type version): ").strip()
        
        if choice in ["1", "2", "3"]:
            return suggestions[int(choice) - 1]
        elif re.match(r'^\d+\.\d+\.\d+$', choice):
            return choice
        elif choice.lower() == 'skip':
            return current_version
        else:
            print("❌ Invalid version format. Use X.Y.Z format or choose 1-3")

def check_prerequisites():
    """Check if all prerequisites are installed."""
    print("🔍 Checking prerequisites...")
    
    # Check if build and twine are installed
    try:
        import build
        import twine
        print("✅ Build tools installed")
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Run: pip install build twine")
        sys.exit(1)
    
    # Check if we're in the right directory
    if not Path("pyproject.toml").exists():
        print("❌ pyproject.toml not found. Run from package root directory.")
        sys.exit(1)
    
    print("✅ Prerequisites check passed")

def clean_build():
    """Clean previous build artifacts."""
    print("🧹 Cleaning previous builds...")
    
    dirs_to_clean = ["build", "dist", "*.egg-info"]
    for pattern in dirs_to_clean:
        for path in Path(".").glob(pattern):
            if path.is_dir():
                shutil.rmtree(path)
                print(f"   Removed {path}")
            elif path.is_file():
                path.unlink()
                print(f"   Removed {path}")

def build_package():
    """Build the package."""
    print("🔨 Building package...")
    result = run_command("python3 -m build")
    
    # Check if build artifacts exist
    dist_files = list(Path("dist").glob("*"))
    if not dist_files:
        print("❌ No build artifacts found in dist/")
        sys.exit(1)
    
    print("✅ Package built successfully")
    for file in dist_files:
        print(f"   Created: {file}")

def check_package():
    """Check the package with twine."""
    print("🔍 Checking package...")
    result = run_command("python3 -m twine check dist/*")
    print("✅ Package check passed")

def upload_to_testpypi():
    """Upload to TestPyPI."""
    print("📤 Uploading to TestPyPI...")
    print("   Username: __token__")
    print("   Password: [Enter your TestPyPI token]")
    
    result = run_command("python3 -m twine upload --repository testpypi dist/*", check=False)
    if result.returncode == 0:
        print("✅ Uploaded to TestPyPI successfully")
        print("   Test install: pip install --index-url https://test.pypi.org/simple/ ardenpy")
    else:
        print("❌ TestPyPI upload failed")
        print(result.stderr)

def upload_to_pypi():
    """Upload to PyPI."""
    print("📤 Uploading to PyPI...")
    print("   Username: __token__")
    print("   Password: [Enter your PyPI token]")
    
    result = run_command("python3 -m twine upload dist/*", check=False)
    if result.returncode == 0:
        print("✅ Uploaded to PyPI successfully!")
        print("   Install: pip install ardenpy")
        print("   View: https://pypi.org/project/ardenpy/")
    else:
        print("❌ PyPI upload failed")
        print(result.stderr)

def main():
    """Main publishing workflow."""
    print("🚀 Arden PyPI Publishing Script")
    print("=" * 40)
    
    check_prerequisites()
    
    # Ask user what they want to do
    print("\nWhat would you like to do?")
    print("1. Build package only")
    print("2. Build and upload to TestPyPI")
    print("3. Build and upload to PyPI")
    print("4. Upload existing build to TestPyPI")
    print("5. Upload existing build to PyPI")
    
    choice = input("\nEnter choice (1-5): ").strip()
    
    # Handle version input for build operations
    if choice in ["1", "2", "3"]:
        # Get new version from user
        new_version = get_version_input()
        if not new_version:
            print("❌ Version input failed")
            return
        
        # Update version in pyproject.toml
        if not update_version(new_version):
            print("❌ Failed to update version")
            return
        
        clean_build()
        build_package()
        check_package()
    
    if choice == "2":
        upload_to_testpypi()
    elif choice == "3":
        confirm = input("\n⚠️  Upload to PyPI? This will make the package public. (y/n): ")
        if confirm.lower() == 'y':
            upload_to_pypi()
        else:
            print("Cancelled")
    elif choice == "4":
        upload_to_testpypi()
    elif choice == "5":
        confirm = input("\n⚠️  Upload to PyPI? This will make the package public. (y/n): ")
        if confirm.lower() == 'y':
            upload_to_pypi()
        else:
            print("Cancelled")
    
    print("\n🎉 Publishing workflow complete!")

if __name__ == "__main__":
    main()
