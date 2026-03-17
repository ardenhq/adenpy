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
from version_manager import VersionManager

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

def get_version_input(target_repo: str = None):
    """Get version number from user input with smart suggestions."""
    vm = VersionManager()
    
    # Show comprehensive status
    vm.print_status_report()
    
    # Get analysis for validation
    analysis = vm.analyze_version_state()
    
    current_version = analysis["local_version"]
    if not current_version:
        return None
    
    # Show current status and let user choose a version
    if target_repo:
        can_upload_current, reason = vm.validate_upload(target_repo)
        if not can_upload_current:
            print(f"\n⚠️ Current version {current_version} cannot be uploaded to {target_repo}: {reason}")
            print("Please select a different version below:")
        else:
            print(f"\n✅ Current version {current_version} can be uploaded to {target_repo}")
    
    # Get appropriate suggestions based on target
    suggestions_data = vm.suggest_next_versions()
    if target_repo and target_repo.lower() == "pypi":
        suggestions = suggestions_data["for_pypi"][:3]
        print(f"\n💡 Suggested versions for PyPI:")
    elif target_repo and target_repo.lower() == "testpypi":
        suggestions = suggestions_data["for_testpypi"][:3]
        print(f"\n🧪 Suggested versions for TestPyPI:")
    else:
        suggestions = suggest_next_version(current_version)
        print(f"\n💡 Suggested versions:")
    
    for i, version in enumerate(suggestions, 1):
        labels = ["(patch)", "(minor)", "(major)"]
        print(f"   {i}. {version} {labels[i-1] if i <= 3 else ''}")
    
    # Add option to keep current version if it's valid
    if target_repo:
        can_upload_current, _ = vm.validate_upload(target_repo)
        if can_upload_current:
            print(f"   c. {current_version} (keep current)")
    else:
        print(f"   c. {current_version} (keep current)")
    
    while True:
        choice_prompt = f"\nEnter new version (1-{len(suggestions)} for suggestions"
        if target_repo:
            can_upload_current, _ = vm.validate_upload(target_repo)
            if can_upload_current:
                choice_prompt += ", 'c' for current"
        choice_prompt += ", or type version): "
        
        choice = input(choice_prompt).strip()
        
        if choice.isdigit() and 1 <= int(choice) <= len(suggestions):
            selected_version = suggestions[int(choice) - 1]
            
            # Validate the selected version
            if target_repo:
                # Temporarily update version to validate
                original_version = current_version
                update_version(selected_version)
                can_upload, reason = vm.validate_upload(target_repo)
                update_version(original_version)  # Restore original
                
                if not can_upload:
                    print(f"❌ Version {selected_version} cannot be uploaded to {target_repo}: {reason}")
                    continue
            
            return selected_version
        elif choice.lower() == 'c':
            # Use current version if valid
            if target_repo:
                can_upload_current, reason = vm.validate_upload(target_repo)
                if can_upload_current:
                    return current_version
                else:
                    print(f"❌ Current version {current_version} cannot be uploaded to {target_repo}: {reason}")
                    continue
            else:
                return current_version
        elif re.match(r'^\d+\.\d+\.\d+', choice):
            # Validate custom version
            if target_repo:
                original_version = current_version
                update_version(choice)
                can_upload, reason = vm.validate_upload(target_repo)
                update_version(original_version)  # Restore original
                
                if not can_upload:
                    print(f"❌ Version {choice} cannot be uploaded to {target_repo}: {reason}")
                    continue
            
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
        # Determine target repository for version validation
        target_repo = None
        if choice == "2":
            target_repo = "testpypi"
        elif choice == "3":
            target_repo = "pypi"
        
        # Get new version from user with repository-specific validation
        new_version = get_version_input(target_repo)
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
        # Final validation before upload
        vm = VersionManager()
        can_upload, reason = vm.validate_upload("testpypi")
        if can_upload:
            upload_to_testpypi()
        else:
            print(f"❌ Upload blocked: {reason}")
    elif choice == "3":
        # Final validation before upload
        vm = VersionManager()
        can_upload, reason = vm.validate_upload("pypi")
        if not can_upload:
            print(f"❌ Upload blocked: {reason}")
            return
            
        confirm = input("\n⚠️  Upload to PyPI? This will make the package public. (y/n): ")
        if confirm.lower() == 'y':
            upload_to_pypi()
        else:
            print("Cancelled")
    elif choice == "4":
        # Validate existing build for TestPyPI
        vm = VersionManager()
        can_upload, reason = vm.validate_upload("testpypi")
        if can_upload:
            upload_to_testpypi()
        else:
            print(f"❌ Upload blocked: {reason}")
    elif choice == "5":
        # Validate existing build for PyPI
        vm = VersionManager()
        can_upload, reason = vm.validate_upload("pypi")
        if not can_upload:
            print(f"❌ Upload blocked: {reason}")
            return
            
        confirm = input("\n⚠️  Upload to PyPI? This will make the package public. (y/n): ")
        if confirm.lower() == 'y':
            upload_to_pypi()
        else:
            print("Cancelled")
    
    print("\n🎉 Publishing workflow complete!")

if __name__ == "__main__":
    main()
