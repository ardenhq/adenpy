#!/usr/bin/env python3
"""
Version Management System for Arden PyPI Publishing

Handles different version states between TestPyPI and PyPI to prevent
incorrect uploads and manage version increments properly.
"""

import requests
import re
import json
from typing import Optional, List, Tuple, Dict
from packaging import version


class VersionManager:
    """Manages versions across TestPyPI and PyPI repositories."""
    
    def __init__(self, package_name: str = "ardenpy"):
        self.package_name = package_name
        self.pypi_url = f"https://pypi.org/pypi/{package_name}/json"
        self.testpypi_url = f"https://test.pypi.org/pypi/{package_name}/json"
    
    def get_current_local_version(self) -> Optional[str]:
        """Get the current version from pyproject.toml."""
        try:
            with open("pyproject.toml", "r") as f:
                content = f.read()
            
            match = re.search(r'version\s*=\s*"([^"]+)"', content)
            if match:
                return match.group(1)
            return None
        except Exception as e:
            print(f"❌ Error reading local version: {e}")
            return None
    
    def get_remote_versions(self, repository: str) -> Dict[str, any]:
        """Get version info from a PyPI repository."""
        url = self.testpypi_url if repository == "testpypi" else self.pypi_url
        
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 404:
                return {"exists": False, "versions": [], "latest": None}
            
            response.raise_for_status()
            data = response.json()
            
            versions = list(data["releases"].keys())
            # Filter out pre-release versions and sort
            stable_versions = [v for v in versions if not any(pre in v for pre in ['a', 'b', 'rc', 'dev'])]
            
            if stable_versions:
                latest = max(stable_versions, key=version.parse)
            else:
                latest = max(versions, key=version.parse) if versions else None
            
            return {
                "exists": True,
                "versions": sorted(versions, key=version.parse),
                "latest": latest,
                "all_versions": versions
            }
        
        except requests.RequestException as e:
            print(f"⚠️ Could not fetch {repository} versions: {e}")
            return {"exists": False, "versions": [], "latest": None, "error": str(e)}
    
    def get_version_status(self) -> Dict[str, any]:
        """Get comprehensive version status across all repositories."""
        local_version = self.get_current_local_version()
        pypi_info = self.get_remote_versions("pypi")
        testpypi_info = self.get_remote_versions("testpypi")
        
        return {
            "local": local_version,
            "pypi": pypi_info,
            "testpypi": testpypi_info
        }
    
    def analyze_version_state(self) -> Dict[str, any]:
        """Analyze current version state and provide recommendations."""
        status = self.get_version_status()
        local_ver = status["local"]
        pypi_latest = status["pypi"].get("latest")
        testpypi_latest = status["testpypi"].get("latest")
        
        analysis = {
            "local_version": local_ver,
            "pypi_latest": pypi_latest,
            "testpypi_latest": testpypi_latest,
            "pypi_exists": status["pypi"]["exists"],
            "testpypi_exists": status["testpypi"]["exists"],
            "recommendations": [],
            "warnings": [],
            "can_upload_to_pypi": False,
            "can_upload_to_testpypi": False
        }
        
        if not local_ver:
            analysis["warnings"].append("Could not read local version from pyproject.toml")
            return analysis
        
        local_v = version.parse(local_ver)
        
        # Analyze PyPI state
        if not analysis["pypi_exists"]:
            analysis["can_upload_to_pypi"] = True
            analysis["recommendations"].append(f"First PyPI release: {local_ver} is ready")
        elif pypi_latest:
            pypi_v = version.parse(pypi_latest)
            if local_v > pypi_v:
                analysis["can_upload_to_pypi"] = True
                analysis["recommendations"].append(f"PyPI update: {local_ver} > {pypi_latest} ✅")
            elif local_v == pypi_v:
                analysis["warnings"].append(f"Version {local_ver} already exists on PyPI")
            else:
                analysis["warnings"].append(f"Local version {local_ver} < PyPI {pypi_latest}")
        
        # Analyze TestPyPI state
        if not analysis["testpypi_exists"]:
            analysis["can_upload_to_testpypi"] = True
            analysis["recommendations"].append(f"First TestPyPI release: {local_ver} is ready")
        elif testpypi_latest:
            testpypi_v = version.parse(testpypi_latest)
            if local_v > testpypi_v:
                analysis["can_upload_to_testpypi"] = True
                analysis["recommendations"].append(f"TestPyPI update: {local_ver} > {testpypi_latest} ✅")
            elif local_v == testpypi_v:
                analysis["warnings"].append(f"Version {local_ver} already exists on TestPyPI")
            else:
                analysis["warnings"].append(f"Local version {local_ver} < TestPyPI {testpypi_latest}")
        
        return analysis
    
    def suggest_next_versions(self) -> Dict[str, List[str]]:
        """Suggest appropriate next versions for each repository."""
        status = self.get_version_status()
        local_ver = status["local"]
        pypi_latest = status["pypi"].get("latest")
        testpypi_latest = status["testpypi"].get("latest")
        
        suggestions = {
            "for_testpypi": [],
            "for_pypi": [],
            "current_local": local_ver
        }
        
        if not local_ver:
            return suggestions
        
        local_v = version.parse(local_ver)
        
        # Suggest versions for TestPyPI
        if testpypi_latest:
            testpypi_v = version.parse(testpypi_latest)
            base_version = max(local_v, testpypi_v)
        else:
            base_version = local_v
        
        # Generate TestPyPI suggestions (can be more frequent)
        suggestions["for_testpypi"] = self._generate_version_suggestions(str(base_version), include_dev=True)
        
        # Suggest versions for PyPI (should be stable)
        if pypi_latest:
            pypi_v = version.parse(pypi_latest)
            base_version = max(local_v, pypi_v)
        else:
            base_version = local_v
        
        suggestions["for_pypi"] = self._generate_version_suggestions(str(base_version), include_dev=False)
        
        return suggestions
    
    def _generate_version_suggestions(self, base_version: str, include_dev: bool = False) -> List[str]:
        """Generate version increment suggestions."""
        try:
            parts = base_version.split(".")
            major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
            
            suggestions = [
                f"{major}.{minor}.{patch + 1}",  # Patch increment
                f"{major}.{minor + 1}.0",        # Minor increment
                f"{major + 1}.0.0"               # Major increment
            ]
            
            if include_dev:
                suggestions.extend([
                    f"{major}.{minor}.{patch + 1}dev1",  # Dev version
                    f"{major}.{minor + 1}.0rc1",         # Release candidate
                ])
            
            return suggestions
        except:
            return ["0.1.1", "0.2.0", "1.0.0"]
    
    def print_status_report(self):
        """Print a comprehensive status report."""
        print("🔍 Version Status Report")
        print("=" * 50)
        
        analysis = self.analyze_version_state()
        
        print(f"📦 Package: {self.package_name}")
        print(f"💻 Local Version: {analysis['local_version'] or 'Not found'}")
        print(f"🌐 PyPI Latest: {analysis['pypi_latest'] or 'Not published'}")
        print(f"🧪 TestPyPI Latest: {analysis['testpypi_latest'] or 'Not published'}")
        print()
        
        if analysis["recommendations"]:
            print("✅ Recommendations:")
            for rec in analysis["recommendations"]:
                print(f"   • {rec}")
            print()
        
        if analysis["warnings"]:
            print("⚠️ Warnings:")
            for warning in analysis["warnings"]:
                print(f"   • {warning}")
            print()
        
        print("📋 Upload Status:")
        print(f"   • Can upload to PyPI: {'✅ Yes' if analysis['can_upload_to_pypi'] else '❌ No'}")
        print(f"   • Can upload to TestPyPI: {'✅ Yes' if analysis['can_upload_to_testpypi'] else '❌ No'}")
        print()
        
        # Show version suggestions
        suggestions = self.suggest_next_versions()
        if suggestions["for_pypi"]:
            print("💡 Suggested versions for PyPI:")
            for i, ver in enumerate(suggestions["for_pypi"][:3], 1):
                labels = ["(patch)", "(minor)", "(major)"]
                print(f"   {i}. {ver} {labels[i-1] if i <= 3 else ''}")
            print()
        
        if suggestions["for_testpypi"]:
            print("🧪 Suggested versions for TestPyPI:")
            for i, ver in enumerate(suggestions["for_testpypi"][:3], 1):
                labels = ["(patch)", "(minor)", "(major)"]
                print(f"   {i}. {ver} {labels[i-1] if i <= 3 else ''}")
            print()
    
    def validate_upload(self, target_repo: str) -> Tuple[bool, str]:
        """Validate if upload to target repository is safe."""
        analysis = self.analyze_version_state()
        
        if target_repo.lower() == "pypi":
            can_upload = analysis["can_upload_to_pypi"]
            reason = "PyPI upload is safe" if can_upload else "Version conflict or downgrade detected for PyPI"
        elif target_repo.lower() == "testpypi":
            can_upload = analysis["can_upload_to_testpypi"]
            reason = "TestPyPI upload is safe" if can_upload else "Version conflict or downgrade detected for TestPyPI"
        else:
            return False, f"Unknown repository: {target_repo}"
        
        return can_upload, reason


def main():
    """CLI interface for version management."""
    vm = VersionManager()
    vm.print_status_report()


if __name__ == "__main__":
    main()
